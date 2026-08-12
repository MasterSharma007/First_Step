# AWS EC2 Deployment

Moves the whole stack (Postgres + Redis + backend + frontend) from your
local machine to a single EC2 box, running continuously via Docker
Compose (`docker-compose.prod.yml`).

## 1. Instance sizing

| | Minimum | Recommended |
|---|---|---|
| Type | `t3.medium` (2 vCPU, 4 GB) | **`t3.large`** (2 vCPU, 8 GB) |
| Storage | 30 GB gp3 | 50 GB gp3 |
| AMI | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Network | Elastic IP (static) | Elastic IP (static) |

Why: locally this stack runs backend (~300-700 MB RSS), Postgres,
Redis, and a Next.js process comfortably inside 2 GB with room to
spare - but that's dev mode with nothing else on the box. `t3.medium`
is workable if money's tight; `t3.large`'s extra headroom means the
`next build` during deploys and Postgres's page cache (this ingests
tick data continuously) won't compete with the live paper-trading
loop for memory. Both are burstable (T-series) - fine here since this
isn't a sustained-CPU workload, mostly I/O waits on Kite API calls.

`RabbitMQ` from the local `docker-compose.yml` is dropped in
`docker-compose.prod.yml` - nothing in the codebase actually connects
to it (only `Settings.rabbitmq_url` exists, unused), so it would just
burn RAM for nothing on a box you're paying for.

**If you already launched a smaller instance** (e.g. free-tier
`t2.micro`, 1 GB RAM): it will not run this stack reliably - resize it
(stop instance → Instance Settings → Change Instance Type) before
proceeding.

## 2. Security group

| Port | Source | Purpose |
|---|---|---|
| 22 | your IP only | SSH |
| 80, 443 | 0.0.0.0/0 | Nginx (HTTP/HTTPS) - the only public entry point |

Backend (8000) and frontend (3000) are **not** opened publicly -
`docker-compose.prod.yml` binds them to `127.0.0.1` only; Nginx is the
sole reverse proxy in front of both. Postgres/Redis aren't published
to the host at all.

## 3. One-time server setup

SSH in, then:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose-v2 git nginx

sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # log out/in once for this to take effect

# Node.js (for the Claude Code CLI, not needed by the app itself - it runs in Docker)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
npm install -g @anthropic-ai/claude-code
```

## 4. Get the code onto the box

```bash
git clone git@github.com:MasterSharma007/First_Step.git
cd First_Step
```

(Use whichever auth you've already got working for this repo - SSH
deploy key or HTTPS+PAT, same as pushing from your laptop.)

## 5. Configure environment

**Root `.env`** (compose port/DB overrides):

```
POSTGRES_USER=bn_user
POSTGRES_PASSWORD=<generate a real one - openssl rand -hex 24>
POSTGRES_DB=banknifty
BACKEND_HOST_PORT=8000
FRONTEND_HOST_PORT=3000
NEXT_PUBLIC_API_URL=/api/v1
```

**`backend/.env`** - copy your local one's values across (Kite
credentials, risk settings), but change:

```
KITE_REDIRECT_URL=https://<your-domain-or-IP>/api/v1/kite/callback
```

You'll need to update this same URL in your Kite Connect app settings
at developers.kite.trade - Kite rejects callbacks that don't exactly
match what's registered there.

## 6. Bring the existing data across

On your **local machine** (dump the DB you've been building all
session):

```bash
docker exec bn_postgres pg_dump -U bn_user -d banknifty --no-owner --clean > banknifty.sql
scp banknifty.sql ubuntu@<ec2-ip>:~/First_Step/
```

On the **EC2 box**, start just Postgres first, then restore before the
backend touches it:

```bash
docker compose -f docker-compose.prod.yml up -d postgres
sleep 5
docker exec -i bn_postgres psql -U bn_user -d banknifty < banknifty.sql
```

If you'd rather start clean instead of migrating history, skip this
and just run `uv run alembic upgrade head` + the backfill CLI once the
backend container is up (see `docs/SETUP.md` §2).

## 7. Build and start everything

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend uv run alembic upgrade head
```

Check it's actually up:

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:3000 -o /dev/null -w "%{http_code}\n"
```

**One hard rule**: never scale the `backend` service beyond 1
replica/worker. The live paper-trading scheduler
(`app/workers/scheduler.py`) runs in-process with in-memory state - a
second instance means the live loop runs twice, opening every paper
position twice. `docker-compose.prod.yml` has this called out; don't
add `--scale backend=N` or gunicorn/uvicorn multi-worker flags.

## 8. Nginx reverse proxy (+ HTTPS)

```nginx
# /etc/nginx/sites-available/banknifty
server {
    listen 80;
    server_name <your-domain-or-IP>;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/banknifty /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

If you have a domain pointed at the Elastic IP, add HTTPS (Kite's
production redirect URL should be `https://`, not `http://`):

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Without a domain, Kite will generally still accept an `http://<IP>/...`
redirect URL for a personal/test app - use that and revisit HTTPS once
you have a domain.

## 9. Daily Kite login + go live

Same flow as local (`docs/SETUP.md`), against the new URL:

1. `GET https://<domain>/api/v1/kite/login-url` → log in on Kite.
2. Paste the returned access token into `backend/.env`'s
   `KITE_ACCESS_TOKEN`, then `docker compose -f docker-compose.prod.yml restart backend`.
3. Set `LIVE_LOOP_ENABLED=true` in `backend/.env` and restart backend
   when you're ready for it to trade (paper) automatically.

This access token expires daily - you'll need to repeat step 1-2 every
trading morning, same as running locally.

## 10. Keep it running

- `restart: unless-stopped` on every service means Docker restarts them
  if they crash, and restarts them automatically when the Docker
  daemon comes up after an EC2 reboot (`systemctl enable docker`
  already covers that).
- Back up the DB regularly - a simple cron on the EC2 box:
  ```bash
  # /etc/cron.d/banknifty-backup
  0 2 * * * ubuntu docker exec bn_postgres pg_dump -U bn_user -d banknifty | gzip > /home/ubuntu/backups/banknifty-$(date +\%F).sql.gz
  ```
- Watch logs: `docker compose -f docker-compose.prod.yml logs -f backend`

## 11. Using Claude Code on the box

Once the CLI's installed (step 3), `cd ~/First_Step && claude` from an
SSH session gives you the same workflow you've been using locally,
directly against the production deployment - useful for debugging
against real production logs/DB without needing to sync anything back.

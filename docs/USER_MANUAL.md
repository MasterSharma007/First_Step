# User Manual

What each page in the dashboard (`http://localhost:3001`) shows, and where to find specific things. For install/setup, see `docs/SETUP.md`. For the original requirements, see `docs/SRD.md`.

## Quick answers

| I want to see... | Go to |
|---|---|
| Current price | Dashboard or Live |
| Which signal is firing right now (buy CE/PE?) | **Live** → Signal Suggestion card |
| Target / stop loss for the current signal | **Live** → Signal Suggestion card |
| Support & resistance | Dashboard or **Live** → Trend card |
| Live profit/loss on an open trade | **Live** → Open Paper Positions table |
| Past trades and their P&L | **Trades** |
| History of signals the engine has generated | **Signals** |
| Option chain (PCR, Max Pain, OI) | **Option Chain** |
| How the strategy performs historically | **Backtest** |
| Today's / a day's P&L summary | **Reports** |
| Errors or what the backend is doing | **Logs** |

## Dashboard (`/`)

The landing page. Spot price candlestick chart (5-minute candles), day high/low/change, the current Trend card (direction + support/resistance), and the 10 most recent signals.

Static snapshot as of page load - refresh to update. For continuously-updating data, use **Live**.

## Live (`/live`)

The real-time cockpit. Polls the backend every 8 seconds.

- **Spot LTP, India VIX, PCR, Max Pain** - live stat cards.
- **Trend card** - BULLISH/BEARISH/NEUTRAL with the reasons (VWAP position, EMA alignment, HH/HL structure, OI writing), plus a Support / current price / Resistance ladder.
- **Signal Suggestion card** - what the Signal Engine says *right now*: which strike/side to buy (e.g. "Buy 57600 CE"), its live entry premium, stop loss, and target. Shows "No actionable setup" when nothing meets the confidence threshold.
- **Open Paper Positions** - any currently-open paper trade, with live unrealized P&L, updating every poll.
- **Today's realized P&L** - top-right of the positions section.
- An amber banner appears if auto paper-trading is off (`LIVE_LOOP_ENABLED=false` - see `docs/SETUP.md`). The signal/price/trend view works either way; only automatic execution is gated.

## Option Chain (`/option-chain`)

Pick an expiry from the dropdown. Shows spot price, ATM strike, PCR, Max Pain, total CE/PE OI, the OI writing verdict (CE_WRITING / PE_WRITING / NEUTRAL), and the full per-strike table (OI, OI change, LTP for both sides - ATM row highlighted).

**Browsing history**: set the "As of date" field to any backfilled date to see that day's chain instead of the latest one.

## Signals (`/signals`)

Every signal the engine has generated and persisted - time, CE/PE, strike, entry price, stop loss, target, and confidence score (0-100; ≥70 → strong CE, ≤30 → strong PE, between → no trade). This only fills up once the live loop has actually opened trades (each paper trade records the signal that triggered it) or the backtest data has run.

## Trades (`/trades`)

Every executed trade across backtest/paper/live modes - symbol, status (open/closed/cancelled), quantity, entry/exit price, P&L, and exit reason (STOP_LOSS/TARGET).

## Backtest (`/backtest`)

Pick a start/end date and run the strategy against historical data. Results table shows trade count, win rate, profit factor, max drawdown, Sharpe ratio, and net P&L for every run you've done.

Needs `spot_ohlc` and `option_ohlc` history for the chosen range first - see `docs/SETUP.md` → backfill.

## Reports (`/reports`)

Daily summary: total trades, win rate, net profit, charges, max drawdown, for a given day (defaults to today).

## Logs (`/logs`)

Tails the backend's log file (`backend/logs/app.log`), refreshing every 5 seconds. Filter by level (debug/info/warning/error) with the dropdown - use **error** or **warning** to cut through noise when something's not working.

## Glossary

| Term | Meaning |
|---|---|
| **CE / PE** | Call / Put option |
| **ATM** | At-the-money - the strike closest to the current spot price |
| **PCR** | Put-Call Ratio - total PE OI ÷ total CE OI. Conventionally read as contrarian: high PCR (lots of puts written) → bullish |
| **Max Pain** | The strike at which option writers collectively lose the least (buyers gain the least) - a magnet price near expiry |
| **OI / OI Change** | Open Interest - number of outstanding contracts, and how much it changed |
| **CE/PE Writing** | OI increasing while premium falls at a strike - sellers in control, a directional signal |
| **SL / Target** | Stop Loss / Target price |
| **RR** | Risk:Reward ratio (default 1:2 - risk 1 to make 2) |
| **VWAP** | Volume-Weighted Average Price |
| **Confidence Score** | 0-100 output of the Signal Engine; ≥70 strong CE, ≤30 strong PE, 30-70 no trade |
| **Paper trading** | Simulated trades with real prices but no real money |

## Common questions

**Why is the Signal Suggestion card empty / "No actionable setup"?**
Confidence score is between 30-70 - conditions aren't strong enough either way. This is normal for most of the trading day.

**Why does Live show a different price than Option Chain?**
Live polls Kite directly for the current tick. Option Chain (without an "as of" date) shows the most recent *stored* snapshot, which may be a few minutes older depending on when it was last backfilled/ingested.

**Nothing shows up anywhere - all pages are empty.**
You likely haven't backfilled historical data yet, or the backend can't reach Kite (check `KITE_ACCESS_TOKEN` hasn't expired). Check **Logs** for the actual error.

**Backtest shows a lot of trades and/or consistent losses.**
A realistic run is roughly a handful to a few dozen trades per month, not hundreds - if you see hundreds, something's likely still off with the underlying data (e.g. missing option history for part of the range) rather than the strategy itself. Assuming trade count looks sane, ongoing net losses are a legitimate finding about the rule-based scorer, not a bug - it's a starting point that needs tuning, not a finished strategy. Check `params.expiry_traded` in the result and the individual trades' premiums/durations look plausible before concluding either way.

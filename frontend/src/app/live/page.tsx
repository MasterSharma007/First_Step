"use client";

import EmptyState from "@/components/EmptyState";
import MultiTimeframePanel from "@/components/MultiTimeframePanel";
import SignalSuggestionCard from "@/components/SignalSuggestionCard";
import StatCard from "@/components/StatCard";
import TrendCard from "@/components/TrendCard";
import { ApiError, api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";

const POLL_MS = 5000; // matches the backend's live tick-aggregation cadence
const MTF_POLL_MS = 15000; // 15m/1h/1d/1w/1M candles don't move fast enough to justify 5s polling

export default function LivePage() {
  const { data: status, error, loading } = usePolling(() => api.liveStatus(), POLL_MS);
  const { data: multiTimeframe } = usePolling(() => api.multiTimeframe(), MTF_POLL_MS);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-black">Live</h1>
          <p className="mt-1 text-sm text-slate-600">
            Live price, signal, and P&amp;L - refreshes every {POLL_MS / 1000}s.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <span
              className={`rounded px-2.5 py-1 text-xs font-bold tracking-wide ${
                status.trading_mode === "LIVE" ? "bg-red-600 text-white" : "bg-slate-700 text-white"
              }`}
            >
              {status.trading_mode === "LIVE" ? "🔴 LIVE - REAL MONEY" : "PAPER"}
            </span>
          )}
          {status && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-500" : "bg-green-600"} animate-pulse`} />
              as of {new Date(status.as_of).toLocaleTimeString()}
            </div>
          )}
        </div>
      </div>

      {error && !status && (
        <EmptyState
          title="Can't load live status"
          hint={error instanceof ApiError ? error.message : "Backend unreachable - is it running?"}
        />
      )}

      {!status && !error && <EmptyState title="Loading live status…" />}

      {status && (
        <>
          {!status.live_loop_enabled && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-xs text-amber-800">
              Auto trading loop is OFF (LIVE_LOOP_ENABLED=false) - signals are shown but positions won&apos;t open
              automatically.
            </div>
          )}
          {status.trading_mode === "LIVE" && (
            <div className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-xs font-medium text-red-800">
              Trading mode is LIVE - entries/exits below place real orders through Kite, not simulated ones. Switch
              back via PAPER_TRADING=true in backend/.env (restart required).
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Spot LTP" value={status.spot_price.toFixed(2)} />
            <StatCard label="India VIX" value={status.india_vix.toFixed(2)} />
            <StatCard label="PCR" value={status.pcr?.toFixed(3) ?? "—"} />
            <StatCard label="Max Pain" value={status.max_pain?.toFixed(0) ?? "—"} />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <TrendCard
              trend={{
                symbol: "NIFTY BANK",
                interval: "live",
                as_of: status.as_of,
                direction: status.trend_direction,
                reasons: status.trend_reasons,
                support: status.support,
                resistance: status.resistance,
                current_price: status.spot_price,
              }}
            />
            <SignalSuggestionCard signal={status.signal} />
          </div>

          {multiTimeframe && <MultiTimeframePanel data={multiTimeframe} />}

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-black">
                Open {status.trading_mode === "LIVE" ? "Live" : "Paper"} Positions
              </h2>
              <span className="text-xs text-slate-500">
                Today&apos;s realized P&amp;L:{" "}
                <span className={status.today_realized_pnl >= 0 ? "text-green-600" : "text-red-600"}>
                  {status.today_realized_pnl.toFixed(2)}
                </span>
              </span>
            </div>

            {status.open_positions.length === 0 ? (
              <EmptyState
                title={`No open ${status.trading_mode === "LIVE" ? "live" : "paper"} positions`}
                hint="One will appear here automatically once the live loop opens a trade."
              />
            ) : (
              <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
                <table className="w-full text-sm">
                  <thead className="bg-slate-100 text-left text-xs font-semibold uppercase text-black">
                    <tr>
                      <th className="px-4 py-2 font-medium">Symbol</th>
                      <th className="px-4 py-2 font-medium">Qty</th>
                      <th className="px-4 py-2 font-medium">Entry</th>
                      <th className="px-4 py-2 font-medium">Current</th>
                      <th className="px-4 py-2 font-medium">SL</th>
                      <th className="px-4 py-2 font-medium">Target</th>
                      <th className="px-4 py-2 font-medium">Unrealized P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {status.open_positions.map((p) => (
                      <tr key={p.order_id}>
                        <td className="px-4 py-2 font-semibold text-black">
                          {p.symbol} <span className="font-normal text-slate-500">{p.option_type}</span>
                        </td>
                        <td className="px-4 py-2 text-black">{p.quantity}</td>
                        <td className="px-4 py-2 text-black">{p.entry_price.toFixed(2)}</td>
                        <td className="px-4 py-2 text-black">{p.current_price?.toFixed(2) ?? "—"}</td>
                        <td className="px-4 py-2 text-red-600">{p.stop_loss?.toFixed(2) ?? "—"}</td>
                        <td className="px-4 py-2 text-green-600">{p.target?.toFixed(2) ?? "—"}</td>
                        <td
                          className={`px-4 py-2 font-semibold ${
                            (p.unrealized_pnl ?? 0) > 0
                              ? "text-green-600"
                              : (p.unrealized_pnl ?? 0) < 0
                                ? "text-red-600"
                                : "text-black"
                          }`}
                        >
                          {p.unrealized_pnl?.toFixed(2) ?? "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

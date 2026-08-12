"use client";

import EmptyState from "@/components/EmptyState";
import SignalSuggestionCard from "@/components/SignalSuggestionCard";
import StatCard from "@/components/StatCard";
import TrendCard from "@/components/TrendCard";
import { ApiError, api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";

const POLL_MS = 8000;

export default function LivePage() {
  const { data: status, error, loading } = usePolling(() => api.liveStatus(), POLL_MS);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-100">Live</h1>
          <p className="mt-1 text-sm text-neutral-500">
            Live price, signal, and paper P&amp;L - refreshes every {POLL_MS / 1000}s.
          </p>
        </div>
        {status && (
          <div className="flex items-center gap-2 text-xs text-neutral-500">
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400" : "bg-emerald-400"} animate-pulse`} />
            as of {new Date(status.as_of).toLocaleTimeString()}
          </div>
        )}
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
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs text-amber-400">
              Auto paper-trading loop is OFF (LIVE_LOOP_ENABLED=false) - signals are shown but positions won&apos;t
              open automatically.
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

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-medium text-neutral-300">Open Paper Positions</h2>
              <span className="text-xs text-neutral-500">
                Today&apos;s realized P&amp;L:{" "}
                <span className={status.today_realized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                  {status.today_realized_pnl.toFixed(2)}
                </span>
              </span>
            </div>

            {status.open_positions.length === 0 ? (
              <EmptyState
                title="No open paper positions"
                hint="One will appear here automatically once the live loop opens a trade."
              />
            ) : (
              <div className="overflow-x-auto rounded-lg border border-neutral-800">
                <table className="w-full text-sm">
                  <thead className="bg-neutral-800 text-left text-xs font-semibold uppercase text-neutral-300">
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
                  <tbody className="divide-y divide-neutral-800">
                    {status.open_positions.map((p) => (
                      <tr key={p.order_id}>
                        <td className="px-4 py-2 font-medium text-neutral-100">
                          {p.symbol} <span className="text-neutral-500">{p.option_type}</span>
                        </td>
                        <td className="px-4 py-2">{p.quantity}</td>
                        <td className="px-4 py-2">{p.entry_price.toFixed(2)}</td>
                        <td className="px-4 py-2">{p.current_price?.toFixed(2) ?? "—"}</td>
                        <td className="px-4 py-2 text-red-400">{p.stop_loss?.toFixed(2) ?? "—"}</td>
                        <td className="px-4 py-2 text-emerald-400">{p.target?.toFixed(2) ?? "—"}</td>
                        <td
                          className={`px-4 py-2 font-medium ${
                            (p.unrealized_pnl ?? 0) > 0
                              ? "text-emerald-400"
                              : (p.unrealized_pnl ?? 0) < 0
                                ? "text-red-400"
                                : ""
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

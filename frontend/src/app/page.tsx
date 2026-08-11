import EmptyState from "@/components/EmptyState";
import SignalBadge from "@/components/SignalBadge";
import SpotChart from "@/components/SpotChart";
import StatCard from "@/components/StatCard";
import TrendCard from "@/components/TrendCard";
import { api } from "@/lib/api";
import type { SpotOHLC, TradeSignal, Trend } from "@/lib/types";

export default async function DashboardPage() {
  const [candles, signals, trend] = await Promise.all([
    api.spotOhlc({ interval: "5m", limit: 200 }).catch((): SpotOHLC[] => []),
    api.signals(10).catch((): TradeSignal[] => []),
    api.trend({ interval: "5m" }).catch((): Trend | null => null),
  ]);

  const latest = candles.at(-1);
  const prev = candles.at(-2);
  const change = latest && prev ? latest.close - prev.close : 0;
  const changePct = latest && prev ? (change / prev.close) * 100 : 0;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-neutral-100">Bank Nifty Overview</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Live spot price action and the latest signals from the Signal Generation Engine.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Spot LTP" value={latest ? latest.close.toFixed(2) : "—"} />
        <StatCard
          label="Change"
          value={latest ? `${change >= 0 ? "+" : ""}${change.toFixed(2)} (${changePct.toFixed(2)}%)` : "—"}
          accent={change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}
        />
        <StatCard label="Day High" value={latest ? latest.high.toFixed(2) : "—"} />
        <StatCard label="Day Low" value={latest ? latest.low.toFixed(2) : "—"} />
      </div>

      {trend && <TrendCard trend={trend} />}

      <section className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4">
        <h2 className="mb-4 text-sm font-medium text-neutral-300">Spot Price (5m)</h2>
        {candles.length > 0 ? (
          <SpotChart candles={candles} />
        ) : (
          <EmptyState
            title="No spot OHLC data yet"
            hint="Run the historical backfill or start the live feed against your Kite credentials, then refresh."
          />
        )}
      </section>

      <section>
        <h2 className="mb-4 text-sm font-medium text-neutral-300">Latest Signals</h2>
        {signals.length > 0 ? (
          <div className="overflow-hidden rounded-lg border border-neutral-800">
            <table className="w-full text-sm">
              <thead className="bg-neutral-900/60 text-left text-xs uppercase text-neutral-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Time</th>
                  <th className="px-4 py-2 font-medium">Type</th>
                  <th className="px-4 py-2 font-medium">Entry</th>
                  <th className="px-4 py-2 font-medium">SL / Target</th>
                  <th className="px-4 py-2 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {signals.map((s) => (
                  <tr key={s.signal_id}>
                    <td className="px-4 py-2 text-neutral-400">
                      {new Date(s.entry_time).toLocaleString()}
                    </td>
                    <td className="px-4 py-2">
                      <SignalBadge type={s.signal_type} />
                    </td>
                    <td className="px-4 py-2">{s.entry_price.toFixed(2)}</td>
                    <td className="px-4 py-2 text-neutral-400">
                      {s.stop_loss?.toFixed(2) ?? "—"} / {s.target?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-4 py-2 font-medium">{s.confidence_score.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No signals yet" hint="The Signal Engine hasn't emitted any signals." />
        )}
      </section>
    </div>
  );
}

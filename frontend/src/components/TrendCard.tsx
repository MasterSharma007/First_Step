import type { Trend } from "@/lib/types";

const STYLES: Record<string, string> = {
  BULLISH: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  BEARISH: "bg-red-500/15 text-red-400 border-red-500/30",
  NEUTRAL: "bg-neutral-500/15 text-neutral-300 border-neutral-500/30",
};

export default function TrendCard({ trend }: { trend: Trend }) {
  const range = trend.resistance - trend.support;
  const positionPct = range > 0 ? ((trend.current_price - trend.support) / range) * 100 : 50;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-neutral-500">Trend ({trend.interval})</span>
        <span className={`rounded border px-2 py-0.5 text-xs font-semibold ${STYLES[trend.direction]}`}>
          {trend.direction}
        </span>
      </div>

      <ul className="mt-2 space-y-0.5 text-xs text-neutral-400">
        {trend.reasons.length === 0 ? (
          <li>No strong signals either way</li>
        ) : (
          trend.reasons.map((reason) => <li key={reason}>{reason}</li>)
        )}
      </ul>

      <div className="mt-4 border-t border-neutral-800 pt-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-red-400">S {trend.support.toFixed(2)}</span>
          <span className="font-medium text-neutral-100">{trend.current_price.toFixed(2)}</span>
          <span className="font-medium text-emerald-400">R {trend.resistance.toFixed(2)}</span>
        </div>
        <div className="mt-1.5 h-1.5 w-full rounded-full bg-neutral-800">
          <div
            className="h-1.5 rounded-full bg-sky-500"
            style={{ width: `${Math.min(Math.max(positionPct, 0), 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

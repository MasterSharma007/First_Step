import type { Trend } from "@/lib/types";

const STYLES: Record<string, string> = {
  BULLISH: "bg-green-600 text-white",
  BEARISH: "bg-red-600 text-white",
  NEUTRAL: "bg-slate-500 text-white",
};

export default function TrendCard({ trend }: { trend: Trend }) {
  const range = trend.resistance - trend.support;
  const positionPct = range > 0 ? ((trend.current_price - trend.support) / range) * 100 : 50;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-500">Trend ({trend.interval})</span>
        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${STYLES[trend.direction]}`}>
          {trend.direction}
        </span>
      </div>

      <ul className="mt-2 space-y-0.5 text-xs text-slate-600">
        {trend.reasons.length === 0 ? (
          <li>No strong signals either way</li>
        ) : (
          trend.reasons.map((reason) => <li key={reason}>{reason}</li>)
        )}
      </ul>

      <div className="mt-4 border-t border-slate-200 pt-3">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-red-600">S {trend.support.toFixed(2)}</span>
          <span className="font-semibold text-black">{trend.current_price.toFixed(2)}</span>
          <span className="font-semibold text-green-600">R {trend.resistance.toFixed(2)}</span>
        </div>
        <div className="mt-1.5 h-1.5 w-full rounded-full bg-slate-200">
          <div
            className="h-1.5 rounded-full bg-blue-600"
            style={{ width: `${Math.min(Math.max(positionPct, 0), 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}

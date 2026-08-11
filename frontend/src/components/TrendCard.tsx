import type { Trend } from "@/lib/types";

const STYLES: Record<string, string> = {
  BULLISH: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  BEARISH: "bg-red-500/15 text-red-400 border-red-500/30",
  NEUTRAL: "bg-neutral-500/15 text-neutral-300 border-neutral-500/30",
};

export default function TrendCard({ trend }: { trend: Trend }) {
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
    </div>
  );
}

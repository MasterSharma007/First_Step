import type { MultiTimeframe, TrendDirection } from "@/lib/types";

const STYLES: Record<TrendDirection, string> = {
  BULLISH: "bg-green-600 text-white",
  BEARISH: "bg-red-600 text-white",
  NEUTRAL: "bg-slate-500 text-white",
};

const LABELS: Record<string, string> = {
  "15m": "15 Min",
  "1h": "1 Hour",
  "1d": "Day",
  "1w": "Week",
  "1M": "Month",
};

export default function MultiTimeframePanel({ data }: { data: MultiTimeframe }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-500">Multi-Timeframe Trend</span>
        <span className="text-xs text-slate-500">Spot {data.current_price.toFixed(2)}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {data.timeframes.map((tf) => (
          <div key={tf.timeframe} className="rounded border border-slate-200 p-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-black">{LABELS[tf.timeframe] ?? tf.timeframe}</span>
              {tf.insufficient_data || !tf.direction ? (
                <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-600">
                  N/A
                </span>
              ) : (
                <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${STYLES[tf.direction]}`}>
                  {tf.direction}
                </span>
              )}
            </div>

            {tf.support !== null && tf.resistance !== null ? (
              <div className="mt-1.5 space-y-0.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-red-600">S</span>
                  <span className="font-medium text-black">{tf.support.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-green-600">R</span>
                  <span className="font-medium text-black">{tf.resistance.toFixed(1)}</span>
                </div>
              </div>
            ) : (
              <p className="mt-1.5 text-[11px] text-slate-400">No data</p>
            )}

            {tf.insufficient_data && (
              <p className="mt-1 text-[10px] text-slate-400">{tf.bars_available} bars (need 50+)</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

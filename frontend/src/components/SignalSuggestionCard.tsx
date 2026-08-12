import type { SignalSuggestion } from "@/lib/types";

const VERDICT_STYLE: Record<string, string> = {
  STRONG_CE: "border-green-300 bg-green-50",
  STRONG_PE: "border-red-300 bg-red-50",
  NO_TRADE: "border-slate-200 bg-white",
};

const BADGE_STYLE: Record<string, string> = {
  STRONG_CE: "bg-green-600 text-white",
  STRONG_PE: "bg-red-600 text-white",
  NO_TRADE: "bg-slate-500 text-white",
};

export default function SignalSuggestionCard({ signal }: { signal: SignalSuggestion }) {
  const isActionable = signal.signal_type !== "NO_TRADE";

  return (
    <div className={`rounded-lg border p-4 shadow-sm ${VERDICT_STYLE[signal.verdict] ?? VERDICT_STYLE.NO_TRADE}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-slate-500">Signal Suggestion</span>
        <span className={`rounded px-2 py-0.5 text-xs font-bold ${BADGE_STYLE[signal.verdict] ?? BADGE_STYLE.NO_TRADE}`}>
          {signal.verdict.replace("_", " ")}
        </span>
      </div>

      {isActionable ? (
        <>
          <div className="mt-2 text-lg font-semibold text-black">
            Buy {signal.strike?.toFixed(0)} {signal.option_type}
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-xs text-slate-500">Entry (premium)</div>
              <div className="font-semibold text-black">{signal.entry_price?.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Stop Loss</div>
              <div className="font-semibold text-red-600">{signal.stop_loss?.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-slate-500">Target</div>
              <div className="font-semibold text-green-600">{signal.target?.toFixed(2)}</div>
            </div>
          </div>
        </>
      ) : (
        <p className="mt-2 text-sm text-slate-600">No actionable setup right now - conditions aren&apos;t strong enough.</p>
      )}

      <div className="mt-3 text-xs text-slate-500">
        Confidence <span className="font-semibold text-black">{signal.confidence_score.toFixed(1)}</span> / 100
      </div>
    </div>
  );
}

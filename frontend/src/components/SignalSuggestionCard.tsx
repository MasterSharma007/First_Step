import type { SignalSuggestion } from "@/lib/types";

const VERDICT_STYLE: Record<string, string> = {
  STRONG_CE: "border-emerald-500/40 bg-emerald-500/10",
  STRONG_PE: "border-red-500/40 bg-red-500/10",
  NO_TRADE: "border-neutral-800 bg-neutral-900/50",
};

const BADGE_STYLE: Record<string, string> = {
  STRONG_CE: "bg-emerald-500 text-neutral-950",
  STRONG_PE: "bg-red-500 text-neutral-950",
  NO_TRADE: "bg-neutral-700 text-neutral-200",
};

export default function SignalSuggestionCard({ signal }: { signal: SignalSuggestion }) {
  const isActionable = signal.signal_type !== "NO_TRADE";

  return (
    <div className={`rounded-lg border p-4 ${VERDICT_STYLE[signal.verdict] ?? VERDICT_STYLE.NO_TRADE}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-wide text-neutral-500">Signal Suggestion</span>
        <span className={`rounded px-2 py-0.5 text-xs font-bold ${BADGE_STYLE[signal.verdict] ?? BADGE_STYLE.NO_TRADE}`}>
          {signal.verdict.replace("_", " ")}
        </span>
      </div>

      {isActionable ? (
        <>
          <div className="mt-2 text-lg font-semibold text-neutral-100">
            Buy {signal.strike?.toFixed(0)} {signal.option_type}
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-xs text-neutral-500">Entry (premium)</div>
              <div className="font-medium text-neutral-100">{signal.entry_price?.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-neutral-500">Stop Loss</div>
              <div className="font-medium text-red-400">{signal.stop_loss?.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-neutral-500">Target</div>
              <div className="font-medium text-emerald-400">{signal.target?.toFixed(2)}</div>
            </div>
          </div>
        </>
      ) : (
        <p className="mt-2 text-sm text-neutral-400">No actionable setup right now - conditions aren&apos;t strong enough.</p>
      )}

      <div className="mt-3 text-xs text-neutral-500">
        Confidence <span className="font-medium text-neutral-300">{signal.confidence_score.toFixed(1)}</span> / 100
      </div>
    </div>
  );
}

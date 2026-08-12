"use client";

import EmptyState from "@/components/EmptyState";
import { ApiError, api } from "@/lib/api";
import type { PriceActionReading, SwingKind } from "@/lib/types";
import { usePolling } from "@/lib/usePolling";

const POLL_MS = 5000; // matches the backend's live tick-aggregation cadence

const SWING_LABELS: Record<SwingKind, string> = {
  HH: "Higher High",
  LH: "Lower High",
  HL: "Higher Low",
  LL: "Lower Low",
};

const SWING_STYLES: Record<SwingKind, string> = {
  HH: "bg-green-600 text-white",
  HL: "bg-green-100 text-green-700",
  LH: "bg-red-100 text-red-700",
  LL: "bg-red-600 text-white",
};

function TimeframePanel({ reading }: { reading: PriceActionReading }) {
  const cb = reading.candle_break;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-black">{reading.timeframe} Candle</span>
        <span className="text-xs text-slate-500">Price {reading.current_price.toFixed(2)}</span>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="rounded border border-slate-200 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">Candle Break</p>
          {cb ? (
            <>
              <span
                className={`mt-1 inline-block rounded px-2 py-0.5 text-xs font-semibold ${
                  cb.direction === "UP"
                    ? "bg-green-600 text-white"
                    : cb.direction === "DOWN"
                      ? "bg-red-600 text-white"
                      : "bg-slate-200 text-slate-600"
                }`}
              >
                {cb.direction === "UP" ? "BREAKOUT UP" : cb.direction === "DOWN" ? "BREAKDOWN" : "INSIDE RANGE"}
              </span>
              <p className="mt-1.5 text-[11px] text-slate-500">
                vs prior candle {cb.reference_low.toFixed(1)} – {cb.reference_high.toFixed(1)}
              </p>
            </>
          ) : (
            <p className="mt-1 text-xs text-slate-400">Not enough candles yet</p>
          )}
        </div>

        <div className="rounded border border-slate-200 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">S/R Break</p>
          <span
            className={`mt-1 inline-block rounded px-2 py-0.5 text-xs font-semibold ${
              reading.sr_break === "RESISTANCE_BREAK"
                ? "bg-green-600 text-white"
                : reading.sr_break === "SUPPORT_BREAK"
                  ? "bg-red-600 text-white"
                  : "bg-slate-200 text-slate-600"
            }`}
          >
            {reading.sr_break === "RESISTANCE_BREAK"
              ? "RESISTANCE BROKEN"
              : reading.sr_break === "SUPPORT_BREAK"
                ? "SUPPORT BROKEN"
                : "HOLDING RANGE"}
          </span>
          <p className="mt-1.5 text-[11px] text-slate-500">
            S {reading.support?.toFixed(1) ?? "—"} · R {reading.resistance?.toFixed(1) ?? "—"}
          </p>
        </div>
      </div>

      <div className="mt-3 rounded border border-slate-200 p-3">
        <div className="flex items-center justify-between">
          <p className="text-xs uppercase tracking-wide text-slate-500">Market Structure</p>
          {reading.structure && (
            <span className={`rounded px-2 py-0.5 text-xs font-semibold ${SWING_STYLES[reading.structure]}`}>
              {SWING_LABELS[reading.structure]}
            </span>
          )}
        </div>

        {reading.swing_points.length === 0 ? (
          <p className="mt-1.5 text-xs text-slate-400">Not enough confirmed swing points yet</p>
        ) : (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {reading.swing_points.map((p) => (
              <span
                key={`${p.time}-${p.kind}`}
                title={new Date(p.time).toLocaleString()}
                className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${SWING_STYLES[p.kind]}`}
              >
                {p.kind} {p.price.toFixed(0)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function PriceActionPage() {
  const { data, error, loading } = usePolling(() => api.priceAction(), POLL_MS);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-black">Price Action</h1>
          <p className="mt-1 text-sm text-slate-600">
            Live candle breakouts, support/resistance breaks, and swing structure - refreshes every{" "}
            {POLL_MS / 1000}s.
          </p>
        </div>
        {data && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-500" : "bg-green-600"} animate-pulse`} />
            {data.symbol} · {data.current_price.toFixed(2)}
          </div>
        )}
      </div>

      {error && !data && (
        <EmptyState
          title="Can't load price action"
          hint={error instanceof ApiError ? error.message : "Backend unreachable - is it running?"}
        />
      )}

      {!data && !error && <EmptyState title="Loading price action…" />}

      {data && data.timeframes.length === 0 && (
        <EmptyState
          title="No spot OHLC data yet"
          hint="Run the historical backfill or start the live feed, then refresh."
        />
      )}

      {data && data.timeframes.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2">
          {data.timeframes.map((reading) => (
            <TimeframePanel key={reading.timeframe} reading={reading} />
          ))}
        </div>
      )}
    </div>
  );
}

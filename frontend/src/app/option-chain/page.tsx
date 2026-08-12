"use client";

import { useCallback, useEffect, useState } from "react";

import EmptyState from "@/components/EmptyState";
import StatCard from "@/components/StatCard";
import { ApiError, api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";
import type { OptionChainAnalysis } from "@/lib/types";

// option_chain/option_ohlc are stored under the NFO underlying name
// (e.g. "BANKNIFTY"), which differs from the NSE spot symbol
// ("NIFTY BANK") - see backend app/core/config.py:nfo_underlying.
const NFO_UNDERLYING = "BANKNIFTY";
const SPOT_SYMBOL = "NIFTY BANK";

const LIVE_POLL_MS = 5000; // matches the backend's live tick-aggregation cadence
const HISTORICAL_POLL_MS = 24 * 60 * 60 * 1000; // as_of is a fixed date - nothing to re-poll

export default function OptionChainPage() {
  const [expiries, setExpiries] = useState<string[]>([]);
  const [expiriesLoaded, setExpiriesLoaded] = useState(false);
  const [expiry, setExpiry] = useState("");
  const [asOf, setAsOf] = useState("");

  useEffect(() => {
    api
      .optionChainExpiries(NFO_UNDERLYING)
      .then((rows) => {
        setExpiries(rows);
        setExpiry((current) => current || rows[0] || "");
      })
      .catch(() => setExpiries([]))
      .finally(() => setExpiriesLoaded(true));
  }, []);

  const fetchAnalysis = useCallback(async (): Promise<OptionChainAnalysis | null> => {
    if (!expiry) return null;
    const spotRows = await api.spotOhlc({ symbol: SPOT_SYMBOL, interval: asOf ? "1d" : "5m", limit: 1 });
    const spotPrice = spotRows.at(-1)?.close;
    if (!spotPrice) return null;
    return api.optionChain(NFO_UNDERLYING, expiry, spotPrice, asOf || undefined).catch((err) => {
      if (err instanceof ApiError) return null;
      throw err;
    });
  }, [expiry, asOf]);

  const { data: analysis, loading } = usePolling(fetchAnalysis, asOf ? HISTORICAL_POLL_MS : LIVE_POLL_MS);
  const hasExpiries = expiriesLoaded && expiries.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-black">Option Chain</h1>
          <p className="mt-1 text-sm text-slate-600">
            {NFO_UNDERLYING} · PCR, Max Pain, and OI writing activity
            {!asOf && ` - refreshes every ${LIVE_POLL_MS / 1000}s`}.
          </p>
        </div>
        {analysis && (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-500" : "bg-green-600"} animate-pulse`} />
            as of {new Date(analysis.as_of).toLocaleString()}
          </div>
        )}
      </div>

      {expiriesLoaded && expiries.length === 0 ? (
        <EmptyState
          title="No option chain data at all"
          hint="Run `uv run backfill options` first (see backend/app/cli/backfill.py)."
        />
      ) : (
        <div className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <label className="flex flex-col gap-1 text-xs text-slate-500">
            Expiry
            <select
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-black"
            >
              {expiries.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-500">
            As of date (blank = live)
            <input
              type="date"
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
              className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-black"
            />
          </label>
          {asOf && (
            <button
              type="button"
              onClick={() => setAsOf("")}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700"
            >
              Back to live
            </button>
          )}
        </div>
      )}

      {!analysis && hasExpiries && (
        <EmptyState
          title={loading ? "Loading option chain…" : "No option chain snapshot found"}
          hint={
            loading
              ? undefined
              : "Try a different expiry or date - only backfilled/live-ingested points are available."
          }
        />
      )}

      {analysis && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Spot" value={analysis.spot_price.toFixed(2)} />
            <StatCard label="ATM Strike" value={analysis.atm_strike.toFixed(0)} />
            <StatCard label="PCR" value={analysis.pcr.toFixed(3)} />
            <StatCard label="Max Pain" value={analysis.max_pain.toFixed(0)} />
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm shadow-sm">
            <span className="text-slate-500">OI Signal: </span>
            <span className="font-semibold text-black">{analysis.oi_signal.replace("_", " ")}</span>
            <span className="ml-4 text-slate-500">Total CE OI: </span>
            <span className="font-semibold text-black">{analysis.total_ce_oi.toLocaleString()}</span>
            <span className="ml-4 text-slate-500">Total PE OI: </span>
            <span className="font-semibold text-black">{analysis.total_pe_oi.toLocaleString()}</span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-slate-100 text-xs font-semibold uppercase text-black">
                <tr>
                  <th className="px-3 py-2 text-right font-medium">CE OI</th>
                  <th className="px-3 py-2 text-right font-medium">CE Chg</th>
                  <th className="px-3 py-2 text-right font-medium">CE LTP</th>
                  <th className="px-3 py-2 text-center font-medium">Strike</th>
                  <th className="px-3 py-2 text-left font-medium">PE LTP</th>
                  <th className="px-3 py-2 text-left font-medium">PE Chg</th>
                  <th className="px-3 py-2 text-left font-medium">PE OI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {analysis.rows.map((row) => (
                  <tr
                    key={row.strike}
                    className={row.strike === analysis.atm_strike ? "bg-blue-50" : undefined}
                  >
                    <td className="px-3 py-2 text-right text-slate-600">{row.ce_oi.toLocaleString()}</td>
                    <td
                      className={`px-3 py-2 text-right ${row.ce_oi_change >= 0 ? "text-green-600" : "text-red-600"}`}
                    >
                      {row.ce_oi_change.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right text-black">{row.ce_ltp?.toFixed(2) ?? "—"}</td>
                    <td className="px-3 py-2 text-center font-semibold text-black">{row.strike}</td>
                    <td className="px-3 py-2 text-black">{row.pe_ltp?.toFixed(2) ?? "—"}</td>
                    <td
                      className={`px-3 py-2 ${row.pe_oi_change >= 0 ? "text-green-600" : "text-red-600"}`}
                    >
                      {row.pe_oi_change.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-slate-600">{row.pe_oi.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

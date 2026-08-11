import EmptyState from "@/components/EmptyState";
import StatCard from "@/components/StatCard";
import { api, ApiError } from "@/lib/api";

const DEFAULT_UNDERLYING = "NIFTY BANK";

function nextThursday(): string {
  const d = new Date();
  const day = d.getDay();
  const diff = (4 - day + 7) % 7 || 7;
  d.setDate(d.getDate() + diff);
  return d.toISOString().slice(0, 10);
}

export default async function OptionChainPage({
  searchParams,
}: {
  searchParams: Promise<{ expiry?: string; spot?: string }>;
}) {
  const params = await searchParams;
  const expiry = params.expiry ?? nextThursday();
  const spotPrice = Number(params.spot ?? 50000);

  const analysis = await api.optionChain(DEFAULT_UNDERLYING, expiry, spotPrice).catch((err) => {
    if (err instanceof ApiError) return null;
    throw err;
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-100">Option Chain</h1>
        <p className="mt-1 text-sm text-neutral-500">
          {DEFAULT_UNDERLYING} · Expiry {expiry} · PCR, Max Pain, and OI writing activity.
        </p>
      </div>

      {!analysis ? (
        <EmptyState
          title="No option chain snapshot found"
          hint="Ingest a live/historical option_chain snapshot for this underlying and expiry, then reload."
        />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatCard label="Spot" value={analysis.spot_price.toFixed(2)} />
            <StatCard label="ATM Strike" value={analysis.atm_strike.toFixed(0)} />
            <StatCard label="PCR" value={analysis.pcr.toFixed(3)} />
            <StatCard label="Max Pain" value={analysis.max_pain.toFixed(0)} />
          </div>

          <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4 text-sm">
            <span className="text-neutral-500">OI Signal: </span>
            <span className="font-medium text-neutral-100">{analysis.oi_signal.replace("_", " ")}</span>
            <span className="ml-4 text-neutral-500">Total CE OI: </span>
            <span className="font-medium">{analysis.total_ce_oi.toLocaleString()}</span>
            <span className="ml-4 text-neutral-500">Total PE OI: </span>
            <span className="font-medium">{analysis.total_pe_oi.toLocaleString()}</span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-neutral-800">
            <table className="w-full text-sm">
              <thead className="bg-neutral-900/60 text-xs uppercase text-neutral-500">
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
              <tbody className="divide-y divide-neutral-800">
                {analysis.rows.map((row) => (
                  <tr
                    key={row.strike}
                    className={row.strike === analysis.atm_strike ? "bg-emerald-500/5" : undefined}
                  >
                    <td className="px-3 py-2 text-right text-neutral-400">{row.ce_oi.toLocaleString()}</td>
                    <td
                      className={`px-3 py-2 text-right ${row.ce_oi_change >= 0 ? "text-emerald-400" : "text-red-400"}`}
                    >
                      {row.ce_oi_change.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right">{row.ce_ltp?.toFixed(2) ?? "—"}</td>
                    <td className="px-3 py-2 text-center font-medium text-neutral-100">{row.strike}</td>
                    <td className="px-3 py-2">{row.pe_ltp?.toFixed(2) ?? "—"}</td>
                    <td
                      className={`px-3 py-2 ${row.pe_oi_change >= 0 ? "text-emerald-400" : "text-red-400"}`}
                    >
                      {row.pe_oi_change.toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-neutral-400">{row.pe_oi.toLocaleString()}</td>
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

import EmptyState from "@/components/EmptyState";
import { api } from "@/lib/api";
import type { TradeExecution } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  OPEN: "bg-blue-600 text-white",
  CLOSED: "bg-slate-500 text-white",
  CANCELLED: "bg-red-600 text-white",
};

export default async function TradesPage() {
  const trades = await api.trades(100).catch((): TradeExecution[] => []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-black">Trades</h1>
        <p className="mt-1 text-sm text-slate-600">Executed trades across backtest, paper, and live modes.</p>
      </div>

      {trades.length === 0 ? (
        <EmptyState title="No trades yet" hint="Trades placed by the Paper or Live Trading Engine will appear here." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left text-xs font-semibold uppercase text-black">
              <tr>
                <th className="px-4 py-2 font-medium">Symbol</th>
                <th className="px-4 py-2 font-medium">Mode</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Qty</th>
                <th className="px-4 py-2 font-medium">Entry</th>
                <th className="px-4 py-2 font-medium">Exit</th>
                <th className="px-4 py-2 font-medium">P&amp;L</th>
                <th className="px-4 py-2 font-medium">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {trades.map((t) => (
                <tr key={t.order_id}>
                  <td className="px-4 py-2 font-semibold text-black">
                    {t.symbol} <span className="font-normal text-slate-500">{t.option_type}</span>
                  </td>
                  <td className="px-4 py-2 text-slate-600">{t.mode}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[t.status]}`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-black">{t.quantity}</td>
                  <td className="px-4 py-2 text-black">{t.entry_price.toFixed(2)}</td>
                  <td className="px-4 py-2 text-black">{t.exit_price?.toFixed(2) ?? "—"}</td>
                  <td
                    className={`px-4 py-2 font-semibold ${
                      (t.pnl ?? 0) > 0 ? "text-green-600" : (t.pnl ?? 0) < 0 ? "text-red-600" : "text-black"
                    }`}
                  >
                    {t.pnl?.toFixed(2) ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-500">{t.exit_reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

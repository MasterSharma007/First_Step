import EmptyState from "@/components/EmptyState";
import { api } from "@/lib/api";
import type { TradeExecution } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  OPEN: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  CLOSED: "bg-neutral-500/15 text-neutral-300 border-neutral-500/30",
  CANCELLED: "bg-red-500/15 text-red-400 border-red-500/30",
};

export default async function TradesPage() {
  const trades = await api.trades(100).catch((): TradeExecution[] => []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-100">Trades</h1>
        <p className="mt-1 text-sm text-neutral-500">Executed trades across backtest, paper, and live modes.</p>
      </div>

      {trades.length === 0 ? (
        <EmptyState title="No trades yet" hint="Trades placed by the Paper or Live Trading Engine will appear here." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-900/60 text-left text-xs uppercase text-neutral-500">
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
            <tbody className="divide-y divide-neutral-800">
              {trades.map((t) => (
                <tr key={t.order_id}>
                  <td className="px-4 py-2 font-medium text-neutral-100">
                    {t.symbol} <span className="text-neutral-500">{t.option_type}</span>
                  </td>
                  <td className="px-4 py-2 text-neutral-400">{t.mode}</td>
                  <td className="px-4 py-2">
                    <span className={`rounded border px-2 py-0.5 text-xs ${STATUS_STYLE[t.status]}`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="px-4 py-2">{t.quantity}</td>
                  <td className="px-4 py-2">{t.entry_price.toFixed(2)}</td>
                  <td className="px-4 py-2">{t.exit_price?.toFixed(2) ?? "—"}</td>
                  <td
                    className={`px-4 py-2 font-medium ${
                      (t.pnl ?? 0) > 0 ? "text-emerald-400" : (t.pnl ?? 0) < 0 ? "text-red-400" : ""
                    }`}
                  >
                    {t.pnl?.toFixed(2) ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-neutral-500">{t.exit_reason ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

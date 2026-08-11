import BacktestForm from "@/components/BacktestForm";
import EmptyState from "@/components/EmptyState";
import { api } from "@/lib/api";
import type { BacktestResultOut } from "@/lib/types";

export default async function BacktestPage() {
  const results = await api.backtestResults(20).catch((): BacktestResultOut[] => []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-100">Backtesting</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Run the strategy against historical spot data and review win rate, profit factor, drawdown, and Sharpe ratio.
        </p>
      </div>

      <BacktestForm />

      {results.length === 0 ? (
        <EmptyState
          title="No backtest runs yet"
          hint="Backfill spot_ohlc history, then run a backtest above."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-800 text-left text-xs font-semibold uppercase text-neutral-300">
              <tr>
                <th className="px-4 py-2 font-medium">Strategy</th>
                <th className="px-4 py-2 font-medium">Range</th>
                <th className="px-4 py-2 font-medium">Trades</th>
                <th className="px-4 py-2 font-medium">Win Rate</th>
                <th className="px-4 py-2 font-medium">Profit Factor</th>
                <th className="px-4 py-2 font-medium">Max Drawdown</th>
                <th className="px-4 py-2 font-medium">Sharpe</th>
                <th className="px-4 py-2 font-medium">Net P&amp;L</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {results.map((r) => (
                <tr key={r.run_id}>
                  <td className="px-4 py-2 font-medium text-neutral-100">{r.strategy_name}</td>
                  <td className="px-4 py-2 text-neutral-400">
                    {r.start_date} → {r.end_date}
                  </td>
                  <td className="px-4 py-2">{r.total_trades}</td>
                  <td className="px-4 py-2">{r.win_rate.toFixed(1)}%</td>
                  <td className="px-4 py-2">{r.profit_factor.toFixed(2)}</td>
                  <td className="px-4 py-2 text-red-400">{r.max_drawdown.toFixed(2)}</td>
                  <td className="px-4 py-2">{r.sharpe_ratio.toFixed(2)}</td>
                  <td
                    className={`px-4 py-2 font-medium ${r.net_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}
                  >
                    {r.net_pnl.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

import EmptyState from "@/components/EmptyState";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";

export default async function ReportsPage() {
  const [report, rangeReport] = await Promise.all([
    api.dailyReport().catch(() => null),
    api.rangeReport().catch(() => []),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-black">Daily Report</h1>
        <p className="mt-1 text-sm text-slate-600">
          {report ? report.report_date : "Today"} · Trades, win rate, net profit, and drawdown.
        </p>
      </div>

      {!report ? (
        <EmptyState title="No report data yet" hint="Close some trades to see today's report." />
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
          <StatCard label="Total Trades" value={String(report.total_trades)} />
          <StatCard label="Win Rate" value={`${report.win_rate.toFixed(1)}%`} />
          <StatCard
            label="Net Profit"
            value={report.net_profit.toFixed(2)}
            accent={report.net_profit >= 0 ? "positive" : "negative"}
          />
          <StatCard label="Charges" value={report.charges.toFixed(2)} />
          <StatCard label="Max Drawdown" value={report.max_drawdown.toFixed(2)} accent="negative" />
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold text-black">Date-wise Profit</h2>
        <p className="mt-1 text-sm text-slate-600">Net profit per day over the last 30 days.</p>
      </div>

      {rangeReport.length === 0 ? (
        <EmptyState title="No date-wise data yet" hint="Close some trades to see profit broken down by day." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-100 text-left text-xs font-semibold uppercase text-black">
              <tr>
                <th className="px-4 py-2 font-medium">Date</th>
                <th className="px-4 py-2 font-medium">Trades</th>
                <th className="px-4 py-2 font-medium">Win Rate</th>
                <th className="px-4 py-2 font-medium">Net Profit</th>
                <th className="px-4 py-2 font-medium">Charges</th>
                <th className="px-4 py-2 font-medium">Max Drawdown</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {rangeReport.map((r) => (
                <tr key={r.report_date}>
                  <td className="px-4 py-2 font-semibold text-black">{r.report_date}</td>
                  <td className="px-4 py-2 text-black">{r.total_trades}</td>
                  <td className="px-4 py-2 text-black">{r.win_rate.toFixed(1)}%</td>
                  <td
                    className={`px-4 py-2 font-semibold ${
                      r.net_profit > 0 ? "text-green-600" : r.net_profit < 0 ? "text-red-600" : "text-black"
                    }`}
                  >
                    {r.net_profit.toFixed(2)}
                  </td>
                  <td className="px-4 py-2 text-black">{r.charges.toFixed(2)}</td>
                  <td className="px-4 py-2 text-red-600">{r.max_drawdown.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

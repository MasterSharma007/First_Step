import EmptyState from "@/components/EmptyState";
import StatCard from "@/components/StatCard";
import { api } from "@/lib/api";

export default async function ReportsPage() {
  const report = await api.dailyReport().catch(() => null);

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
    </div>
  );
}

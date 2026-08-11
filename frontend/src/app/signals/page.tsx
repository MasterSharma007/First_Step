import EmptyState from "@/components/EmptyState";
import SignalBadge from "@/components/SignalBadge";
import { api } from "@/lib/api";
import type { TradeSignal } from "@/lib/types";

export default async function SignalsPage() {
  const signals = await api.signals(100).catch((): TradeSignal[] => []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-neutral-100">Signals</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Output of the Signal Generation Engine - entries, exits, and confidence scores.
        </p>
      </div>

      {signals.length === 0 ? (
        <EmptyState title="No signals yet" hint="The Signal Engine hasn't emitted any signals." />
      ) : (
        <div className="overflow-hidden rounded-lg border border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-900/60 text-left text-xs uppercase text-neutral-500">
              <tr>
                <th className="px-4 py-2 font-medium">Time</th>
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium">Strike</th>
                <th className="px-4 py-2 font-medium">Entry</th>
                <th className="px-4 py-2 font-medium">SL</th>
                <th className="px-4 py-2 font-medium">Target</th>
                <th className="px-4 py-2 font-medium">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {signals.map((s) => (
                <tr key={s.signal_id}>
                  <td className="px-4 py-2 text-neutral-400">
                    {new Date(s.entry_time).toLocaleString()}
                  </td>
                  <td className="px-4 py-2">
                    <SignalBadge type={s.signal_type} />
                  </td>
                  <td className="px-4 py-2">{s.strike ?? "—"}</td>
                  <td className="px-4 py-2">{s.entry_price.toFixed(2)}</td>
                  <td className="px-4 py-2 text-red-400">{s.stop_loss?.toFixed(2) ?? "—"}</td>
                  <td className="px-4 py-2 text-emerald-400">{s.target?.toFixed(2) ?? "—"}</td>
                  <td className="px-4 py-2 font-medium">{s.confidence_score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function StatCard({
  label,
  value,
  accent = "neutral",
}: {
  label: string;
  value: string;
  accent?: "neutral" | "positive" | "negative";
}) {
  const accentClass =
    accent === "positive"
      ? "text-emerald-400"
      : accent === "negative"
        ? "text-red-400"
        : "text-neutral-100";

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-4">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${accentClass}`}>{value}</div>
    </div>
  );
}

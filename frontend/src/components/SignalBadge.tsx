import type { SignalType } from "@/lib/types";

const STYLES: Record<string, string> = {
  CE_ENTRY: "bg-green-600 text-white",
  PE_ENTRY: "bg-red-600 text-white",
  EXIT: "bg-slate-500 text-white",
  PARTIAL_EXIT: "bg-amber-500 text-white",
  SL_UPDATE: "bg-blue-600 text-white",
};

export default function SignalBadge({ type }: { type: SignalType }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-semibold ${STYLES[type] ?? STYLES.EXIT}`}>
      {type.replace("_", " ")}
    </span>
  );
}

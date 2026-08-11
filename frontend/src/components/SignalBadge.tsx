import type { SignalType } from "@/lib/types";

const STYLES: Record<string, string> = {
  CE_ENTRY: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  PE_ENTRY: "bg-red-500/15 text-red-400 border-red-500/30",
  EXIT: "bg-neutral-500/15 text-neutral-300 border-neutral-500/30",
  PARTIAL_EXIT: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  SL_UPDATE: "bg-sky-500/15 text-sky-400 border-sky-500/30",
};

export default function SignalBadge({ type }: { type: SignalType }) {
  return (
    <span className={`rounded border px-2 py-0.5 text-xs font-medium ${STYLES[type] ?? STYLES.EXIT}`}>
      {type.replace("_", " ")}
    </span>
  );
}

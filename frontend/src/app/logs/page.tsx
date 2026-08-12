"use client";

import { useState } from "react";

import EmptyState from "@/components/EmptyState";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";

const POLL_MS = 5000;

const LEVEL_STYLE: Record<string, string> = {
  debug: "text-slate-500",
  info: "text-blue-600",
  warning: "text-amber-600",
  error: "text-red-600",
  critical: "text-red-600",
};

export default function LogsPage() {
  const [level, setLevel] = useState("");
  const { data: logs, error } = usePolling(() => api.logsTail({ lines: 300, level: level || undefined }), POLL_MS);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-black">Logs</h1>
          <p className="mt-1 text-sm text-slate-600">Backend log tail - refreshes every {POLL_MS / 1000}s.</p>
        </div>
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-black"
        >
          <option value="">All levels</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
          <option value="debug">Debug</option>
        </select>
      </div>

      {error && <EmptyState title="Can't load logs" hint={error.message} />}

      {logs && logs.length === 0 && (
        <EmptyState title="No log entries yet" hint="Logs write to backend/logs/app.log once the backend runs." />
      )}

      {logs && logs.length > 0 && (
        <div className="max-h-[70vh] overflow-y-auto rounded-lg border border-slate-200 bg-white font-mono text-xs shadow-sm">
          {[...logs].reverse().map((entry, i) => (
            <div key={i} className="flex gap-3 border-b border-slate-100 px-3 py-1.5 hover:bg-slate-50">
              <span className="shrink-0 text-slate-400">
                {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : "—"}
              </span>
              <span className={`shrink-0 w-14 uppercase font-semibold ${LEVEL_STYLE[entry.level] ?? "text-slate-600"}`}>
                {entry.level}
              </span>
              <span className="break-all text-black">{entry.event}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

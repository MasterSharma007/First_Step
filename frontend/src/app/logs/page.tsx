"use client";

import { useState } from "react";

import EmptyState from "@/components/EmptyState";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/usePolling";

const POLL_MS = 5000;

const LEVEL_STYLE: Record<string, string> = {
  debug: "text-neutral-500",
  info: "text-sky-400",
  warning: "text-amber-400",
  error: "text-red-400",
  critical: "text-red-400",
};

export default function LogsPage() {
  const [level, setLevel] = useState("");
  const { data: logs, error } = usePolling(() => api.logsTail({ lines: 300, level: level || undefined }), POLL_MS);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-neutral-100">Logs</h1>
          <p className="mt-1 text-sm text-neutral-500">Backend log tail - refreshes every {POLL_MS / 1000}s.</p>
        </div>
        <select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-200"
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
        <div className="max-h-[70vh] overflow-y-auto rounded-lg border border-neutral-800 bg-neutral-950 font-mono text-xs">
          {[...logs].reverse().map((entry, i) => (
            <div key={i} className="flex gap-3 border-b border-neutral-900 px-3 py-1.5 hover:bg-neutral-900/50">
              <span className="shrink-0 text-neutral-600">
                {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : "—"}
              </span>
              <span className={`shrink-0 w-14 uppercase ${LEVEL_STYLE[entry.level] ?? "text-neutral-400"}`}>
                {entry.level}
              </span>
              <span className="break-all text-neutral-300">{entry.event}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

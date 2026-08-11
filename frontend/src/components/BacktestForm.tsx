"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, ApiError } from "@/lib/api";

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export default function BacktestForm() {
  const router = useRouter();
  const [startDate, setStartDate] = useState(isoDaysAgo(30));
  const [endDate, setEndDate] = useState(isoDaysAgo(0));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.runBacktest({ strategy_name: "default", start_date: startDate, end_date: endDate });
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to run backtest");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4 rounded-lg border border-neutral-800 bg-neutral-900/30 p-4">
      <label className="flex flex-col gap-1 text-xs text-neutral-500">
        Start date
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-200"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-neutral-500">
        End date
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="rounded border border-neutral-700 bg-neutral-950 px-2 py-1 text-sm text-neutral-200"
        />
      </label>
      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-emerald-500 px-4 py-1.5 text-sm font-medium text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
      >
        {submitting ? "Running…" : "Run Backtest"}
      </button>
      {error && <span className="text-sm text-red-400">{error}</span>}
    </form>
  );
}

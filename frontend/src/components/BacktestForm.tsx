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
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        Start date
        <input
          type="date"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-black"
        />
      </label>
      <label className="flex flex-col gap-1 text-xs text-slate-500">
        End date
        <input
          type="date"
          value={endDate}
          onChange={(e) => setEndDate(e.target.value)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-black"
        />
      </label>
      <button
        type="submit"
        disabled={submitting}
        className="rounded bg-blue-600 px-4 py-1.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {submitting ? "Running…" : "Run Backtest"}
      </button>
      {error && <span className="text-sm text-red-600">{error}</span>}
    </form>
  );
}

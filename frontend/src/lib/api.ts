import type {
  BacktestRequest,
  BacktestResultOut,
  DailyReport,
  LiveStatus,
  LogEntry,
  MultiTimeframe,
  OptionChainAnalysis,
  PriceAction,
  SpotOHLC,
  TradeExecution,
  TradeSignal,
  Trend,
} from "./types";

// Server components run inside the frontend container, where the browser-facing
// `localhost:<host-port>` URL doesn't reach the backend container - they need the
// Docker network's service name instead.
const API_BASE_URL =
  typeof window === "undefined"
    ? (process.env.API_INTERNAL_URL ?? "http://backend:8000/api/v1")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1");

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  spotOhlc: (params: { interval?: string; symbol?: string; limit?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.interval) query.set("interval", params.interval);
    if (params.symbol) query.set("symbol", params.symbol);
    if (params.limit) query.set("limit", String(params.limit));
    return request<SpotOHLC[]>(`/market-data/spot-ohlc?${query.toString()}`);
  },

  trend: (params: { symbol?: string; interval?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.symbol) query.set("symbol", params.symbol);
    if (params.interval) query.set("interval", params.interval);
    return request<Trend>(`/market-data/trend?${query.toString()}`);
  },

  multiTimeframe: (symbol = "NIFTY BANK") =>
    request<MultiTimeframe>(`/market-data/multi-timeframe?symbol=${encodeURIComponent(symbol)}`),

  priceAction: (symbol = "NIFTY BANK") =>
    request<PriceAction>(`/market-data/price-action?symbol=${encodeURIComponent(symbol)}`),

  optionChainExpiries: (underlying: string) =>
    request<string[]>(`/option-chain/${encodeURIComponent(underlying)}/expiries`),

  optionChain: (underlying: string, expiry: string, spotPrice: number, asOf?: string) => {
    const query = new URLSearchParams({ spot_price: String(spotPrice) });
    if (asOf) query.set("as_of", asOf);
    return request<OptionChainAnalysis>(
      `/option-chain/${encodeURIComponent(underlying)}/${expiry}?${query.toString()}`,
    );
  },

  signals: (limit = 50) => request<TradeSignal[]>(`/signals?limit=${limit}`),

  trades: (limit = 50) => request<TradeExecution[]>(`/trades?limit=${limit}`),

  runBacktest: (payload: BacktestRequest) =>
    request<BacktestResultOut>("/backtest/run", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  backtestResults: (limit = 20) => request<BacktestResultOut[]>(`/backtest/results?limit=${limit}`),

  dailyReport: (reportDate?: string) =>
    request<DailyReport>(`/reports/daily${reportDate ? `?report_date=${reportDate}` : ""}`),

  rangeReport: (params: { startDate?: string; endDate?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.startDate) query.set("start_date", params.startDate);
    if (params.endDate) query.set("end_date", params.endDate);
    return request<DailyReport[]>(`/reports/range?${query.toString()}`);
  },

  liveStatus: () => request<LiveStatus>("/live/status"),

  logsTail: (params: { lines?: number; level?: string } = {}) => {
    const query = new URLSearchParams();
    if (params.lines) query.set("lines", String(params.lines));
    if (params.level) query.set("level", params.level);
    return request<LogEntry[]>(`/logs/tail?${query.toString()}`);
  },
};

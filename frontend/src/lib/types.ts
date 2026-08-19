export interface SpotOHLC {
  symbol: string;
  interval: string;
  datetime_: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type TrendDirection = "BULLISH" | "BEARISH" | "NEUTRAL";

export interface Trend {
  symbol: string;
  interval: string;
  as_of: string;
  direction: TrendDirection;
  reasons: string[];
  support: number;
  resistance: number;
  current_price: number;
}

export interface OptionChainRow {
  strike: number;
  ce_ltp: number | null;
  ce_oi: number;
  ce_oi_change: number;
  ce_volume: number;
  ce_iv: number | null;
  pe_ltp: number | null;
  pe_oi: number;
  pe_oi_change: number;
  pe_volume: number;
  pe_iv: number | null;
}

export interface OptionChainAnalysis {
  underlying: string;
  expiry: string;
  as_of: string;
  spot_price: number;
  atm_strike: number;
  pcr: number;
  max_pain: number;
  total_ce_oi: number;
  total_pe_oi: number;
  rows: OptionChainRow[];
  oi_signal: string;
}

export type SignalType = "CE_ENTRY" | "PE_ENTRY" | "EXIT" | "PARTIAL_EXIT" | "SL_UPDATE";

export interface TradeSignal {
  signal_id: string;
  entry_time: string;
  underlying: string;
  strike: number | null;
  expiry: string | null;
  signal_type: SignalType;
  entry_price: number;
  stop_loss: number | null;
  target: number | null;
  confidence_score: number;
  reasons: Record<string, number | string> | null;
}

export type TradeMode = "BACKTEST" | "PAPER" | "LIVE";
export type TradeStatus = "OPEN" | "CLOSED" | "CANCELLED";

export interface TradeExecution {
  order_id: string;
  mode: TradeMode;
  status: TradeStatus;
  symbol: string;
  option_type: string;
  quantity: number;
  entry_time: string;
  entry_price: number;
  exit_time: string | null;
  exit_price: number | null;
  stop_loss: number | null;
  target: number | null;
  pnl: number | null;
  charges: number;
  exit_reason: string | null;
}

export interface BacktestRequest {
  strategy_name: string;
  start_date: string;
  end_date: string;
  underlying?: string;
  initial_capital?: number;
  params?: Record<string, unknown>;
}

export interface BacktestResultOut {
  run_id: string;
  strategy_name: string;
  start_date: string;
  end_date: string;
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  sharpe_ratio: number;
  net_pnl: number;
}

export interface DailyReport {
  report_date: string;
  total_trades: number;
  win_rate: number;
  net_profit: number;
  charges: number;
  max_drawdown: number;
}

export interface SignalSuggestion {
  signal_type: "CE_ENTRY" | "PE_ENTRY" | "NO_TRADE";
  verdict: string;
  confidence_score: number;
  strike: number | null;
  option_type: string | null;
  entry_price: number | null;
  stop_loss: number | null;
  target: number | null;
  reasons: Record<string, number | string>;
}

export interface LiveOpenPosition {
  order_id: string;
  symbol: string;
  option_type: string;
  quantity: number;
  entry_price: number;
  current_price: number | null;
  stop_loss: number | null;
  target: number | null;
  unrealized_pnl: number | null;
  entry_time: string;
}

export interface LiveStatus {
  as_of: string;
  spot_price: number;
  trend_direction: TrendDirection;
  trend_reasons: string[];
  support: number;
  resistance: number;
  expiry: string | null;
  atm_strike: number | null;
  pcr: number | null;
  max_pain: number | null;
  oi_signal: string | null;
  india_vix: number;
  signal: SignalSuggestion;
  open_positions: LiveOpenPosition[];
  today_realized_pnl: number;
  today_trade_count: number;
  live_loop_enabled: boolean;
  trading_mode: "PAPER" | "LIVE";
}

export interface TimeframeReading {
  timeframe: string; // 15m, 1h, 1d, 1w, 1M
  bars_available: number;
  insufficient_data: boolean;
  support: number | null;
  resistance: number | null;
  direction: TrendDirection | null;
  reasons: string[] | null;
}

export interface MultiTimeframe {
  symbol: string;
  current_price: number;
  timeframes: TimeframeReading[];
}

export interface CandleBreak {
  direction: "UP" | "DOWN" | null;
  reference_high: number;
  reference_low: number;
  reference_time: string;
}

export type SwingKind = "HH" | "LH" | "HL" | "LL";

export interface SwingPoint {
  kind: SwingKind;
  price: number;
  time: string;
}

export interface PriceActionReading {
  timeframe: string; // 5m, 15m
  current_price: number;
  candle_break: CandleBreak | null;
  sr_break: "SUPPORT_BREAK" | "RESISTANCE_BREAK" | null;
  support: number | null;
  resistance: number | null;
  swing_points: SwingPoint[];
  structure: SwingKind | null;
}

export interface PriceAction {
  symbol: string;
  current_price: number;
  timeframes: PriceActionReading[];
}

export interface LogEntry {
  timestamp: string | null;
  level: string;
  event: string;
  logger?: string;
  [key: string]: unknown;
}

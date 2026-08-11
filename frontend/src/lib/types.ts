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

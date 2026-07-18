"""analysis/backtest.py – Historical backtesting of valuation signals."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Summary statistics from a backtest run."""
    ticker: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_return_per_trade: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: pd.DataFrame
    equity_curve: pd.Series
    warnings: List[str] = field(default_factory=list)


class Backtester:
    """Simple price-based backtester for valuation signals.

    Logic
    -----
    1. For each rebalance date, run valuation_fn(historical_data_slice) -> signal.
    2. If signal == BUY  -> go long (or add to position).
    3. If signal == SELL -> close long (or go flat).
    4. Compute equity curve and performance metrics.
    """

    def __init__(
        self,
        buy_signal: str = "BUY",
        sell_signal: str = "SELL",
        initial_capital: float = 100_000.0,
        position_size: float = 1.0,   # fraction of capital per trade
        risk_free_rate: float = 0.04,  # annualised for Sharpe
        periods_per_year: int = 252,
    ) -> None:
        self.buy_signal = buy_signal
        self.sell_signal = sell_signal
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.risk_free_rate = risk_free_rate
        self.periods_per_year = periods_per_year

    def run(
        self,
        price_series: pd.Series,
        signal_series: pd.Series,
        ticker: str = "TICKER",
    ) -> BacktestResult:
        """Execute backtest.

        Parameters
        ----------
        price_series : pd.Series
            Indexed by date, values = closing prices.
        signal_series : pd.Series
            Indexed by date (subset of price_series), values = 'BUY'/'HOLD'/'SELL'.
        ticker : str
        """
        warnings: List[str] = []

        if price_series.empty:
            return self._empty_result(ticker, warnings, "Empty price series.")

        # Align signals onto price index (forward-fill so signal persists)
        signals = signal_series.reindex(price_series.index).ffill().fillna("HOLD")

        capital = self.initial_capital
        position = 0.0  # shares held
        equity: List[float] = []
        trades: List[Dict] = []

        for date, price in price_series.items():
            sig = signals.get(date, "HOLD")
            eq = capital + position * price
            equity.append(eq)

            if sig == self.buy_signal and position == 0:
                shares = (capital * self.position_size) / price
                cost = shares * price
                capital -= cost
                position = shares
                trades.append({"date": date, "type": "BUY", "price": price, "shares": shares})

            elif sig == self.sell_signal and position > 0:
                proceeds = position * price
                capital += proceeds
                trades.append({"date": date, "type": "SELL", "price": price, "shares": position})
                position = 0.0

        # Close any open position at last price
        if position > 0:
            last_price = price_series.iloc[-1]
            capital += position * last_price
            trades.append({"date": price_series.index[-1], "type": "SELL_CLOSE",
                           "price": last_price, "shares": position})
            position = 0.0

        equity_curve = pd.Series(equity, index=price_series.index)
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame(
            columns=["date", "type", "price", "shares"]
        )

        # ---- Performance metrics ----------------------------------------
        buys = trades_df[trades_df["type"] == "BUY"]
        sells = trades_df[trades_df["type"].isin(["SELL", "SELL_CLOSE"])]
        n_trades = min(len(buys), len(sells))

        returns = []
        for i in range(n_trades):
            buy_price = buys.iloc[i]["price"]
            sell_price = sells.iloc[i]["price"]
            returns.append((sell_price - buy_price) / buy_price)

        winning = [r for r in returns if r > 0]
        losing  = [r for r in returns if r <= 0]
        win_rate = len(winning) / n_trades if n_trades else 0.0
        avg_return = float(np.mean(returns)) if returns else 0.0
        total_return = (capital - self.initial_capital) / self.initial_capital

        daily_returns = equity_curve.pct_change().dropna()
        mdd = self._max_drawdown(equity_curve)
        sharpe = self._sharpe(daily_returns)

        return BacktestResult(
            ticker=ticker,
            total_trades=n_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=round(win_rate, 4),
            avg_return_per_trade=round(avg_return, 4),
            total_return=round(total_return, 4),
            max_drawdown=round(mdd, 4),
            sharpe_ratio=round(sharpe, 4),
            trades=trades_df,
            equity_curve=equity_curve,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _max_drawdown(equity: pd.Series) -> float:
        roll_max = equity.cummax()
        drawdown = (equity - roll_max) / roll_max
        return float(drawdown.min())

    def _sharpe(self, daily_returns: pd.Series) -> float:
        if daily_returns.empty or daily_returns.std() == 0:
            return 0.0
        excess = daily_returns - self.risk_free_rate / self.periods_per_year
        return float(excess.mean() / excess.std() * np.sqrt(self.periods_per_year))

    def _empty_result(self, ticker: str, warnings: list, msg: str) -> BacktestResult:
        warnings.append(msg)
        return BacktestResult(
            ticker=ticker,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_return_per_trade=0.0,
            total_return=0.0,
            max_drawdown=0.0,
            sharpe_ratio=0.0,
            trades=pd.DataFrame(),
            equity_curve=pd.Series(dtype=float),
            warnings=warnings,
        )

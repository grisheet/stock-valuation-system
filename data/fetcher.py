"""Data fetcher: downloads financial data via yfinance with retries and caching."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

import config
from data import cache


class DataFetchError(RuntimeError):
    """Raised when data cannot be retrieved after all retries."""


@dataclass
class CompanySnapshot:
    """All financial data needed by the valuation models."""
    ticker: str
    price: float
    shares_outstanding: float
    market_cap: float
    income_statement: pd.DataFrame        # columns = years, rows = line items
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    price_history: pd.DataFrame           # Date index, Close column
    info: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class MarketDataFetcher:
    """Fetches and caches financial data for one or more tickers."""

    def __init__(self):
        self._cache = cache

    def get_snapshot(self, ticker: str) -> CompanySnapshot:
        """Return a CompanySnapshot, using cache if available."""
        key = f"snapshot:{ticker}"
        cached = self._cache.get(key)
        if cached:
            return self._deserialise(cached)
        raw = self._fetch_snapshot_raw(ticker)
        self._cache.set(key, raw)
        return self._deserialise(raw)

    def get_peer_table(self, peer_tickers: List[str]) -> pd.DataFrame:
        """Fetch key multiples for a list of peer tickers.

        Rows that cannot be fetched are dropped (with the gap surfaced to the
        caller via fewer rows, never a silent NaN row)."""
        rows = []
        for t in peer_tickers:
            try:
                snap = self.get_snapshot(t)
            except DataFetchError:
                continue
            rows.append(self._compute_multiples_row(snap))
        return pd.DataFrame(rows)

    # ── Internals ────────────────────────────────────────────────────────────

    def _fetch_snapshot_raw(self, ticker: str) -> Dict[str, Any]:
        """Pulls everything from yfinance and serialises to JSON-safe
        primitives (DataFrames → records) so it can be cached as JSON."""

        def _pull():
            tk = yf.Ticker(ticker)
            info = tk.info or {}
            if not info or info.get("regularMarketPrice") is None and info.get(
                "currentPrice"
            ) is None and info.get("previousClose") is None:
                raise DataFetchError(f"No data found for ticker '{ticker}'.")
            return tk

        tk = self._retry(_pull)
        info = tk.info or {}

        price = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
            or info.get("previousClose")
            or float("nan")
        )
        shares = info.get("sharesOutstanding") or float("nan")
        market_cap = info.get("marketCap") or (price * shares if not np.isnan(price * shares) else float("nan"))

        hist = tk.history(period="5y", auto_adjust=True)

        return {
            "ticker": ticker,
            "price": price,
            "shares_outstanding": shares,
            "market_cap": market_cap,
            "income_statement": _df_to_records(tk.income_stmt),
            "balance_sheet": _df_to_records(tk.balance_sheet),
            "cash_flow": _df_to_records(tk.cashflow),
            "price_history": _df_to_records(hist[["Close"]] if "Close" in hist.columns else hist),
            "info": {k: v for k, v in info.items() if isinstance(v, (str, int, float, bool, type(None)))},
        }

    def _deserialise(self, raw: Dict[str, Any]) -> CompanySnapshot:
        return CompanySnapshot(
            ticker=raw["ticker"],
            price=raw["price"],
            shares_outstanding=raw["shares_outstanding"],
            market_cap=raw["market_cap"],
            income_statement=_records_to_df(raw.get("income_statement")),
            balance_sheet=_records_to_df(raw.get("balance_sheet")),
            cash_flow=_records_to_df(raw.get("cash_flow")),
            price_history=_records_to_df(raw.get("price_history")),
            info=raw.get("info", {}),
        )

    def _compute_multiples_row(self, snap: CompanySnapshot) -> Dict[str, Any]:
        info = snap.info
        return {
            "Ticker": snap.ticker,
            "Company": info.get("shortName", snap.ticker),
            "EV/EBITDA": info.get("enterpriseToEbitda"),
            "EV/Revenue": info.get("enterpriseToRevenue"),
            "P/E": info.get("trailingPE"),
            "P/B": info.get("priceToBook"),
        }

    @staticmethod
    def _retry(fn, retries: int = config.MAX_RETRIES, backoff: float = config.RETRY_BACKOFF):
        last_exc: Exception = RuntimeError("Unreachable")
        for attempt in range(retries):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < retries - 1:
                    time.sleep(backoff * (attempt + 1))
        raise DataFetchError(str(last_exc)) from last_exc


# ── Small module-level helpers ──────────────────────────────────────────────────────

def _df_to_records(df: pd.DataFrame) -> Dict[str, Any]:
    """Serialise a (possibly datetime-indexed/columned) DataFrame to a
    JSON-cacheable structure without losing the index."""
    if df is None or df.empty:
        return {"columns": [], "index": [], "data": []}
    d = df.copy()
    d.columns = [str(c) for c in d.columns]
    return {
        "columns": list(d.columns),
        "index": [str(i) for i in d.index],
        "data": d.astype(object).where(pd.notnull(d), None).values.tolist(),
    }


def _records_to_df(payload: Optional[Dict[str, Any]]) -> pd.DataFrame:
    if not payload or not payload.get("columns"):
        return pd.DataFrame()
    return pd.DataFrame(payload["data"], columns=payload["columns"], index=payload["index"])


def _latest_value(df: pd.DataFrame, row_candidates: List[str]) -> Optional[float]:
    """Financial statement rows are inconsistently named across tickers
    (e.g. 'EBITDA' vs 'Normalized EBITDA') – try each candidate label and
    return the most recent (first) column value for the first match."""
    if df is None or df.empty:
        return None
    for label in row_candidates:
        if label in df.index:
            val = df.loc[label].iloc[0]
            return float(val) if val is not None and not (isinstance(val, float) and np.isnan(val)) else None
    return None

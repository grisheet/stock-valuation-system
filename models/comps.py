"""models/comps.py – Comparable-company (trading comps) analysis."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CompsResult:
    """Results container for comparable-company analysis."""
    implied_price_ev_ebitda: float
    implied_price_pe: float
    implied_price_ps: float
    implied_price_pb: float
    blended_price: float
    peer_multiples: pd.DataFrame
    target_metrics: Dict[str, float]
    assumptions: Dict[str, object] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class CompsModel:
    """Trading comps valuation using EV/EBITDA, P/E, P/S and P/B multiples."""

    # Default peer-multiple weights for blended price
    _WEIGHTS: Dict[str, float] = {
        "ev_ebitda": 0.35,
        "pe": 0.30,
        "ps": 0.20,
        "pb": 0.15,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self.weights = weights or self._WEIGHTS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(
        self,
        target_ticker: str,
        target_info: Dict[str, object],
        peers_info: List[Dict[str, object]],
        use_median: bool = True,
    ) -> CompsResult:
        """Run comps valuation.

        Parameters
        ----------
        target_ticker: str
            Ticker symbol of the company being valued.
        target_info: dict
            Financial data for the target (from data.fetcher).
        peers_info: list[dict]
            Financial data for each peer company.
        use_median: bool
            Use median (True) or mean (False) peer multiples.
        """
        warnings: List[str] = []

        # ---- Build peer-multiples table ---------------------------------
        peer_rows = []
        for p in peers_info:
            row = self._extract_multiples(p)
            if row:
                peer_rows.append(row)

        if not peer_rows:
            return CompsResult(
                implied_price_ev_ebitda=float("nan"),
                implied_price_pe=float("nan"),
                implied_price_ps=float("nan"),
                implied_price_pb=float("nan"),
                blended_price=float("nan"),
                peer_multiples=pd.DataFrame(),
                target_metrics={},
                warnings=warnings,
                error="No valid peer data available.",
            )

        peers_df = pd.DataFrame(peer_rows)
        agg = peers_df.median(numeric_only=True) if use_median else peers_df.mean(numeric_only=True)

        # ---- Target operating metrics -----------------------------------
        target_metrics = self._extract_target_metrics(target_info)
        shares = float(target_info.get("sharesOutstanding") or target_info.get("shares_outstanding") or 0)
        if shares <= 0:
            warnings.append("Shares outstanding unavailable; per-share prices set to NaN.")

        # ---- Implied prices per methodology -----------------------------
        p_ev_ebitda = self._price_from_ev_ebitda(agg, target_metrics, target_info, shares, warnings)
        p_pe = self._price_from_pe(agg, target_metrics, shares, warnings)
        p_ps = self._price_from_ps(agg, target_metrics, shares, warnings)
        p_pb = self._price_from_pb(agg, target_metrics, shares, warnings)

        blended = self._blend(
            {"ev_ebitda": p_ev_ebitda, "pe": p_pe, "ps": p_ps, "pb": p_pb}
        )

        assumptions = {
            "aggregation": "median" if use_median else "mean",
            "weights": self.weights,
            "peer_count": len(peer_rows),
            "target_ticker": target_ticker,
        }

        return CompsResult(
            implied_price_ev_ebitda=p_ev_ebitda,
            implied_price_pe=p_pe,
            implied_price_ps=p_ps,
            implied_price_pb=p_pb,
            blended_price=blended,
            peer_multiples=peers_df,
            target_metrics=target_metrics,
            assumptions=assumptions,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_float(d: dict, *keys) -> Optional[float]:
        for k in keys:
            v = d.get(k)
            if v is not None:
                try:
                    f = float(v)
                    if not np.isnan(f):
                        return f
                except (TypeError, ValueError):
                    pass
        return None

    def _extract_multiples(self, info: dict) -> Optional[dict]:
        ticker = info.get("symbol") or info.get("ticker", "unknown")
        ev_ebitda = self._safe_float(info, "enterpriseToEbitda", "ev_ebitda")
        pe = self._safe_float(info, "trailingPE", "forwardPE", "pe_ratio")
        ps = self._safe_float(info, "priceToSalesTrailing12Months", "price_to_sales")
        pb = self._safe_float(info, "priceToBook", "price_to_book")
        if all(v is None for v in [ev_ebitda, pe, ps, pb]):
            return None
        return {
            "ticker": ticker,
            "EV/EBITDA": ev_ebitda,
            "P/E": pe,
            "P/S": ps,
            "P/B": pb,
        }

    def _extract_target_metrics(self, info: dict) -> Dict[str, float]:
        sf = self._safe_float
        return {
            "ebitda": sf(info, "ebitda") or 0.0,
            "net_income": sf(info, "netIncomeToCommon", "net_income") or 0.0,
            "revenue": sf(info, "totalRevenue", "revenue") or 0.0,
            "book_value": sf(info, "bookValue", "book_value") or 0.0,
            "total_debt": sf(info, "totalDebt", "total_debt") or 0.0,
            "cash": sf(info, "totalCash", "cash") or 0.0,
        }

    def _price_from_ev_ebitda(
        self,
        agg: pd.Series,
        metrics: dict,
        info: dict,
        shares: float,
        warnings: list,
    ) -> float:
        mult = agg.get("EV/EBITDA")
        if mult is None or np.isnan(mult) or metrics["ebitda"] <= 0 or shares <= 0:
            warnings.append("EV/EBITDA implied price unavailable.")
            return float("nan")
        ev = mult * metrics["ebitda"]
        equity_value = ev - metrics["total_debt"] + metrics["cash"]
        return max(equity_value / shares, 0.0)

    def _price_from_pe(self, agg: pd.Series, metrics: dict, shares: float, warnings: list) -> float:
        mult = agg.get("P/E")
        if mult is None or np.isnan(mult) or metrics["net_income"] <= 0 or shares <= 0:
            warnings.append("P/E implied price unavailable.")
            return float("nan")
        return (mult * metrics["net_income"]) / shares

    def _price_from_ps(self, agg: pd.Series, metrics: dict, shares: float, warnings: list) -> float:
        mult = agg.get("P/S")
        if mult is None or np.isnan(mult) or metrics["revenue"] <= 0 or shares <= 0:
            warnings.append("P/S implied price unavailable.")
            return float("nan")
        return (mult * metrics["revenue"]) / shares

    def _price_from_pb(self, agg: pd.Series, metrics: dict, shares: float, warnings: list) -> float:
        mult = agg.get("P/B")
        if mult is None or np.isnan(mult) or metrics["book_value"] <= 0 or shares <= 0:
            warnings.append("P/B implied price unavailable.")
            return float("nan")
        return mult * metrics["book_value"]

    def _blend(self, prices: Dict[str, float]) -> float:
        total_w = 0.0
        weighted_sum = 0.0
        for key, price in prices.items():
            w = self.weights.get(key, 0.0)
            if price is not None and not np.isnan(price) and price > 0:
                weighted_sum += w * price
                total_w += w
        if total_w == 0:
            return float("nan")
        return weighted_sum / total_w

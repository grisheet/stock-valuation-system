"""models/signal.py – BUY / HOLD / SELL signal aggregator."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class Signal(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class SignalResult:
    """Aggregated valuation signal."""
    signal: Signal
    score: float          # -1 (strong sell) to +1 (strong buy)
    margin_of_safety: float  # (intrinsic - market) / intrinsic
    model_signals: Dict[str, Signal]
    model_prices: Dict[str, float]
    market_price: float
    intrinsic_blended: float
    rationale: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class SignalGenerator:
    """Combine DCF, Comps, and DDM outputs into a single trading signal.

    Scoring logic
    -------------
    Each model votes: price_estimate > market_price  =>  BUY (+1),
                      within tolerance band          =>  HOLD (0),
                      below market                   =>  SELL (-1).
    Votes are weighted and averaged to produce a score in [-1, +1].
    """

    # Weights used for blended intrinsic price and signal score
    _DEFAULT_WEIGHTS: Dict[str, float] = {
        "dcf": 0.50,
        "comps": 0.30,
        "ddm": 0.20,
    }

    # Margin-of-safety thresholds
    BUY_THRESHOLD = 0.15   # >15 % undervalued  => BUY
    SELL_THRESHOLD = -0.05  # >5 % overvalued    => SELL

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self.weights = weights or self._DEFAULT_WEIGHTS

    def generate(
        self,
        market_price: float,
        dcf_price: Optional[float] = None,
        comps_price: Optional[float] = None,
        ddm_price: Optional[float] = None,
    ) -> SignalResult:
        """Generate a BUY / HOLD / SELL signal.

        Parameters
        ----------
        market_price : float  Current market price.
        dcf_price    : float  Intrinsic value from DCF model (or None).
        comps_price  : float  Blended comps price (or None).
        ddm_price    : float  DDM intrinsic value (or None).
        """
        warnings: List[str] = []
        model_prices: Dict[str, float] = {}
        model_signals: Dict[str, Signal] = {}

        inputs = {"dcf": dcf_price, "comps": comps_price, "ddm": ddm_price}

        # ---- Collect valid model prices --------------------------------
        for name, price in inputs.items():
            if price is not None and not (isinstance(price, float) and np.isnan(price)) and price > 0:
                model_prices[name] = price
                model_signals[name] = self._model_vote(price, market_price)
            else:
                warnings.append(f"{name.upper()} price unavailable or invalid; excluded from signal.")

        if not model_prices:
            return SignalResult(
                signal=Signal.INSUFFICIENT_DATA,
                score=0.0,
                margin_of_safety=0.0,
                model_signals={},
                model_prices={},
                market_price=market_price,
                intrinsic_blended=float("nan"),
                rationale=["No valid model prices available."],
                warnings=warnings,
            )

        # ---- Blended intrinsic price -----------------------------------
        total_w = sum(self.weights.get(k, 1.0) for k in model_prices)
        intrinsic_blended = sum(
            model_prices[k] * self.weights.get(k, 1.0)
            for k in model_prices
        ) / total_w

        # ---- Margin of safety -----------------------------------------
        mos = (intrinsic_blended - market_price) / intrinsic_blended

        # ---- Weighted score -------------------------------------------
        score_sum = 0.0
        score_w = 0.0
        for k, sig in model_signals.items():
            w = self.weights.get(k, 1.0)
            v = 1.0 if sig == Signal.BUY else (-1.0 if sig == Signal.SELL else 0.0)
            score_sum += v * w
            score_w += w
        score = score_sum / score_w if score_w else 0.0

        # ---- Final signal ---------------------------------------------
        if mos >= self.BUY_THRESHOLD:
            final_signal = Signal.BUY
        elif mos <= self.SELL_THRESHOLD:
            final_signal = Signal.SELL
        else:
            final_signal = Signal.HOLD

        # ---- Rationale ------------------------------------------------
        rationale = [
            f"Blended intrinsic value: ${intrinsic_blended:.2f}",
            f"Market price: ${market_price:.2f}",
            f"Margin of safety: {mos*100:.1f}%",
            f"Signal score: {score:.2f} (range -1 to +1)",
        ]
        for k, sig in model_signals.items():
            rationale.append(f"  {k.upper()}: ${model_prices[k]:.2f} => {sig.value}")

        return SignalResult(
            signal=final_signal,
            score=round(score, 4),
            margin_of_safety=round(mos, 4),
            model_signals=model_signals,
            model_prices=model_prices,
            market_price=market_price,
            intrinsic_blended=round(intrinsic_blended, 4),
            rationale=rationale,
            warnings=warnings,
        )

    # ------------------------------------------------------------------

    def _model_vote(self, model_price: float, market_price: float) -> Signal:
        mos = (model_price - market_price) / model_price
        if mos >= self.BUY_THRESHOLD:
            return Signal.BUY
        if mos <= self.SELL_THRESHOLD:
            return Signal.SELL
        return Signal.HOLD

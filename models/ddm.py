"""models/ddm.py – Dividend Discount Model (Gordon Growth & multi-stage)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DDMResult:
    """Results container for Dividend Discount Model."""
    intrinsic_value: float
    model_used: str  # 'gordon_growth' | 'two_stage' | 'three_stage'
    dividends_projected: List[float]
    terminal_value: float
    assumptions: Dict[str, object] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class DDMModel:
    """Dividend Discount Model implementation.

    Supports:
    - Gordon Growth Model (single-stage constant growth)
    - Two-stage DDM  (high growth then terminal)
    - Three-stage DDM (high / transition / terminal)
    """

    def calculate(
        self,
        annual_dividend: float,
        cost_of_equity: float,
        terminal_growth_rate: float,
        high_growth_rate: Optional[float] = None,
        high_growth_years: int = 5,
        transition_growth_rate: Optional[float] = None,
        transition_years: int = 5,
    ) -> DDMResult:
        """Run DDM valuation.

        Parameters
        ----------
        annual_dividend : float
            Most recent annual dividend per share (D0).
        cost_of_equity : float
            Required rate of return (e.g. 0.10 for 10%).
        terminal_growth_rate : float
            Stable long-run growth rate (must be < cost_of_equity).
        high_growth_rate : float, optional
            Growth rate during high-growth phase. If None, uses Gordon model.
        high_growth_years : int
            Number of years in high-growth phase.
        transition_growth_rate : float, optional
            Growth rate during transition phase. Activates three-stage model.
        transition_years : int
            Number of years in transition phase.
        """
        warnings: List[str] = []

        # ---- Input validation -------------------------------------------
        if annual_dividend <= 0:
            return DDMResult(
                intrinsic_value=float("nan"),
                model_used="none",
                dividends_projected=[],
                terminal_value=float("nan"),
                warnings=warnings,
                error="Annual dividend must be positive.",
            )

        if cost_of_equity <= terminal_growth_rate:
            return DDMResult(
                intrinsic_value=float("nan"),
                model_used="none",
                dividends_projected=[],
                terminal_value=float("nan"),
                warnings=warnings,
                error="Cost of equity must exceed terminal growth rate.",
            )

        # ---- Model selection -------------------------------------------
        if high_growth_rate is None:
            return self._gordon_growth(annual_dividend, cost_of_equity, terminal_growth_rate, warnings)

        if transition_growth_rate is not None:
            return self._three_stage(
                annual_dividend, cost_of_equity,
                high_growth_rate, high_growth_years,
                transition_growth_rate, transition_years,
                terminal_growth_rate, warnings,
            )

        return self._two_stage(
            annual_dividend, cost_of_equity,
            high_growth_rate, high_growth_years,
            terminal_growth_rate, warnings,
        )

    # ------------------------------------------------------------------
    # Model variants
    # ------------------------------------------------------------------

    def _gordon_growth(
        self,
        d0: float,
        ke: float,
        g: float,
        warnings: list,
    ) -> DDMResult:
        d1 = d0 * (1 + g)
        value = d1 / (ke - g)
        return DDMResult(
            intrinsic_value=round(value, 4),
            model_used="gordon_growth",
            dividends_projected=[round(d1, 4)],
            terminal_value=round(value, 4),
            assumptions={"d0": d0, "ke": ke, "g": g},
            warnings=warnings,
        )

    def _two_stage(
        self,
        d0: float,
        ke: float,
        g1: float,
        n1: int,
        gn: float,
        warnings: list,
    ) -> DDMResult:
        pv_divs, divs = self._pv_explicit(d0, ke, g1, n1)
        dn = divs[-1] * (1 + gn)
        terminal_value = dn / (ke - gn)
        pv_terminal = terminal_value / (1 + ke) ** n1
        value = pv_divs + pv_terminal
        return DDMResult(
            intrinsic_value=round(value, 4),
            model_used="two_stage",
            dividends_projected=[round(d, 4) for d in divs],
            terminal_value=round(terminal_value, 4),
            assumptions={"d0": d0, "ke": ke, "g1": g1, "n1": n1, "gn": gn},
            warnings=warnings,
        )

    def _three_stage(
        self,
        d0: float,
        ke: float,
        g1: float,
        n1: int,
        g2: float,
        n2: int,
        gn: float,
        warnings: list,
    ) -> DDMResult:
        # Phase 1
        pv1, divs1 = self._pv_explicit(d0, ke, g1, n1)
        # Phase 2
        pv2, divs2 = self._pv_explicit(divs1[-1], ke, g2, n2, start_t=n1)
        all_divs = divs1 + divs2
        # Terminal
        dn = divs2[-1] * (1 + gn)
        terminal_value = dn / (ke - gn)
        pv_terminal = terminal_value / (1 + ke) ** (n1 + n2)
        value = pv1 + pv2 + pv_terminal
        return DDMResult(
            intrinsic_value=round(value, 4),
            model_used="three_stage",
            dividends_projected=[round(d, 4) for d in all_divs],
            terminal_value=round(terminal_value, 4),
            assumptions={"d0": d0, "ke": ke, "g1": g1, "n1": n1, "g2": g2, "n2": n2, "gn": gn},
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    @staticmethod
    def _pv_explicit(
        d_prev: float,
        ke: float,
        g: float,
        n: int,
        start_t: int = 0,
    ):
        """Return (total_pv, list_of_dividends) for n explicit years."""
        divs: List[float] = []
        total_pv = 0.0
        for i in range(1, n + 1):
            d = d_prev * (1 + g) ** i
            divs.append(d)
            total_pv += d / (1 + ke) ** (start_t + i)
        return total_pv, divs

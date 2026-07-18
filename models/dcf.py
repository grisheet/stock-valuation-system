"""Discounted Cash Flow (DCF) valuation model."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

import config
from data.fetcher import CompanySnapshot
from models.wacc import WACCResult


@dataclass
class DCFAssumptions:
    initial_growth_rate: float = 0.10       # Year-1 revenue growth
    terminal_growth_rate: float = config.DEFAULT_TERMINAL_GROWTH_RATE
    projection_years: int = config.DEFAULT_PROJECTION_YEARS
    ebit_margin: Optional[float] = None     # If None, derived from history
    capex_pct_revenue: Optional[float] = None
    nwc_pct_revenue: Optional[float] = None
    da_pct_revenue: Optional[float] = None


@dataclass
class DCFResult:
    intrinsic_value_per_share: float
    enterprise_value: float
    equity_value: float
    terminal_value: float
    pv_fcfs: List[float]
    fcf_projections: List[float]
    revenue_projections: List[float]
    wacc: float
    assumptions: DCFAssumptions
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


def run_dcf(
    snapshot: CompanySnapshot,
    wacc_result: WACCResult,
    assumptions: Optional[DCFAssumptions] = None,
) -> DCFResult:
    """Run a 2-stage DCF and return intrinsic value per share."""
    if assumptions is None:
        assumptions = DCFAssumptions()

    warnings: List[str] = []
    wacc = wacc_result.wacc
    n = assumptions.projection_years
    g = assumptions.terminal_growth_rate

    if wacc <= g:
        return DCFResult(
            intrinsic_value_per_share=float("nan"),
            enterprise_value=float("nan"),
            equity_value=float("nan"),
            terminal_value=float("nan"),
            pv_fcfs=[],
            fcf_projections=[],
            revenue_projections=[],
            wacc=wacc,
            assumptions=assumptions,
            error=f"WACC ({wacc:.1%}) must be greater than terminal growth ({g:.1%}).",
        )

    # ─ Base revenue ──────────────────────────────────────────────────────────────
    revenue_base = _latest(
        snapshot.income_statement, ["Total Revenue", "Revenue", "Net Revenue"]
    )
    if revenue_base is None or revenue_base <= 0:
        return DCFResult(
            intrinsic_value_per_share=float("nan"),
            enterprise_value=float("nan"),
            equity_value=float("nan"),
            terminal_value=float("nan"),
            pv_fcfs=[],
            fcf_projections=[],
            revenue_projections=[],
            wacc=wacc,
            assumptions=assumptions,
            error="Revenue data unavailable or zero.",
        )

    # ─ Derive operating margins from history ───────────────────────────────────
    ebit_margin = assumptions.ebit_margin
    if ebit_margin is None:
        ebit = _latest(snapshot.income_statement, ["EBIT", "Operating Income"])
        ebit_margin = (ebit / revenue_base) if (ebit and revenue_base) else 0.10
        if ebit is None:
            warnings.append("EBIT unavailable; using 10% margin assumption.")

    da_pct = assumptions.da_pct_revenue
    if da_pct is None:
        da = _latest(snapshot.cash_flow, ["Depreciation And Amortization", "Depreciation"])
        da_pct = (da / revenue_base) if (da and revenue_base) else 0.03

    capex_pct = assumptions.capex_pct_revenue
    if capex_pct is None:
        capex = _latest(
            snapshot.cash_flow,
            ["Capital Expenditure", "Purchase Of Property Plant And Equipment"],
        )
        capex_pct = abs(capex / revenue_base) if (capex and revenue_base) else 0.04

    nwc_pct = assumptions.nwc_pct_revenue or 0.02

    # ─ Project FCFs ──────────────────────────────────────────────────────────────
    revenue_projections: List[float] = []
    fcf_projections: List[float] = []
    pv_fcfs: List[float] = []

    rev = revenue_base
    prev_rev = revenue_base
    for yr in range(1, n + 1):
        rev = rev * (1 + assumptions.initial_growth_rate)
        revenue_projections.append(rev)
        nopat = rev * ebit_margin * (1 - wacc_result.tax_rate)
        da_val = rev * da_pct
        capex_val = rev * capex_pct
        d_nwc = (rev - prev_rev) * nwc_pct
        fcf = nopat + da_val - capex_val - d_nwc
        fcf_projections.append(fcf)
        pv_fcfs.append(fcf / (1 + wacc) ** yr)
        prev_rev = rev

    # ─ Terminal value (Gordon Growth) ──────────────────────────────────────────
    terminal_fcf = fcf_projections[-1] * (1 + g)
    terminal_value = terminal_fcf / (wacc - g)
    pv_terminal = terminal_value / (1 + wacc) ** n

    enterprise_value = sum(pv_fcfs) + pv_terminal

    # ─ Bridge to equity ─────────────────────────────────────────────────────────────
    total_debt = snapshot.info.get("totalDebt") or 0.0
    cash = _latest(snapshot.balance_sheet, ["Cash And Cash Equivalents", "Cash"]) or 0.0
    equity_value = enterprise_value - total_debt + cash

    shares = snapshot.shares_outstanding
    if not shares or np.isnan(shares) or shares <= 0:
        return DCFResult(
            intrinsic_value_per_share=float("nan"),
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            terminal_value=terminal_value,
            pv_fcfs=pv_fcfs,
            fcf_projections=fcf_projections,
            revenue_projections=revenue_projections,
            wacc=wacc,
            assumptions=assumptions,
            warnings=warnings,
            error="Shares outstanding unavailable.",
        )

    intrinsic = equity_value / shares
    return DCFResult(
        intrinsic_value_per_share=intrinsic,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        terminal_value=terminal_value,
        pv_fcfs=pv_fcfs,
        fcf_projections=fcf_projections,
        revenue_projections=revenue_projections,
        wacc=wacc,
        assumptions=assumptions,
        warnings=warnings,
    )


# ── Helper ──────────────────────────────────────────────────────────────────────────

def _latest(df, candidates):
    if df is None or df.empty:
        return None
    for c in candidates:
        if c in df.index:
            v = df.loc[c].iloc[0]
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                return float(v)
    return None

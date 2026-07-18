"""WACC (Weighted-Average Cost of Capital) calculator."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

import numpy as np

import config
from data.fetcher import CompanySnapshot


@dataclass
class WACCResult:
    wacc: float
    cost_of_equity: float
    cost_of_debt_after_tax: float
    cost_of_debt_pre_tax: float
    equity_weight: float
    debt_weight: float
    tax_rate: float
    beta: float
    risk_free_rate: float
    equity_risk_premium: float
    notes: List[str] = field(default_factory=list)


def calculate_wacc(
    snapshot: CompanySnapshot,
    risk_free_rate: float = config.DEFAULT_RISK_FREE_RATE,
    equity_risk_premium: float = config.DEFAULT_EQUITY_RISK_PREMIUM,
) -> WACCResult:
    """Compute WACC from a CompanySnapshot.

    Falls back gracefully when data is missing:
    - Beta defaults to 1.0 if unavailable.
    - Cost of debt falls back to risk_free_rate + 2% credit spread.
    - Tax rate falls back to 21% (US statutory).
    """
    info = snapshot.info
    notes: List[str] = []

    # ─ Beta ────────────────────────────────────────────────────────────────────────
    beta = info.get("beta") or 1.0
    if info.get("beta") is None:
        notes.append("Beta unavailable; defaulting to 1.0 (market-average risk).")

    # ─ Weights ──────────────────────────────────────────────────────────────────
    market_cap = snapshot.market_cap or (snapshot.price * snapshot.shares_outstanding)
    debt_value = info.get("totalDebt") or 0.0
    total_capital = market_cap + debt_value

    if total_capital <= 0:
        equity_weight, debt_weight = 1.0, 0.0
        notes.append("Total capital <= 0; assuming 100% equity financing.")
    else:
        equity_weight = market_cap / total_capital
        debt_weight = debt_value / total_capital

    # ─ Cost of equity (CAPM) ────────────────────────────────────────────────
    cost_of_equity = risk_free_rate + beta * equity_risk_premium

    # ─ Tax rate ─────────────────────────────────────────────────────────────────
    tax_rate = info.get("effectiveTaxRate") or 0.21
    tax_rate = max(0.0, min(tax_rate, 0.50))  # clamp 0-50%

    # ─ Cost of debt ─────────────────────────────────────────────────────────────
    interest_expense = _safe_value(
        snapshot.income_statement, ["Interest Expense", "Interest Expense Non Operating"]
    )
    if interest_expense and debt_value > 0:
        cost_of_debt_pre_tax = _clamp(_safe_divide(abs(interest_expense), debt_value), 0.01, 0.25)
    else:
        cost_of_debt_pre_tax = risk_free_rate + 0.02
        notes.append(
            "Interest expense/debt data unavailable; cost of debt estimated as "
            "risk-free rate + 2% credit spread."
        )

    cost_of_debt_after_tax = cost_of_debt_pre_tax * (1 - tax_rate)

    wacc = equity_weight * cost_of_equity + debt_weight * cost_of_debt_after_tax
    # Floor WACC slightly above risk-free rate
    wacc = max(wacc, risk_free_rate + 0.01)

    return WACCResult(
        wacc=wacc,
        cost_of_equity=cost_of_equity,
        cost_of_debt_after_tax=cost_of_debt_after_tax,
        cost_of_debt_pre_tax=cost_of_debt_pre_tax,
        equity_weight=equity_weight,
        debt_weight=debt_weight,
        tax_rate=tax_rate,
        beta=beta,
        risk_free_rate=risk_free_rate,
        equity_risk_premium=equity_risk_premium,
        notes=notes,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────────

def _safe_value(df, candidates):
    if df is None or df.empty:
        return None
    for c in candidates:
        if c in df.index:
            v = df.loc[c].iloc[0]
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                return float(v)
    return None


def _safe_divide(a, b):
    return a / b if b and b != 0 else 0.0


def _clamp(v, lo, hi):
    return max(lo, min(v, hi))

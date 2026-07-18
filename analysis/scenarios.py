"""analysis/scenarios.py – Bull / Base / Bear scenario modeling."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


@dataclass
class Scenario:
    """A single named scenario with its parameter overrides."""
    name: str
    overrides: Dict[str, Any]   # e.g. {"revenue_growth": 0.25, "wacc": 0.09}
    description: str = ""


@dataclass
class ScenarioResult:
    name: str
    intrinsic_value: float
    parameters: Dict[str, Any]
    description: str = ""


class ScenarioAnalysis:
    """Run Bull / Base / Bear (or any custom) scenarios against a valuation function.

    Usage
    -----
    >>> sa = ScenarioAnalysis(base_params={"revenue_growth": 0.12, "wacc": 0.10, ...})
    >>> results_df = sa.run(valuation_fn=my_dcf_fn)
    """

    _DEFAULT_SCENARIOS: List[Scenario] = [
        Scenario(
            name="Bear",
            overrides={},
            description="Pessimistic: lower growth, higher discount rate",
        ),
        Scenario(
            name="Base",
            overrides={},
            description="Management guidance / consensus estimate",
        ),
        Scenario(
            name="Bull",
            overrides={},
            description="Optimistic: higher growth, lower discount rate",
        ),
    ]

    def __init__(self, base_params: Optional[Dict[str, Any]] = None) -> None:
        self.base_params: Dict[str, Any] = base_params or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        valuation_fn: Callable[..., float],
        scenarios: Optional[List[Scenario]] = None,
    ) -> pd.DataFrame:
        """Execute each scenario and return a summary DataFrame.

        Parameters
        ----------
        valuation_fn : Callable(**params) -> float
            Must accept keyword arguments matching keys in base_params / overrides.
        scenarios : list[Scenario], optional
            Custom scenarios. Uses default Bull/Base/Bear if not provided.
        """
        scenarios = scenarios or self._default_scenarios()
        rows = []
        for sc in scenarios:
            params = {**self.base_params, **sc.overrides}
            try:
                value = valuation_fn(**params)
            except Exception as exc:
                value = float("nan")
            rows.append(
                ScenarioResult(
                    name=sc.name,
                    intrinsic_value=round(float(value), 2) if value == value else float("nan"),
                    parameters=params,
                    description=sc.description,
                )
            )
        return self._to_dataframe(rows)

    def build_dcf_scenarios(
        self,
        base_revenue_growth: float,
        base_wacc: float,
        base_terminal_growth: float,
        bear_adj: Optional[Dict[str, float]] = None,
        bull_adj: Optional[Dict[str, float]] = None,
    ) -> List[Scenario]:
        """Build standard three-scenario set with automatic adjustments.

        Default adjustments (can be overridden):
          Bear : revenue_growth -5pp, wacc +1pp, terminal_growth -0.5pp
          Bull : revenue_growth +5pp, wacc -1pp, terminal_growth +0.5pp
        """
        bear_defaults = {"revenue_growth": -0.05, "wacc": +0.01, "terminal_growth": -0.005}
        bull_defaults = {"revenue_growth": +0.05, "wacc": -0.01, "terminal_growth": +0.005}

        bear_adj = {**bear_defaults, **(bear_adj or {})}
        bull_adj = {**bull_defaults, **(bull_adj or {})}

        return [
            Scenario(
                name="Bear",
                overrides={
                    "revenue_growth": base_revenue_growth + bear_adj["revenue_growth"],
                    "wacc": base_wacc + bear_adj["wacc"],
                    "terminal_growth": base_terminal_growth + bear_adj["terminal_growth"],
                },
                description="Pessimistic scenario",
            ),
            Scenario(
                name="Base",
                overrides={
                    "revenue_growth": base_revenue_growth,
                    "wacc": base_wacc,
                    "terminal_growth": base_terminal_growth,
                },
                description="Base case scenario",
            ),
            Scenario(
                name="Bull",
                overrides={
                    "revenue_growth": base_revenue_growth + bull_adj["revenue_growth"],
                    "wacc": base_wacc + bull_adj["wacc"],
                    "terminal_growth": base_terminal_growth + bull_adj["terminal_growth"],
                },
                description="Optimistic scenario",
            ),
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _default_scenarios(self) -> List[Scenario]:
        """Return default Bear/Base/Bull using base_params as-is."""
        return [
            Scenario(name="Bear", overrides={}, description="Bear case"),
            Scenario(name="Base", overrides={}, description="Base case"),
            Scenario(name="Bull", overrides={}, description="Bull case"),
        ]

    @staticmethod
    def _to_dataframe(results: List[ScenarioResult]) -> pd.DataFrame:
        rows = [
            {
                "Scenario": r.name,
                "Intrinsic Value ($)": r.intrinsic_value,
                "Description": r.description,
                **{f"param:{k}": v for k, v in r.parameters.items()},
            }
            for r in results
        ]
        return pd.DataFrame(rows).set_index("Scenario")

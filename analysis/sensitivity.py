"""analysis/sensitivity.py – Sensitivity grid analysis for DCF."""
from __future__ import annotations

from typing import Callable, List, Tuple

import numpy as np
import pandas as pd


class SensitivityAnalysis:
    """Build 2-D sensitivity tables (heat maps) for any valuation function.

    Typical usage
    -------------
    >>> sa = SensitivityAnalysis()
    >>> table = sa.two_way(
    ...     base_fn=lambda wacc, g: dcf_model.calculate(..., wacc=wacc, terminal_growth=g).intrinsic_value_per_share,
    ...     x_values=[0.07, 0.08, 0.09, 0.10, 0.11],
    ...     y_values=[0.02, 0.025, 0.03, 0.035],
    ...     x_label="WACC",
    ...     y_label="Terminal Growth",
    ... )
    """

    def two_way(
        self,
        base_fn: Callable[[float, float], float],
        x_values: List[float],
        y_values: List[float],
        x_label: str = "X",
        y_label: str = "Y",
        fmt_pct: bool = True,
    ) -> pd.DataFrame:
        """Return a DataFrame (rows = y_values, columns = x_values).

        Parameters
        ----------
        base_fn : Callable[[float, float], float]
            Function(x, y) -> scalar output (e.g. intrinsic price).
        x_values : list[float]
            Values for the column axis (e.g. WACC range).
        y_values : list[float]
            Values for the row axis (e.g. terminal growth range).
        x_label : str  Label for column axis.
        y_label : str  Label for row axis.
        fmt_pct : bool  Format axis labels as percentages.
        """
        data = []
        for y in y_values:
            row = []
            for x in x_values:
                try:
                    val = base_fn(x, y)
                    row.append(round(float(val), 2) if val is not None and not np.isnan(val) else np.nan)
                except Exception:
                    row.append(np.nan)
            data.append(row)

        col_labels = [f"{x:.1%}" if fmt_pct else str(x) for x in x_values]
        row_labels = [f"{y:.1%}" if fmt_pct else str(y) for y in y_values]

        df = pd.DataFrame(data, index=row_labels, columns=col_labels)
        df.index.name = y_label
        df.columns.name = x_label
        return df

    def one_way(
        self,
        base_fn: Callable[[float], float],
        x_values: List[float],
        x_label: str = "X",
        output_label: str = "Value",
        fmt_pct: bool = True,
    ) -> pd.DataFrame:
        """Return a single-column DataFrame showing output vs. one variable."""
        results = []
        for x in x_values:
            try:
                val = base_fn(x)
                results.append(round(float(val), 2) if val is not None and not np.isnan(val) else np.nan)
            except Exception:
                results.append(np.nan)

        labels = [f"{x:.1%}" if fmt_pct else str(x) for x in x_values]
        df = pd.DataFrame({output_label: results}, index=labels)
        df.index.name = x_label
        return df

    @staticmethod
    def wacc_growth_grid(
        dcf_fn: Callable,
        base_wacc: float,
        base_growth: float,
        wacc_delta: float = 0.02,
        growth_delta: float = 0.01,
        steps: int = 5,
    ) -> pd.DataFrame:
        """Convenience wrapper: build WACC x Terminal-Growth sensitivity grid.

        Parameters
        ----------
        dcf_fn : Callable(wacc, growth) -> float
        base_wacc : float   Central WACC.
        base_growth : float  Central terminal growth rate.
        wacc_delta : float   Half-range around base_wacc.
        growth_delta : float Half-range around base_growth.
        steps : int          Number of steps on each axis.
        """
        wacc_range = np.linspace(base_wacc - wacc_delta, base_wacc + wacc_delta, steps).tolist()
        growth_range = np.linspace(
            max(0.0, base_growth - growth_delta),
            min(base_wacc - 0.005, base_growth + growth_delta),
            steps,
        ).tolist()

        sa = SensitivityAnalysis()
        return sa.two_way(
            base_fn=dcf_fn,
            x_values=wacc_range,
            y_values=growth_range,
            x_label="WACC",
            y_label="Terminal Growth",
        )

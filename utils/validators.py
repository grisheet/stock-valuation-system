"""utils/validators.py – Input validation helpers."""
from __future__ import annotations

from typing import Any, List, Optional, Tuple


class InputValidator:
    """Validate user inputs before they are passed to financial models."""

    # ---- Ticker ---------------------------------------------------------

    @staticmethod
    def ticker(value: str) -> Tuple[bool, str]:
        """Validate a stock ticker symbol."""
        if not value or not isinstance(value, str):
            return False, "Ticker must be a non-empty string."
        cleaned = value.strip().upper()
        if not cleaned.isalpha() and "." not in cleaned and "-" not in cleaned:
            return False, f"Ticker '{cleaned}' contains invalid characters."
        if len(cleaned) > 10:
            return False, f"Ticker '{cleaned}' is too long (max 10 chars)."
        return True, cleaned

    # ---- Rate / percentage ---------------------------------------------

    @staticmethod
    def rate(
        value: Any,
        name: str = "rate",
        min_val: float = 0.0,
        max_val: float = 1.0,
    ) -> Tuple[bool, str]:
        """Validate a rate/percentage input (expected as decimal, e.g. 0.10)."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False, f"{name} must be a number."
        if not (min_val <= v <= max_val):
            return False, (
                f"{name} must be between {min_val*100:.1f}% and {max_val*100:.1f}%."
            )
        return True, ""

    # ---- Positive number -----------------------------------------------

    @staticmethod
    def positive(
        value: Any,
        name: str = "value",
    ) -> Tuple[bool, str]:
        """Validate that a value is a positive number."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False, f"{name} must be a number."
        if v <= 0:
            return False, f"{name} must be positive (got {v})."
        return True, ""

    # ---- Non-negative --------------------------------------------------

    @staticmethod
    def non_negative(
        value: Any,
        name: str = "value",
    ) -> Tuple[bool, str]:
        """Validate that a value is zero or positive."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False, f"{name} must be a number."
        if v < 0:
            return False, f"{name} must be non-negative (got {v})."
        return True, ""

    # ---- Integer range -------------------------------------------------

    @staticmethod
    def integer_range(
        value: Any,
        name: str = "value",
        min_val: int = 1,
        max_val: int = 30,
    ) -> Tuple[bool, str]:
        """Validate that a value is an integer within [min_val, max_val]."""
        try:
            v = int(value)
        except (TypeError, ValueError):
            return False, f"{name} must be an integer."
        if not (min_val <= v <= max_val):
            return False, f"{name} must be between {min_val} and {max_val}."
        return True, ""

    # ---- WACC vs growth ------------------------------------------------

    @staticmethod
    def wacc_gt_growth(wacc: float, terminal_growth: float) -> Tuple[bool, str]:
        """Ensure WACC > terminal growth rate (required for Gordon formula)."""
        if wacc <= terminal_growth:
            return (
                False,
                f"WACC ({wacc*100:.1f}%) must exceed terminal growth rate "
                f"({terminal_growth*100:.1f}%).",
            )
        return True, ""

    # ---- Batch validate ------------------------------------------------

    @classmethod
    def validate_dcf_inputs(
        cls,
        ticker: str,
        revenue_growth: float,
        wacc: float,
        terminal_growth: float,
        projection_years: int,
        margin: float,
    ) -> List[str]:
        """Run all DCF input validations and return list of error messages."""
        errors: List[str] = []

        ok, msg = cls.ticker(ticker)
        if not ok:
            errors.append(msg)

        for rate_val, rate_name, lo, hi in [
            (revenue_growth, "Revenue Growth", -0.5, 2.0),
            (wacc, "WACC", 0.01, 0.5),
            (terminal_growth, "Terminal Growth", -0.05, 0.15),
            (margin, "FCF Margin", -1.0, 1.0),
        ]:
            ok2, msg2 = cls.rate(rate_val, rate_name, lo, hi)
            if not ok2:
                errors.append(msg2)

        ok3, msg3 = cls.integer_range(projection_years, "Projection Years", 1, 30)
        if not ok3:
            errors.append(msg3)

        ok4, msg4 = cls.wacc_gt_growth(wacc, terminal_growth)
        if not ok4:
            errors.append(msg4)

        return errors

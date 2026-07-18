"""utils/formatting.py – Display formatting utilities."""
from __future__ import annotations

from typing import Optional


class Formatter:
    """Static methods for formatting financial values for display."""

    # ---- Currency -------------------------------------------------------

    @staticmethod
    def currency(
        value: Optional[float],
        prefix: str = "$",
        decimals: int = 2,
        na_str: str = "N/A",
    ) -> str:
        """Format a number as currency string (e.g. $1,234.56)."""
        if value is None or (isinstance(value, float) and value != value):
            return na_str
        return f"{prefix}{value:,.{decimals}f}"

    @staticmethod
    def large_currency(
        value: Optional[float],
        prefix: str = "$",
        na_str: str = "N/A",
    ) -> str:
        """Auto-scale large currency values to B/M/K suffixes."""
        if value is None or (isinstance(value, float) and value != value):
            return na_str
        abs_val = abs(value)
        sign = "-" if value < 0 else ""
        if abs_val >= 1e12:
            return f"{sign}{prefix}{abs_val/1e12:.2f}T"
        if abs_val >= 1e9:
            return f"{sign}{prefix}{abs_val/1e9:.2f}B"
        if abs_val >= 1e6:
            return f"{sign}{prefix}{abs_val/1e6:.2f}M"
        if abs_val >= 1e3:
            return f"{sign}{prefix}{abs_val/1e3:.2f}K"
        return f"{sign}{prefix}{abs_val:.2f}"

    # ---- Percentage -----------------------------------------------------

    @staticmethod
    def percent(
        value: Optional[float],
        decimals: int = 1,
        na_str: str = "N/A",
    ) -> str:
        """Format a decimal as percentage string (e.g. 0.1234 -> '12.3%')."""
        if value is None or (isinstance(value, float) and value != value):
            return na_str
        return f"{value*100:.{decimals}f}%"

    # ---- Signal badge --------------------------------------------------

    @staticmethod
    def signal_badge(signal: str) -> str:
        """Return a Markdown/HTML-friendly label for a valuation signal."""
        badges = {
            "BUY": "🟢 **BUY**",
            "HOLD": "🟡 **HOLD**",
            "SELL": "🔴 **SELL**",
            "INSUFFICIENT_DATA": "⚪ INSUFFICIENT DATA",
        }
        return badges.get(signal.upper(), signal)

    # ---- Delta ----------------------------------------------------------

    @staticmethod
    def delta(
        value: Optional[float],
        na_str: str = "N/A",
    ) -> str:
        """Format a signed percentage change with arrow."""
        if value is None or (isinstance(value, float) and value != value):
            return na_str
        arrow = "\u2191" if value >= 0 else "\u2193"
        return f"{arrow} {abs(value)*100:.1f}%"

    # ---- Ratio ----------------------------------------------------------

    @staticmethod
    def ratio(
        value: Optional[float],
        suffix: str = "x",
        decimals: int = 1,
        na_str: str = "N/A",
    ) -> str:
        """Format a financial ratio (e.g. 12.3x P/E)."""
        if value is None or (isinstance(value, float) and value != value):
            return na_str
        return f"{value:.{decimals}f}{suffix}"

    # ---- Summary dict --------------------------------------------------

    @staticmethod
    def format_dcf_summary(
        intrinsic: Optional[float],
        market_price: Optional[float],
        wacc: Optional[float],
        terminal_growth: Optional[float],
        enterprise_value: Optional[float],
    ) -> dict:
        """Return a formatted dict ready for display in Streamlit metrics."""
        fmt = Formatter
        mos = None
        if intrinsic and market_price and intrinsic > 0:
            mos = (intrinsic - market_price) / intrinsic
        return {
            "Intrinsic Value": fmt.currency(intrinsic),
            "Market Price": fmt.currency(market_price),
            "Margin of Safety": fmt.percent(mos),
            "WACC": fmt.percent(wacc),
            "Terminal Growth Rate": fmt.percent(terminal_growth),
            "Enterprise Value": fmt.large_currency(enterprise_value),
        }

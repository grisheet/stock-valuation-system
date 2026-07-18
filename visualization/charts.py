"""visualization/charts.py – Plotly chart builders for the Streamlit dashboard."""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class ChartBuilder:
    """Factory for all Plotly figures used in the Streamlit dashboard."""

    # ------------------------------------------------------------------ #
    # Waterfall / FCF projection                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def fcf_waterfall(
        years: List[int],
        fcf_values: List[float],
        title: str = "Free Cash Flow Projections",
    ) -> go.Figure:
        """Bar chart of projected free cash flows."""
        colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in fcf_values]
        fig = go.Figure(
            go.Bar(
                x=[str(y) for y in years],
                y=fcf_values,
                marker_color=colors,
                text=[f"${v/1e9:.1f}B" for v in fcf_values],
                textposition="outside",
            )
        )
        fig.update_layout(
            title=title,
            xaxis_title="Year",
            yaxis_title="FCF ($)",
            template="plotly_dark",
            showlegend=False,
        )
        return fig

    # ------------------------------------------------------------------ #
    # Sensitivity heat map                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def sensitivity_heatmap(
        df: pd.DataFrame,
        title: str = "Sensitivity Analysis",
        market_price: Optional[float] = None,
    ) -> go.Figure:
        """Annotated heat map from a SensitivityAnalysis DataFrame."""
        z = df.values.tolist()
        x = list(df.columns)
        y = list(df.index)

        # Color-code relative to market price if provided
        colorscale = "RdYlGn"
        zmid = market_price if market_price else None

        fig = go.Figure(
            go.Heatmap(
                z=z,
                x=x,
                y=y,
                colorscale=colorscale,
                zmid=zmid,
                text=[[f"${v:.0f}" if v == v else "N/A" for v in row] for row in z],
                texttemplate="%{text}",
                showscale=True,
            )
        )
        fig.update_layout(
            title=title,
            xaxis_title=df.columns.name or "X",
            yaxis_title=df.index.name or "Y",
            template="plotly_dark",
        )
        return fig

    # ------------------------------------------------------------------ #
    # Scenario comparison                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def scenario_bar(
        scenario_values: Dict[str, float],
        market_price: float,
        title: str = "Bull / Base / Bear Scenarios",
    ) -> go.Figure:
        """Horizontal bar chart comparing scenario prices to market price."""
        scenarios = list(scenario_values.keys())
        values = list(scenario_values.values())
        colors = []
        for v in values:
            if v > market_price * 1.15:
                colors.append("#2ecc71")
            elif v < market_price * 0.95:
                colors.append("#e74c3c")
            else:
                colors.append("#f39c12")

        fig = go.Figure(
            go.Bar(
                x=values,
                y=scenarios,
                orientation="h",
                marker_color=colors,
                text=[f"${v:.2f}" for v in values],
                textposition="auto",
            )
        )
        fig.add_vline(
            x=market_price,
            line_dash="dash",
            line_color="white",
            annotation_text=f"Market: ${market_price:.2f}",
            annotation_position="top right",
        )
        fig.update_layout(
            title=title,
            xaxis_title="Intrinsic Value ($)",
            template="plotly_dark",
        )
        return fig

    # ------------------------------------------------------------------ #
    # Equity / backtest curve                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def equity_curve(
        equity: pd.Series,
        price_series: Optional[pd.Series] = None,
        ticker: str = "",
        title: str = "Backtest Equity Curve",
    ) -> go.Figure:
        """Line chart of backtest equity curve vs. buy-and-hold."""
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=equity.index,
                y=equity.values,
                name="Strategy",
                line=dict(color="#3498db"),
            )
        )
        if price_series is not None and not price_series.empty:
            scale = equity.iloc[0] / price_series.iloc[0]
            bah = price_series * scale
            fig.add_trace(
                go.Scatter(
                    x=bah.index,
                    y=bah.values,
                    name=f"Buy & Hold {ticker}",
                    line=dict(color="#95a5a6", dash="dash"),
                )
            )
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            template="plotly_dark",
            legend=dict(orientation="h"),
        )
        return fig

    # ------------------------------------------------------------------ #
    # Valuation football field                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def football_field(
        model_prices: Dict[str, float],
        market_price: float,
        title: str = "Valuation Football Field",
    ) -> go.Figure:
        """Horizontal range chart showing each model's implied price."""
        models = list(model_prices.keys())
        prices = list(model_prices.values())

        fig = go.Figure()
        for model, price in zip(models, prices):
            if price != price:  # nan check
                continue
            fig.add_trace(
                go.Bar(
                    x=[price],
                    y=[model],
                    orientation="h",
                    name=model,
                    text=[f"${price:.2f}"],
                    textposition="auto",
                )
            )
        fig.add_vline(
            x=market_price,
            line_dash="dash",
            line_color="yellow",
            annotation_text=f"Market ${market_price:.2f}",
        )
        fig.update_layout(
            title=title,
            xaxis_title="Price ($)",
            barmode="overlay",
            template="plotly_dark",
            showlegend=True,
        )
        return fig

    # ------------------------------------------------------------------ #
    # WACC breakdown donut                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def wacc_donut(wacc_components: Dict[str, float], title: str = "WACC Breakdown") -> go.Figure:
        """Donut chart showing contribution of equity vs. debt to WACC."""
        labels = list(wacc_components.keys())
        values = list(wacc_components.values())
        fig = go.Figure(
            go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                textinfo="label+percent",
            )
        )
        fig.update_layout(title=title, template="plotly_dark")
        return fig

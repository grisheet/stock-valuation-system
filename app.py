# app.py
"""
Stock Valuation System - Streamlit Application Entry Point

Run with: streamlit run app.py
"""

import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

from config import AppConfig
from models.dcf import DCFModel
from models.wacc import WACCModel
from models.ddm import DDMModel
from models.comps import CompsModel
from models.signal import SignalEngine
from analysis.sensitivity import SensitivityAnalyzer
from analysis.scenarios import ScenarioAnalyzer
from analysis.backtest import Backtester
from visualization.charts import ChartBuilder
from reports.export import ReportExporter
from utils.validators import InputValidator
from utils.formatting import Formatter

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Stock Valuation System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Stock Valuation System")
st.sidebar.markdown("---")

page = st.sidebar.selectbox(
    "Select Module",
    [
        "DCF Valuation",
        "WACC Calculator",
        "DDM Valuation",
        "Comparable Companies",
        "Sensitivity Analysis",
        "Scenario Analysis",
        "Backtest",
        "Signals",
        "Export Report",
    ],
)

st.sidebar.markdown("---")
st.sidebar.info(
    "Configure your inputs on each module page. "
    "Results are computed in real time."
)

# ---------------------------------------------------------------------------
# Page Routing
# ---------------------------------------------------------------------------

fmt = Formatter()


def page_dcf():
    st.title("Discounted Cash Flow (DCF) Valuation")
    st.markdown("Estimate intrinsic value by discounting projected free cash flows.")

    with st.form("dcf_form"):
        col1, col2 = st.columns(2)
        with col1:
            ticker = st.text_input("Ticker Symbol", value="AAPL")
            shares = st.number_input("Shares Outstanding (M)", min_value=0.1, value=15500.0)
            wacc = st.slider("WACC (%)", 5.0, 20.0, 10.0, step=0.1) / 100
            tgr = st.slider("Terminal Growth Rate (%)", 0.0, 5.0, 2.5, step=0.1) / 100
        with col2:
            st.markdown("**Projected Free Cash Flows (USD Millions)**")
            fcfs = [
                st.number_input(f"Year {i+1} FCF", value=float(100 * (1.08 ** i)), key=f"fcf_{i}")
                for i in range(5)
            ]
        submitted = st.form_submit_button("Calculate")

    if submitted:
        if not InputValidator.validate_ticker(ticker):
            st.error("Invalid ticker symbol.")
            return
        model = DCFModel(
            free_cash_flows=fcfs,
            wacc=wacc,
            terminal_growth_rate=tgr,
            shares_outstanding=shares,
        )
        result = model.calculate()
        col1, col2, col3 = st.columns(3)
        col1.metric("Intrinsic Value / Share", fmt.currency(result.get("intrinsic_value", 0)))
        col2.metric("Enterprise Value", fmt.large_currency(result.get("enterprise_value", 0)))
        col3.metric("Terminal Value", fmt.large_currency(result.get("terminal_value", 0)))

        chart = ChartBuilder.waterfall(result)
        if chart:
            st.plotly_chart(chart, use_container_width=True)


def page_wacc():
    st.title("WACC Calculator")
    st.markdown("Compute the Weighted Average Cost of Capital.")

    with st.form("wacc_form"):
        col1, col2 = st.columns(2)
        with col1:
            equity = st.number_input("Market Cap (USD M)", min_value=0.0, value=2_500_000.0)
            debt = st.number_input("Total Debt (USD M)", min_value=0.0, value=120_000.0)
            tax_rate = st.slider("Tax Rate (%)", 0.0, 40.0, 21.0, step=0.5) / 100
        with col2:
            coe = st.slider("Cost of Equity (%)", 1.0, 25.0, 9.5, step=0.1) / 100
            cod = st.slider("Pre-Tax Cost of Debt (%)", 1.0, 15.0, 4.5, step=0.1) / 100
        submitted = st.form_submit_button("Calculate WACC")

    if submitted:
        model = WACCModel(
            equity=equity, debt=debt,
            cost_of_equity=coe, cost_of_debt=cod, tax_rate=tax_rate
        )
        result = model.calculate()
        col1, col2, col3 = st.columns(3)
        col1.metric("WACC", fmt.percent(result.get("wacc", 0)))
        col2.metric("Equity Weight", fmt.percent(result.get("equity_weight", 0)))
        col3.metric("Debt Weight", fmt.percent(result.get("debt_weight", 0)))


def page_ddm():
    st.title("Dividend Discount Model (DDM)")
    st.markdown("Value a stock based on projected dividends (Gordon Growth Model).")

    with st.form("ddm_form"):
        dividend = st.number_input("Annual Dividend per Share (USD)", min_value=0.01, value=1.50)
        growth = st.slider("Dividend Growth Rate (%)", 0.0, 15.0, 4.0, step=0.1) / 100
        req_return = st.slider("Required Return (%)", 1.0, 20.0, 9.0, step=0.1) / 100
        submitted = st.form_submit_button("Calculate")

    if submitted:
        if req_return <= growth:
            st.error("Required return must exceed the growth rate.")
            return
        model = DDMModel(dividend=dividend, growth_rate=growth, required_return=req_return)
        result = model.calculate()
        st.metric("Intrinsic Value per Share", fmt.currency(result.get("intrinsic_value", 0)))


def page_comps():
    st.title("Comparable Company Analysis")
    st.markdown("Value the target using peer group trading multiples.")

    st.info("Enter peer multiples below (comma-separated P/E values).")
    pe_input = st.text_input("Peer P/E ratios (comma-separated)", value="20,22,18,25,19")
    target_eps = st.number_input("Target Company EPS (USD)", min_value=0.01, value=6.0)

    if st.button("Calculate"):
        try:
            pe_list = [float(x.strip()) for x in pe_input.split(",") if x.strip()]
            peers = [{"pe": p, "ev_ebitda": p * 0.9, "pb": p / 6} for p in pe_list]
            model = CompsModel(peers=peers, target_earnings=target_eps)
            result = model.calculate()
            col1, col2, col3 = st.columns(3)
            col1.metric("Median P/E", fmt.ratio(result.get("median_pe", 0)))
            col2.metric("Implied Price (P/E)", fmt.currency(result.get("implied_price_pe", 0)))
            col3.metric("Mean P/E", fmt.ratio(result.get("mean_pe", 0)))
        except Exception as e:
            st.error(f"Error: {e}")


def page_sensitivity():
    st.title("Sensitivity Analysis")
    st.markdown("Examine how intrinsic value changes across WACC and growth rate assumptions.")
    st.info("Run DCF Valuation first, then return here for a sensitivity table.")
    analyzer = SensitivityAnalyzer()
    wacc_range = [w / 100 for w in range(7, 14)]
    tgr_range = [g / 100 for g in range(1, 5)]
    base_fcfs = [100 * (1.08 ** i) for i in range(5)]
    table = analyzer.run(base_fcfs=base_fcfs, wacc_range=wacc_range, tgr_range=tgr_range, shares=1000)
    if table is not None:
        st.dataframe(table, use_container_width=True)


def page_scenarios():
    st.title("Scenario Analysis")
    st.markdown("Compare Bull, Base, and Bear valuation scenarios.")
    analyzer = ScenarioAnalyzer()
    scenarios = {
        "Bull": {"fcf_growth": 0.15, "wacc": 0.09, "tgr": 0.04},
        "Base": {"fcf_growth": 0.08, "wacc": 0.10, "tgr": 0.025},
        "Bear": {"fcf_growth": 0.02, "wacc": 0.12, "tgr": 0.01},
    }
    base_fcf = 100.0
    shares = 1000
    results = analyzer.run(base_fcf=base_fcf, scenarios=scenarios, shares=shares)
    if results:
        st.table(results)


def page_backtest():
    st.title("Backtest")
    st.markdown("Back-test valuation signals against historical price data.")
    ticker = st.text_input("Ticker", value="AAPL")
    if st.button("Run Backtest"):
        backtester = Backtester()
        result = backtester.run(ticker=ticker)
        if result:
            st.write(result)
        else:
            st.warning("No backtest data available. Ensure data module is configured.")


def page_signals():
    st.title("Valuation Signals")
    st.markdown("Composite buy / hold / sell signal based on multiple models.")
    ticker = st.text_input("Ticker", value="AAPL")
    market_price = st.number_input("Current Market Price (USD)", min_value=0.01, value=175.0)
    intrinsic = st.number_input("Estimated Intrinsic Value (USD)", min_value=0.01, value=210.0)
    if st.button("Generate Signal"):
        engine = SignalEngine(ticker=ticker)
        signal = engine.generate(market_price=market_price, intrinsic_value=intrinsic)
        st.subheader(f"Signal: {signal.get('signal', 'N/A')}")
        st.write(signal)


def page_export():
    st.title("Export Report")
    st.markdown("Export a PDF or Excel summary of your valuation.")
    ticker = st.text_input("Ticker", value="AAPL")
    fmt_choice = st.radio("Format", ["PDF", "Excel"])
    if st.button("Generate Report"):
        exporter = ReportExporter()
        if fmt_choice == "PDF":
            path = exporter.to_pdf(ticker=ticker, data={})
        else:
            path = exporter.to_excel(ticker=ticker, data={})
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                st.download_button("Download Report", f, file_name=os.path.basename(path))
        else:
            st.warning("Report generation failed or dependencies missing.")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

ROUTES = {
    "DCF Valuation": page_dcf,
    "WACC Calculator": page_wacc,
    "DDM Valuation": page_ddm,
    "Comparable Companies": page_comps,
    "Sensitivity Analysis": page_sensitivity,
    "Scenario Analysis": page_scenarios,
    "Backtest": page_backtest,
    "Signals": page_signals,
    "Export Report": page_export,
}

ROUTES[page]()

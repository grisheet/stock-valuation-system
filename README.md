# Stock Valuation System

A production-grade, modular stock valuation platform built with Python and Streamlit.

## Features

| Module | Description |
|--------|-------------|
| **DCF** | Discounted Cash Flow valuation with terminal value |
| **WACC** | Weighted Average Cost of Capital calculator |
| **DDM** | Gordon Growth Model dividend discount valuation |
| **Comps** | Comparable company analysis using peer multiples |
| **Sensitivity** | Two-dimensional sensitivity tables (WACC x growth) |
| **Scenarios** | Bull / Base / Bear scenario modeling |
| **Backtest** | Historical signal back-testing engine |
| **Signals** | Composite BUY / HOLD / SELL signal generator |
| **Reports** | PDF and Excel export of valuation summaries |

## Project Structure

```
stock-valuation-system/
├── app.py                    # Streamlit entry point
├── config.py                 # Central configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── data/
│   ├── __init__.py
│   └── fetcher.py            # Financial data retrieval (yfinance / Alpha Vantage)
├── models/
│   ├── __init__.py
│   ├── dcf.py                # DCF valuation model
│   ├── wacc.py               # WACC calculator
│   ├── ddm.py                # Dividend Discount Model
│   ├── comps.py              # Comparable companies analysis
│   └── signal.py             # Signal engine
├── analysis/
│   ├── __init__.py
│   ├── sensitivity.py        # Sensitivity analysis
│   ├── scenarios.py          # Scenario analysis
│   └── backtest.py           # Back-testing engine
├── visualization/
│   ├── __init__.py
│   └── charts.py             # Plotly chart builders
├── reports/
│   ├── __init__.py
│   └── export.py             # PDF / Excel exporters
├── utils/
│   ├── __init__.py
│   ├── validators.py         # Input validation helpers
│   └── formatting.py         # Display formatting utilities
└── tests/
    ├── __init__.py
    └── test_models_offline.py # Offline unit tests
```

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/grisheet/stock-valuation-system.git
cd stock-valuation-system
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 5. Run the Application

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Running Tests

```bash
pytest tests/ -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage API key | — |
| `DATA_CACHE_TTL` | Cache TTL in seconds | `3600` |
| `DEFAULT_WACC` | Default WACC for DCF | `0.10` |
| `DEFAULT_TERMINAL_GROWTH` | Default terminal growth rate | `0.025` |

## Key Dependencies

- **streamlit** — Interactive web dashboard
- **yfinance** — Market data retrieval
- **pandas / numpy** — Data manipulation
- **plotly** — Interactive charting
- **openpyxl** — Excel export
- **reportlab** — PDF generation (optional)
- **pytest** — Unit testing

## Architecture

```
Streamlit UI (app.py)
       │
       ├── models/        # Core valuation engines
       ├── analysis/      # Sensitivity, scenarios, backtest
       ├── visualization/ # Plotly charts
       ├── reports/       # Export layer
       └── utils/         # Validators + formatters
              │
           data/          # Market data fetcher
```

## License

MIT License — see [LICENSE](LICENSE) for details.

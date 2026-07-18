"""Central configuration for the Stock Valuation System."""
from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / os.getenv("CACHE_DIR", ".cache")
CACHE_DIR.mkdir(exist_ok=True)

# ── Cache ────────────────────────────────────────────────────────────────────
CACHE_TTL: int = int(os.getenv("CACHE_TTL_SECONDS", 3600))  # 1 hour default

# ── API / network ────────────────────────────────────────────────────────────
MAX_RETRIES: int = 3
RETRY_BACKOFF: float = 1.5   # seconds between retries (exponential)
REQUEST_TIMEOUT: int = 15    # seconds

# ── Financial defaults (user-visible; overridable in the UI) ─────────────────
DEFAULT_RISK_FREE_RATE: float = 0.045   # 10-yr US Treasury proxy
DEFAULT_EQUITY_RISK_PREMIUM: float = 0.055
DEFAULT_TERMINAL_GROWTH_RATE: float = 0.025
DEFAULT_PROJECTION_YEARS: int = 5
DEFAULT_MARGIN_OF_SAFETY: float = 0.20  # 20 %

# ── Peers (fallback if user leaves field blank) ───────────────────────────────
DEFAULT_PEERS: dict[str, list[str]] = {
    "AAPL": ["MSFT", "GOOGL", "META"],
    "TSLA": ["F", "GM", "RIVN"],
    "JPM":  ["BAC", "WFC", "C"],
}

# ── Signal thresholds ────────────────────────────────────────────────────────
BUY_THRESHOLD: float = 0.20   # intrinsic > market by this margin → BUY
SELL_THRESHOLD: float = -0.10 # intrinsic < market by this margin → SELL

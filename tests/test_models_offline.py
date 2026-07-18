# tests/test_models_offline.py
"""
Offline unit tests for valuation models.
Run with: pytest tests/ -v
"""

import pytest
from models.dcf import DCFModel
from models.wacc import WACCModel
from models.ddm import DDMModel
from models.comps import CompsModel
from utils.validators import InputValidator
from utils.formatting import Formatter


# ---------------------------------------------------------------------------
# DCF Tests
# ---------------------------------------------------------------------------

class TestDCFModel:
    def test_basic_valuation(self):
        model = DCFModel(
            free_cash_flows=[100, 110, 121, 133, 146],
            wacc=0.10,
            terminal_growth_rate=0.03,
            shares_outstanding=50,
        )
        result = model.calculate()
        assert result["intrinsic_value"] > 0
        assert result["enterprise_value"] > 0

    def test_zero_growth_terminal(self):
        model = DCFModel(
            free_cash_flows=[100] * 5,
            wacc=0.10,
            terminal_growth_rate=0.0,
            shares_outstanding=10,
        )
        result = model.calculate()
        assert result["intrinsic_value"] > 0

    def test_invalid_wacc_raises(self):
        with pytest.raises((ValueError, ZeroDivisionError)):
            model = DCFModel(
                free_cash_flows=[100],
                wacc=0.0,
                terminal_growth_rate=0.03,
                shares_outstanding=10,
            )
            model.calculate()


# ---------------------------------------------------------------------------
# WACC Tests
# ---------------------------------------------------------------------------

class TestWACCModel:
    def test_basic_wacc(self):
        model = WACCModel(
            equity=800,
            debt=200,
            cost_of_equity=0.12,
            cost_of_debt=0.05,
            tax_rate=0.21,
        )
        result = model.calculate()
        assert 0 < result["wacc"] < 1

    def test_all_equity(self):
        model = WACCModel(
            equity=1000,
            debt=0,
            cost_of_equity=0.10,
            cost_of_debt=0.0,
            tax_rate=0.21,
        )
        result = model.calculate()
        assert abs(result["wacc"] - 0.10) < 1e-6


# ---------------------------------------------------------------------------
# DDM Tests
# ---------------------------------------------------------------------------

class TestDDMModel:
    def test_gordon_growth(self):
        model = DDMModel(
            dividend=2.0,
            growth_rate=0.04,
            required_return=0.09,
        )
        result = model.calculate()
        assert result["intrinsic_value"] == pytest.approx(2.0 * 1.04 / (0.09 - 0.04), rel=1e-3)

    def test_required_return_le_growth_raises(self):
        with pytest.raises((ValueError, ZeroDivisionError)):
            model = DDMModel(
                dividend=2.0,
                growth_rate=0.10,
                required_return=0.08,
            )
            model.calculate()


# ---------------------------------------------------------------------------
# Comps Tests
# ---------------------------------------------------------------------------

class TestCompsModel:
    def test_peer_multiples(self):
        peers = [
            {"pe": 20, "ev_ebitda": 10, "pb": 3},
            {"pe": 22, "ev_ebitda": 11, "pb": 3.5},
            {"pe": 18, "ev_ebitda": 9,  "pb": 2.8},
        ]
        model = CompsModel(peers=peers, target_earnings=5.0)
        result = model.calculate()
        assert result["median_pe"] > 0
        assert result["implied_price_pe"] > 0


# ---------------------------------------------------------------------------
# Validator Tests
# ---------------------------------------------------------------------------

class TestInputValidator:
    def test_valid_ticker(self):
        assert InputValidator.validate_ticker("AAPL") is True

    def test_invalid_ticker(self):
        assert InputValidator.validate_ticker("") is False
        assert InputValidator.validate_ticker("A" * 20) is False

    def test_positive_number(self):
        assert InputValidator.validate_positive_number(10.5) is True
        assert InputValidator.validate_positive_number(-1) is False
        assert InputValidator.validate_positive_number(0) is False

    def test_rate_range(self):
        assert InputValidator.validate_rate(0.05) is True
        assert InputValidator.validate_rate(-0.01) is False
        assert InputValidator.validate_rate(1.5) is False


# ---------------------------------------------------------------------------
# Formatter Tests
# ---------------------------------------------------------------------------

class TestFormatter:
    def test_currency(self):
        assert Formatter.currency(1234.5) == "$1,234.50"

    def test_percent(self):
        result = Formatter.percent(0.1234)
        assert "12.3" in result

    def test_large_currency_millions(self):
        result = Formatter.large_currency(1_500_000)
        assert "M" in result or "1.5" in result

    def test_ratio(self):
        result = Formatter.ratio(15.7)
        assert "15.7" in result

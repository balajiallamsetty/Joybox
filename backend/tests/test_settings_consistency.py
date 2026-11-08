import pytest
from app import create_app
from app.config import Config
from app.services.catalog_service import CatalogService

def test_settings_reconciled_defaults():
    """Verify default values align across config."""
    app = create_app({"TESTING": True})
    assert app.config["HOLD_DURATION_MINUTES"] == 15
    assert app.config["CHECKOUT_GRACE_MINUTES"] == 15
    assert app.config["GST_RATE_PERCENT"] == 0.0
    assert app.config["REFUND_WINDOW_FULL_HOURS"] == 48
    assert app.config["REFUND_WINDOW_PARTIAL_HOURS"] == 24
    assert app.config["REFUND_WINDOW_PARTIAL_PERCENT"] == 50

def test_settings_environment_overrides():
    """Verify environment overrides customize hold TTL, GST rate, and refund tiers."""
    custom_cfg = {
        "TESTING": True,
        "HOLD_DURATION_MINUTES": 20,
        "CHECKOUT_GRACE_MINUTES": 20,
        "GST_RATE_PERCENT": 18.0,
        "REFUND_WINDOW_FULL_HOURS": 72,
        "REFUND_WINDOW_PARTIAL_HOURS": 36,
        "REFUND_WINDOW_PARTIAL_PERCENT": 40,
    }
    app = create_app(custom_cfg)
    assert app.config["HOLD_DURATION_MINUTES"] == 20
    assert app.config["CHECKOUT_GRACE_MINUTES"] == 20
    assert app.config["GST_RATE_PERCENT"] == 18.0
    assert app.config["REFUND_WINDOW_FULL_HOURS"] == 72
    assert app.config["REFUND_WINDOW_PARTIAL_HOURS"] == 36
    assert app.config["REFUND_WINDOW_PARTIAL_PERCENT"] == 40

def test_catalog_service_honors_configured_gst_rate():
    """Verify CatalogService uses configured GST_RATE_PERCENT when not passed in query."""
    class DummyPackageRepo:
        def find_by_code(self, code):
            return {"code": "gold", "name": "Gold", "pricePerHourMinor": 100000, "active": True}

    class DummyAddonRepo:
        def find_by_codes(self, codes):
            return []

    class DummyOfferRepo:
        def find_active_for_package(self, code):
            return None

    class Config18:
        GST_RATE_PERCENT = 18.0

    svc = CatalogService(
        DummyPackageRepo(),
        DummyAddonRepo(),
        DummyOfferRepo(),
        config=Config18()
    )
    quote = svc.calculate_quote("gold", 1, apply_promo=False)
    assert quote["taxRatePercent"] == 18.0
    assert quote["taxAmountMinor"] == 18000
    assert quote["totalAmountMinor"] == 118000
    assert quote["totalRupees"] == 1180.0

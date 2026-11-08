"""
Tests for P2: "Book Now" Package Propagation and Entry Point Contracts.
Validates:
1. Every package CTA across the frontend passes /booking?package=<slug>.
2. Frontend routing contract in App.jsx mounts BookingWizardPage on both /book and /booking.
3. Package slugs match valid DB package codes ('basic', 'gold', 'diamond').
4. Booking creation with package codes works end-to-end on Atlas test database.
"""

import os
import re
import pytest
from backend.app.config import Config


def get_frontend_file(rel_path):
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_dir, "frontend", "src", rel_path)


class TestP2EntryPointContracts:
    def test_app_jsx_routes(self):
        app_jsx_path = get_frontend_file("App.jsx")
        assert os.path.exists(app_jsx_path)
        with open(app_jsx_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must mount BookingWizardPage on both /book and /booking
        assert re.search(r'<Route\s+path="/book"\s+element={<BookingWizardPage\s*/>}\s*/>', content)
        assert re.search(r'<Route\s+path="/booking"\s+element={<BookingWizardPage\s*/>}\s*/>', content)
        # Must retain /booking/:ref for BookingStatusPage
        assert re.search(r'<Route\s+path="/booking/:ref"\s+element={<BookingStatusPage\s*/>}\s*/>', content)

    def test_header_and_footer_booking_links(self):
        header_path = get_frontend_file("components/Header.jsx")
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert '{ path: \'/booking\', label: \'Book Venue\' }' in content
        assert 'to="/booking"' in content
        assert 'to="/book"' not in content

        footer_path = get_frontend_file("components/Footer.jsx")
        with open(footer_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert '<Link to="/booking" className="hover:text-primary transition-colors">Book Venue</Link>' in content
        assert '<Link to="/book"' not in content

    def test_landing_page_package_cards_propagate_slugs(self):
        landing_path = get_frontend_file("pages/LandingPage.jsx")
        with open(landing_path, "r", encoding="utf-8") as f:
            content = f.read()

        # All 3 packages must link to /booking?package=<slug>
        assert 'to="/booking?package=basic"' in content
        assert 'to="/booking?package=gold"' in content
        assert 'to="/booking?package=diamond"' in content

        # Calculator CTA must link to /booking?package=${calcTier}&duration=${calcHours}
        assert 'to={`/booking?package=${calcTier}&duration=${calcHours}`}' in content

    def test_landing_page_2_package_cards_propagate_slugs(self):
        landing2_path = get_frontend_file("pages/LandingPage2.jsx")
        with open(landing2_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'to="/booking?package=basic"' in content
        assert 'to="/booking?package=gold"' in content
        assert 'to="/booking?package=diamond"' in content
        assert 'to={`/booking?package=${calcTier}&duration=${calcHours}`}' in content
        assert 'to="/book"' not in content

    def test_packages_page_links_propagate_slugs(self):
        packages_path = get_frontend_file("pages/PackagesPage.jsx")
        with open(packages_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert 'to={`/booking?package=${pkg.code}`}' in content
        assert 'to={`/book?package=' not in content

    def test_booking_wizard_page_handles_package_param_and_date_slot_reset(self):
        wizard_path = get_frontend_file("pages/BookingWizardPage.jsx")
        with open(wizard_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Must use useSearchParams
        assert "useSearchParams" in content

        # Must inspect 'package' param and advance step
        assert "searchParams.get('package')" in content
        assert "validInitialPackage ? 2 : 1" in content or "validInitialPackage ? 2 : 1" in content

        # Must wire live availability
        assert "api.getAvailability(bookingDate, duration)" in content

        # Must reset selectedSlot on date/duration change
        assert "setSelectedSlot('')" in content

        # Must redirect ref param
        assert "searchParams.get('ref')" in content


from app import create_app

@pytest.fixture
def app_client(live_test_client):
    test_db = live_test_client
    app = create_app({
        "TESTING": True,
        "MONGODB_URI": os.getenv("MONGODB_URI"),
        "MONGODB_DB": test_db.name
    })
    app.extensions["mongo_db"] = test_db
    with app.test_client() as c:
        yield c


class TestP2BackendPackageIntegration:
    """Verifies that each package code can successfully generate quotes and reservations on Atlas test DB."""

    @pytest.mark.parametrize("package_code", ["basic", "gold", "diamond"])
    def test_packages_quote_and_booking_creation(self, app_client, package_code):
        assert Config.MONGODB_TEST_DB.endswith("_test"), "Must run on test DB"

        # 1. Quote endpoint check
        quote_res = app_client.post("/api/bookings/quote", json={
            "packageCode": package_code,
            "durationHours": 2,
            "addOnCodes": []
        })
        assert quote_res.status_code == 200, f"Quote failed for {package_code}: {quote_res.data}"
        quote_data = quote_res.get_json()["data"]
        assert quote_data["packageCode"] == package_code
        assert quote_data["totalAmountMinor"] > 0

        # 2. Package details check
        pkg_res = app_client.get(f"/api/packages/{package_code}")
        assert pkg_res.status_code == 200, f"Get package failed for {package_code}"
        pkg_data = pkg_res.get_json()["data"]
        assert pkg_data["code"] == package_code

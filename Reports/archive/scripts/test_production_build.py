import os
import sys
import time
import threading
import http.server
import socketserver
from playwright.sync_api import sync_playwright

DIST_DIR = os.path.abspath("frontend/dist")
AUDIT_DIR = os.path.abspath("docs/visual_audit")
os.makedirs(AUDIT_DIR, exist_ok=True)

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_GET(self):
        path_without_query = self.path.split('?')[0]
        full_path = self.translate_path(path_without_query)
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            self.path = "/index.html"
        return super().do_GET()

def start_server(port=4173):
    server = socketserver.TCPServer(("127.0.0.1", port), SPAHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def test_production_build():
    print("Testing production build dist...", flush=True)
    server = start_server(4173)
    time.sleep(1)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            # TEST 1: ?preview=confirmed on /booking in production
            print("1. Testing /booking?preview=confirmed on production build...", flush=True)
            page.goto("http://127.0.0.1:4173/booking?preview=confirmed", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            # Assert dev state switcher is NOT in DOM
            switcher_count = page.locator('aside[aria-label="Interactive State Preview Switcher"]').count()
            print(f"   Interactive State Preview Switcher count: {switcher_count} (Must be 0)", flush=True)
            assert switcher_count == 0, f"Expected 0 switchers in production build, found {switcher_count}"

            # Assert mock confirmed banner is NOT displayed
            mock_banner_count = page.locator('text="Party Locked & Confirmed!"').count()
            print(f"   Mock Confirmed Banner count: {mock_banner_count} (Must be 0)", flush=True)
            assert mock_banner_count == 0, f"Expected mock confirmed banner to be hidden in production, found {mock_banner_count}"

            # Assert real lookup interface is displayed
            lookup_heading = page.locator('text="Track Your Celebration Booking"')
            assert lookup_heading.count() == 1, "Expected real booking lookup interface in production"
            print("   Real Booking Lookup Form is correctly displayed.", flush=True)

            out_booking = os.path.join(AUDIT_DIR, "prod_build_booking_no_preview.png")
            page.screenshot(path=out_booking)
            print(f"   Screenshot saved: {out_booking}", flush=True)

            # TEST 2: /landing-2 on production build
            print("2. Testing /landing-2 on production build...", flush=True)
            page.goto("http://127.0.0.1:4173/landing-2", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            # Assert font switcher bar is NOT in DOM
            font_switcher_count = page.locator('text="Landing Page 2 Export Variant"').count()
            print(f"   Font Dev Switcher count: {font_switcher_count} (Must be 0)", flush=True)
            assert font_switcher_count == 0, f"Expected 0 font switchers in production build, found {font_switcher_count}"

            # Assert Landing 2 uses Fredoka/Poppins
            root_div = page.locator('#root > div')
            classes = root_div.get_attribute("class") or ""
            assert "font-poppins" in classes, "Expected Landing Page 2 to have font-poppins class"
            print("   Landing Page 2 strictly retains Fredoka/Poppins styling.", flush=True)

            out_landing2 = os.path.join(AUDIT_DIR, "prod_build_landing_2_no_font_switcher.png")
            page.screenshot(path=out_landing2)
            print(f"   Screenshot saved: {out_landing2}", flush=True)

            # TEST 3: /admin route in production
            print("3. Testing /admin route redirection in production build...", flush=True)
            page.goto("http://127.0.0.1:4173/admin", timeout=15000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
            current_url = page.url
            print(f"   Attempted /admin, redirected to: {current_url}", flush=True)
            assert current_url.endswith("/admin/login") or current_url.endswith("/"), f"Expected redirect to '/admin/login' or '/', but got {current_url}"
            print("   Admin console route is properly locked and hidden in production.", flush=True)

            browser.close()
            print("\nALL PRODUCTION BUILD INVARIANTS VERIFIED SUCCESSFULLY!", flush=True)

    finally:
        server.shutdown()
        print("Server shutdown.", flush=True)

if __name__ == "__main__":
    test_production_build()


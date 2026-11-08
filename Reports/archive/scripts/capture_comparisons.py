import os
import sys
import time
import threading
import http.server
import socketserver
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

AUDIT_DIR = os.path.abspath("docs/visual_audit")
DIST_DIR = os.path.abspath("frontend/dist")
os.makedirs(AUDIT_DIR, exist_ok=True)

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIST_DIR, **kwargs)

    def do_GET(self):
        # Strip query params
        path_without_query = self.path.split('?')[0]
        full_path = self.translate_path(path_without_query)
        if not os.path.exists(full_path) or os.path.isdir(full_path):
            self.path = "/index.html"
        return super().do_GET()

def start_server(port=4173):
    handler = SPAHandler
    server = socketserver.TCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server

def wait_for_images(page):
    """Ensure all images on the page have loaded completely."""
    page.wait_for_load_state("networkidle")
    page.evaluate("""
        () => {
            return Promise.all(
                Array.from(document.images).map(img => {
                    if (img.complete) return Promise.resolve();
                    return new Promise((resolve) => {
                        img.onload = resolve;
                        img.onerror = resolve;
                        setTimeout(resolve, 2000);
                    });
                })
            );
        }
    """)
    page.wait_for_timeout(1000)

def create_side_by_side(react_img_path, stitch_img_path, output_path, title):
    if not os.path.exists(react_img_path) or not os.path.exists(stitch_img_path):
        print(f"Skipping composite, missing file: {react_img_path} or {stitch_img_path}", flush=True)
        return

    react_im = Image.open(react_img_path)
    stitch_im = Image.open(stitch_img_path)

    # Match heights
    target_height = max(react_im.height, stitch_im.height)
    if react_im.height != target_height:
        scale = target_height / react_im.height
        react_im = react_im.resize((int(react_im.width * scale), target_height), Image.Resampling.LANCZOS)
    if stitch_im.height != target_height:
        scale = target_height / stitch_im.height
        stitch_im = stitch_im.resize((int(stitch_im.width * scale), target_height), Image.Resampling.LANCZOS)

    header_height = 50
    total_width = react_im.width + stitch_im.width + 20
    total_height = target_height + header_height

    composite = Image.new("RGB", (total_width, total_height), color=(26, 16, 48))
    draw = ImageDraw.Draw(composite)

    # Paste images
    composite.paste(react_im, (0, header_height))
    composite.paste(stitch_im, (react_im.width + 20, header_height))

    # Draw divider
    draw.rectangle([react_im.width, 0, react_im.width + 20, total_height], fill=(45, 25, 75))

    # Add text labels
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    draw.text((20, 15), f"React Implementation: {title}", fill=(255, 225, 117), font=font)
    draw.text((react_im.width + 40, 15), f"Stitch Export Design: {title}", fill=(255, 217, 228), font=font)

    composite.save(output_path)
    print(f"Saved side-by-side comparison: {os.path.basename(output_path)}", flush=True)

def run():
    print("Starting internal SPA HTTP server on port 4173...", flush=True)
    server = start_server(4173)
    time.sleep(1)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            tasks = [
                # Landing Page 2
                {
                    "url": "http://127.0.0.1:4173/landing-2",
                    "prefix": "landing_2",
                    "title": "Landing Page 2"
                },
                # Mobile Celebration Flow
                {
                    "url": "http://127.0.0.1:4173/mobile-booking",
                    "prefix": "mobile_booking",
                    "title": "Mobile Celebration Booking Flow"
                },
                # Gallery (re-capture 390px with images loaded)
                {
                    "url": "http://127.0.0.1:4173/gallery",
                    "prefix": "gallery",
                    "title": "Themes & Gallery"
                },
                # Booking Status States
                {
                    "url": "http://127.0.0.1:4173/booking?preview=confirmed",
                    "prefix": "booking_status_confirmed",
                    "title": "Status: Confirmed"
                },
                {
                    "url": "http://127.0.0.1:4173/booking?preview=inquiry",
                    "prefix": "booking_status_inquiry",
                    "title": "Status: Inquiry Review"
                },
                {
                    "url": "http://127.0.0.1:4173/booking?preview=pending",
                    "prefix": "booking_status_pending",
                    "title": "Status: Pay Token Pending"
                },
                {
                    "url": "http://127.0.0.1:4173/booking?preview=failed",
                    "prefix": "booking_status_failed",
                    "title": "Status: Session Failed"
                },
            ]

            viewports = [
                {"name": "1440px", "width": 1440, "height": 900},
                {"name": "390px", "width": 390, "height": 844}
            ]

            for item in tasks:
                for vp in viewports:
                    print(f"Capturing {item['title']} at {vp['name']}...", flush=True)
                    page = browser.new_page(viewport={"width": vp["width"], "height": vp["height"]})
                    try:
                        page.goto(item["url"], timeout=15000)
                        wait_for_images(page)
                        out_file = os.path.join(AUDIT_DIR, f"react_{item['prefix']}_{vp['name']}.png")
                        page.screenshot(path=out_file)
                        print(f"Captured: react_{item['prefix']}_{vp['name']}.png", flush=True)
                    except Exception as e:
                        print(f"Error capturing {item['url']} at {vp['name']}: {e}", flush=True)
                    finally:
                        page.close()

            browser.close()

    finally:
        server.shutdown()
        print("Server stopped.", flush=True)

    # Now generate side-by-side comparisons
    comparisons = [
        ("react_landing_2_1440px.png", "stitch_landing_2_1440px.png", "compare_landing_2_1440px.png", "Landing Page 2 (Desktop 1440px)"),
        ("react_landing_2_390px.png", "stitch_landing_2_390px.png", "compare_landing_2_390px.png", "Landing Page 2 (Mobile 390px)"),
        ("react_mobile_booking_1440px.png", "stitch_mobile_booking_1440px.png", "compare_mobile_booking_1440px.png", "Mobile Booking Flow (Desktop 1440px)"),
        ("react_mobile_booking_390px.png", "stitch_mobile_booking_390px.png", "compare_mobile_booking_390px.png", "Mobile Booking Flow (Mobile 390px)"),
        ("react_gallery_390px.png", "stitch_gallery_390px.png", "compare_gallery_390px.png", "Gallery (Mobile 390px Fully Loaded)"),
        ("react_booking_status_confirmed_1440px.png", "stitch_booking_status_1440px.png", "compare_booking_status_1440px.png", "Booking Status Confirmed (Desktop 1440px)"),
        ("react_booking_status_confirmed_390px.png", "stitch_booking_status_390px.png", "compare_booking_status_390px.png", "Booking Status Confirmed (Mobile 390px)")
    ]

    for react_f, stitch_f, comp_f, desc in comparisons:
        r_path = os.path.join(AUDIT_DIR, react_f)
        s_path = os.path.join(AUDIT_DIR, stitch_f)
        c_path = os.path.join(AUDIT_DIR, comp_f)
        create_side_by_side(r_path, s_path, c_path, desc)

    print("All captures and comparisons completed successfully!", flush=True)

if __name__ == "__main__":
    run()


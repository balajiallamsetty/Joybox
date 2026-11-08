import sys
import os
import re

POLICY_PAGES = [
    ("Terms of Service", "/terms", "frontend/src/pages/TermsPage.jsx"),
    ("Privacy Policy", "/privacy", "frontend/src/pages/PrivacyPage.jsx"),
    ("Refund Policy", "/refund-policy", "frontend/src/pages/RefundPolicyPage.jsx"),
]

PLACEHOLDER_MARKERS = [
    "Owner Review Placeholder Notice",
    "[Owner Review Placeholder Notice]",
    "OWNER REVIEW PLACEHOLDER",
]

def check_source_files(repo_root: str):
    failures = []
    for title, route, file_rel in POLICY_PAGES:
        file_path = os.path.join(repo_root, file_rel)
        if not os.path.exists(file_path):
            failures.append((title, route, f"File not found: {file_path}"))
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        for marker in PLACEHOLDER_MARKERS:
            if marker.lower() in content.lower():
                failures.append((title, route, f"Contains placeholder marker: '{marker}'"))
                break

    return failures

def check_live_routes(base_url: str):
    import urllib.request
    failures = []
    base = base_url.rstrip("/")

    for title, route, _ in POLICY_PAGES:
        target_url = f"{base}{route}"
        try:
            req = urllib.request.Request(target_url, headers={"User-Agent": "JoyboxPolicyChecker/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                for marker in PLACEHOLDER_MARKERS:
                    if marker.lower() in html.lower():
                        failures.append((title, route, f"Contains placeholder marker in rendered HTML: '{marker}'"))
                        break
        except Exception as exc:
            failures.append((title, route, f"Failed to fetch {target_url}: {exc}"))

    return failures

def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    base_url = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].startswith("http") else None

    if base_url:
        print(f"[*] Checking live policy pages at {base_url}...")
        failures = check_live_routes(base_url)
    else:
        print(f"[*] Checking local source policy pages in {repo_root}...")
        failures = check_source_files(repo_root)

    if failures:
        print("\n[!] PRE-LAUNCH GATE FAILED: Policy placeholders detected:")
        for title, route, reason in failures:
            print(f"    - {title} ({route}): {reason}")
        print("\nACTION REQUIRED: Owner must approve final legal text and remove placeholder notices before public launch.\n")
        sys.exit(1)
    else:
        print("\n[+] PASS: All policy pages have finalized text with zero placeholder notices.")
        sys.exit(0)

if __name__ == "__main__":
    main()

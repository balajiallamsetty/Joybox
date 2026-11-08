import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

for filename in ["LandingPage.jsx", "LandingPage2.jsx", "PackagesPage.jsx", "Header.jsx", "Footer.jsx"]:
    filepath = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "pages" if "Page" in filename else "components", filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for idx, line in enumerate(lines, 1):
                if re.search(r'(Book|Reserve|Select\s+Basic|Select\s+Gold|Select\s+Diamond)', line, re.IGNORECASE):
                    if not line.strip().startswith("//") and not line.strip().startswith("/*"):
                        print(f"{filename}:{idx} -> {line.strip()}")

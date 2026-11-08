import os
import re

frontend_src = os.path.join(os.path.dirname(__file__), "..", "frontend", "src")

booking_pattern = re.compile(r'(/book(?:ing)?(?:\?[^"\'`]*)?|to=[\'"{`]/book(?:ing)?|href=[\'"{`]/book(?:ing)?)')

print("================================================================================")
print("INVENTORY OF ALL BOOKING ENTRY POINTS & LINKS IN FRONTEND")
print("================================================================================")

results = []

for root, dirs, files in os.walk(frontend_src):
    for f in files:
        if f.endswith(".jsx") or f.endswith(".js"):
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, frontend_src)
            with open(full_path, "r", encoding="utf-8") as file:
                lines = file.readlines()
                for idx, line in enumerate(lines, 1):
                    line_str = line.strip()
                    if "/book" in line_str:
                        results.append((rel_path, idx, line_str))

for rel_path, line_no, line_str in results:
    print(f"{rel_path}:{line_no} -> {line_str}")

print(f"\nTotal matches: {len(results)}")

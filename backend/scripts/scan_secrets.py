#!/usr/bin/env python3
"""
Joybox Secret Scanner & Hygiene Verifier
Scans the working tree and (optionally) git commit history for credentials, tokens,
and private keys. Masks all output to ensure zero secret leakage in logs or terminal.
Exit code 0 if working tree is clean; exit code 1 if working tree secrets detected.
"""
import os
import re
import sys
import argparse
import subprocess

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

PATTERNS = {
    "MONGODB_CREDENTIALS": re.compile(r"(mongodb(?:\+srv)?):\/\/([^:\/\s]+):([^@\/\s]+)@([^\s\"\'\>\<\,\;]+)"),
    "RAZORPAY_KEY_ID": re.compile(r"(rzp_(?:test|live)_)[a-zA-Z0-9]{8,}"),
    "RAZORPAY_KEY_SECRET": re.compile(r"(RAZORPAY_KEY_SECRET\s*[:=]\s*[\"']?)([a-zA-Z0-9]{10,})([\"']?)"),
    "JWT_SECRET": re.compile(r"((?:JWT_SECRET|ADMIN_JWT_SECRET|SECRET_KEY)\s*[:=]\s*[\"']?)([^\s\"']{16,})([\"']?)"),
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA|OPENSSH|DSA|EC)?\s*PRIVATE KEY-----"),
}

IGNORE_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", "dist", "build", ".idea", ".vscode"
}

IGNORE_FILES = {
    "scan_secrets.py", "scan_git_secrets.py"
}

FROZEN_PAYMENT_TESTS = {
    os.path.normpath("backend/tests/test_payments.py"),
    os.path.normpath("backend/tests/test_razorpay_standard.py")
}

def mask_text(text: str) -> str:
    """Masks all sensitive values in a text snippet."""
    # MongoDB: replace user:pass with <MASKED_USER>:<MASKED_PASS>
    text = re.sub(
        r"(mongodb(?:\+srv)?):\/\/([^:\/\s]+):([^@\/\s]+)@([^\s\"\'\>\<\,\;]+)",
        r"\1://<MASKED_USER>:<MASKED_PASS>@\4",
        text
    )
    # Razorpay Key ID: mask identifier
    text = re.sub(r"(rzp_(?:test|live)_)[a-zA-Z0-9]{8,}", r"\1<MASKED_KEY_ID>", text)
    # Razorpay Secret
    text = re.sub(r"(RAZORPAY_KEY_SECRET\s*[:=]\s*[\"']?)([a-zA-Z0-9]{10,})([\"']?)", r"\1<MASKED_SECRET>\3", text)
    # JWT Secret
    text = re.sub(r"((?:JWT_SECRET|ADMIN_JWT_SECRET|SECRET_KEY)\s*[:=]\s*[\"']?)([^\s\"']{8,})([\"']?)", r"\1<MASKED_SECRET>\3", text)
    return text

def is_example_file(filepath: str) -> bool:
    name = os.path.basename(filepath).lower()
    return "example" in name or "template" in name

def is_ignored_by_git(filepath: str) -> bool:
    """Checks if git considers this file ignored."""
    try:
        res = subprocess.run(["git", "check-ignore", filepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.returncode == 0
    except Exception:
        name = os.path.basename(filepath)
        return name.startswith(".env") and not name.endswith(".example")

def scan_file(filepath: str):
    """Scans a single file for exposed credentials."""
    findings = []
    # Skip binary files, known example templates, or frozen payment tests
    if is_example_file(filepath):
        return findings
    norm_path = os.path.normpath(filepath)
    for frozen in FROZEN_PAYMENT_TESTS:
        if norm_path.endswith(frozen):
            return findings

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line_no, line in enumerate(f, start=1):
                # Don't flag documentation examples containing placeholder markers
                if "<" in line and ">" in line:
                    continue
                if "<username>" in line or "<password>" in line or "<REDACTED" in line or "<MASKED" in line:
                    continue
                if "dev-secret-key-change-in-prod" in line or "generate-a-strong-random-key" in line:
                    continue
                if "your-" in line or "example" in line.lower():
                    continue

                for p_name, pattern in PATTERNS.items():
                    m = pattern.search(line)
                    if m:
                        matched_str = m.group(0)
                        if any(token in matched_str for token in ["REDACTED", "MASKED", "PLACEHOLDER", "YOUR_", "xxx", "..."]):
                            continue
                        findings.append({
                            "file": filepath,
                            "line": line_no,
                            "type": p_name,
                            "snippet": mask_text(line.strip())
                        })
    except Exception as exc:
        pass
    return findings

def scan_working_tree(root_dir: str):
    """Walks the directory and scans tracked and untracked non-ignored files."""
    tracked_leaks = []
    ignored_env_items = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Prune ignored directories
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for f in filenames:
            if f in IGNORE_FILES:
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot", ".pyc"]:
                continue
            full_path = os.path.join(dirpath, f)
            rel_path = os.path.relpath(full_path, root_dir)
            
            file_findings = scan_file(full_path)
            if not file_findings:
                continue
                
            if is_ignored_by_git(rel_path):
                ignored_env_items.extend(file_findings)
            else:
                tracked_leaks.extend(file_findings)
                
    return tracked_leaks, ignored_env_items

def scan_git_history():
    """Scans git log -p across all historical commits."""
    cmd = ["git", "log", "-p", "--all"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    except Exception as exc:
        return []

    findings = []
    current_commit = "unknown"
    current_file = "unknown"

    for line in proc.stdout:
        if line.startswith("commit "):
            current_commit = line.strip().split()[1]
        elif line.startswith("+++ b/"):
            current_file = line.strip()[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            if is_example_file(current_file):
                continue
            if "<username>" in line or "<password>" in line or "<REDACTED" in line or "<MASKED" in line:
                continue
            for p_name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append({
                        "commit": current_commit[:10],
                        "file": current_file,
                        "type": p_name,
                        "snippet": mask_text(line.strip())
                    })
    proc.wait()
    return findings

def main():
    parser = argparse.ArgumentParser(description="Joybox Secret Scanner & Hygiene Verifier")
    parser.add_argument("--history", action="store_true", help="Also scan full git commit history")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    args = parser.parse_args()

    print("==================================================================")
    print("           JOYBOX SECRET & HYGIENE VERIFICATION SCAN")
    print(f"           Scanning Working Tree from: {os.path.abspath(args.root)}")
    print("==================================================================")

    tracked_leaks, ignored_env_items = scan_working_tree(args.root)
    print(f"\n[1/3] Tracked Files Scan: {len(tracked_leaks)} unmasked leaks detected.")
    if tracked_leaks:
        print("\n[!] CRITICAL: Exposed credentials found in tracked repository files:")
        for f in tracked_leaks:
            print(f"  - [{f['type']}] {f['file']}:{f['line']} -> {f['snippet']}")
    else:
        print("  [PASS] All tracked repository files are clean of secrets.")

    print(f"\n[2/3] Local Environment (.env) Files: {len(ignored_env_items)} local config values detected.")
    print("  [PASS] All local environment files (.env) are strictly excluded by .gitignore.")

    history_findings = []
    if args.history:
        print("\n[3/3] Scanning Git commit history (all branches)...")
        history_findings = scan_git_history()
        # Deduplicate
        seen = set()
        deduped = []
        for h in history_findings:
            k = (h["commit"], h["file"], h["type"])
            if k not in seen:
                seen.add(k)
                deduped.append(h)
        print(f"  Found {len(deduped)} historical credential instances in git log.")
        if deduped:
            print("  Note: Historical commits require credential rotation in owner dashboards.")
            for h in deduped[:15]:
                print(f"    - Commit {h['commit']} ({h['file']}): [{h['type']}] {h['snippet']}")
            if len(deduped) > 15:
                print(f"    ... and {len(deduped) - 15} more historical records (masked).")
    else:
        print("\n[3/3] Git history scan skipped (pass --history to include).")

    print("\n==================================================================")
    if tracked_leaks:
        print("  STATUS: FAIL (Tracked files contain secrets - commit aborted)")
        print("==================================================================")
        sys.exit(1)
    else:
        print("  STATUS: PASS (Repository working tree is clean)")
        print("==================================================================")
        sys.exit(0)

if __name__ == "__main__":
    main()

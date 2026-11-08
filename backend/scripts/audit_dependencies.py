"""
Automated Dependency Vulnerability Audit for Joybox Party Room.
Runs pip-audit against backend/requirements.txt.
"""
import sys
import subprocess

def run_audit():
    print("[*] Running pip-audit on backend/requirements.txt...")
    cmd = [sys.executable, "-m", "pip_audit", "-r", "backend/requirements.txt"]
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("[OK] Dependency vulnerability audit PASSED: 0 vulnerabilities found.")
    else:
        print("[FAIL] Vulnerabilities detected! Please review and update packages.")
    sys.exit(res.returncode)

if __name__ == "__main__":
    run_audit()


import os
import re

def list_external_urls():
    p = 'frontend/src'
    urls = set()
    for r, d, fs in os.walk(p):
        for f in fs:
            if f.endswith(('.jsx', '.js', '.css', '.html')):
                content = open(os.path.join(r, f), encoding='utf-8').read()
                matches = re.findall(r'https?://[^\s"\'<>`]+', content)
                for m in matches:
                    urls.add(m)
    print(f"Total external URLs found: {len(urls)}")
    for u in sorted(urls):
        print(u)

def scan_patterns():
    patterns = {
        "TODO": re.compile(r'\bTODO\b', re.IGNORECASE),
        "FIXME": re.compile(r'\bFIXME\b', re.IGNORECASE),
        "HACK": re.compile(r'\bHACK\b', re.IGNORECASE),
        "Phase N": re.compile(r'\bPhase\s+[0-9]\b', re.IGNORECASE),
        "console.log": re.compile(r'\bconsole\.log\b'),
        "print(": re.compile(r'\bprint\s*\('),
    }
    
    scan_dirs = ['backend/app', 'frontend/src']
    findings = {k: [] for k in patterns}
    
    for sdir in scan_dirs:
        for r, d, fs in os.walk(sdir):
            if any(ign in r for ign in ['node_modules', '.git', '__pycache__', 'dist', '.venv']):
                continue
            for f in fs:
                if f.endswith(('.py', '.js', '.jsx', '.css')):
                    fpath = os.path.join(r, f)
                    try:
                        lines = open(fpath, encoding='utf-8', errors='ignore').readlines()
                    except Exception:
                        continue
                    for idx, line in enumerate(lines, 1):
                        for pat_name, regex in patterns.items():
                            if regex.search(line):
                                findings[pat_name].append((fpath, idx, line.strip()))
                                
    for pat_name, matches in findings.items():
        print(f"\n=== Pattern: {pat_name} (Total: {len(matches)}) ===")
        for fpath, idx, text in matches[:15]:
            print(f"  {fpath}:{idx} -> {text[:100]}")
        if len(matches) > 15:
            print(f"  ... and {len(matches) - 15} more.")

def check_admin_auth():
    import ast
    tree = ast.parse(open('backend/app/routes/admin_routes.py', encoding='utf-8').read())
    endpoints = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            route_decorator = None
            auth_decorators = []
            for dec in node.decorator_list:
                dec_str = ast.unparse(dec)
                if 'admin_bp' in dec_str:
                    route_decorator = dec_str
                if any(x in dec_str for x in ['require_admin_auth', 'require_role', 'admin_required', 'require_admin_session']):
                    auth_decorators.append(dec_str)
            if route_decorator:
                endpoints.append((node.name, route_decorator, auth_decorators))
    print(f"\n=== Admin Endpoints Auth Check (Total: {len(endpoints)}) ===")
    unprotected = []
    for name, route, auths in endpoints:
        is_login = 'login' in route
        status = "PROTECTED" if auths else ("PUBLIC LOGIN" if is_login else "UNPROTECTED!!")
        print(f"  {name:30} {route:40} [{status}] -> {auths}")
        if not auths and not is_login:
            unprotected.append((name, route))
    if unprotected:
        print(f"\n[!] WARNING: {len(unprotected)} unprotected admin routes found:")
        for u in unprotected:
            print("   ", u)
    else:
        print("\n[+] ALL admin endpoints (except public /auth/login) are authenticated!")

if __name__ == '__main__':
    scan_patterns()
    check_admin_auth()


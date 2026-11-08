import os
import sys
import socket
from app import create_app

app = create_app()

def _check_port_available(host: str, port: int) -> bool:
    """Verifies that the target socket port is not already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    debug_mode = app.config.get("DEBUG", False)

    # In development with reloader, WERKZEUG_RUN_MAIN indicates the child worker process
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if not is_reloader_child:
        if not _check_port_available(host, port):
            print(
                f"\n[!] STARTUP ERROR: Port {port} on {host} is already in use by another process.\n"
                f"    Please terminate the conflicting process or specify a different port (e.g. set PORT={port + 1}).\n",
                file=sys.stderr
            )
            sys.exit(1)

    try:
        app.run(host=host, port=port, debug=debug_mode, use_reloader=debug_mode)
    except KeyboardInterrupt:
        print("\n[*] Joybox Party Room backend shutdown gracefully.")
        sys.exit(0)

import sys
import os
import argparse
import signal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import DEFAULT_SERVER_PORT, DEFAULT_SERVER_HOST, get_local_lan_ip
from server.server_core import LANBoxServer

def main():
    parser = argparse.ArgumentParser(description="LANBOX Central TCP Server")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVER_PORT, help=f"Port to bind server (default: {DEFAULT_SERVER_PORT})")
    parser.add_argument("--host", type=str, default=DEFAULT_SERVER_HOST, help=f"Host address to bind (default: {DEFAULT_SERVER_HOST})")
    parser.add_argument("--db", type=str, default="lanbox.db", help="SQLite database filename (default: lanbox.db)")
    args = parser.parse_args()

    lan_ip = get_local_lan_ip()

    print("=" * 60)
    print("                     LANBOX SERVER                     ")
    print("      Local Area Network Communication Platform        ")
    print("=" * 60)
    print(f"[*] Local Host IP (LAN):    {lan_ip}")
    print(f"[*] Bound Host:             {args.host}")
    print(f"[*] Listening Port:          {args.port}")
    print(f"[*] Database File:           {args.db}")
    print("-" * 60)
    print("[*] Give other computers on your Wi-Fi/LAN this IP address:")
    print(f"    --> {lan_ip} : {args.port}")
    print("=" * 60)
    print("[*] Press Ctrl+C at any time to shut down the server.\n")

    server = LANBoxServer(host=args.host, port=args.port, db_path=args.db)

    def handle_sigint(sig, frame):
        print("\n[!] Ctrl+C received. Shutting down server gracefully...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)
    try:
        signal.signal(signal.SIGTERM, handle_sigint)
    except Exception:
        pass

    try:
        server.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        server.stop()

if __name__ == "__main__":
    main()


"""
UDP Broadcast Discovery Service for LANBOX Server.
Responds to client discovery broadcasts so clients can auto-detect the server on the LAN.
"""
import socket
import threading
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import PORT_UDP_DISCOVERY, PORT_TCP_MAIN, get_local_lan_ip

class DiscoveryService:
    def __init__(self, host: str = "0.0.0.0", port: int = PORT_UDP_DISCOVERY, tcp_port: int = PORT_TCP_MAIN, server_name: str = "LANBOX Central Server"):
        self.host = host
        self.port = port
        self.tcp_port = tcp_port
        self.server_name = server_name
        self.sock = None
        self.is_running = False
        self.thread = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.sock.bind((self.host, self.port))
        except Exception as e:
            print(f"[!] Discovery service could not bind to UDP port {self.port}: {e}")
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print(f"[+] UDP Discovery Service active on UDP port {self.port}")

    def _listen_loop(self):
        lan_ip = get_local_lan_ip()
        while self.is_running and self.sock:
            try:
                data, addr = self.sock.recvfrom(2048)
                if not data:
                    continue
                try:
                    msg = json.loads(data.decode('utf-8'))
                except Exception:
                    continue

                if msg.get("action") == "LANBOX_DISCOVER":
                    response = {
                        "action": "LANBOX_OFFER",
                        "server_name": self.server_name,
                        "server_ip": lan_ip,
                        "tcp_port": self.tcp_port
                    }
                    resp_bytes = json.dumps(response).encode('utf-8')
                    self.sock.sendto(resp_bytes, addr)
            except Exception:
                break

    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

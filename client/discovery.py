"""
LAN Auto-Discovery Client for LANBOX.
Broadcasts a discovery query over UDP to automatically find any running LANBOX servers on the local subnet.
"""
import socket
import json
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import PORT_UDP_DISCOVERY, DEFAULT_BROADCAST_IP

class LANDiscoveryClient:
    @staticmethod
    def discover_servers(timeout: float = 1.5) -> list[dict]:
        """
        Broadcasts a discovery query and listens for responses.
        Returns a list of discovered server info dictionaries:
        [{'server_name': '...', 'server_ip': '192.168.1.15', 'tcp_port': 5050}, ...]
        """
        servers = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        query = json.dumps({"action": "LANBOX_DISCOVER"}).encode('utf-8')

        try:
            sock.sendto(query, (DEFAULT_BROADCAST_IP, PORT_UDP_DISCOVERY))
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(2048)
                    resp = json.loads(data.decode('utf-8'))
                    if resp.get("action") == "LANBOX_OFFER":
                        server_info = {
                            "server_name": resp.get("server_name", "LANBOX Server"),
                            "server_ip": resp.get("server_ip", addr[0]),
                            "tcp_port": resp.get("tcp_port", 5050)
                        }
                        if server_info not in servers:
                            servers.append(server_info)
                except socket.timeout:
                    break
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            sock.close()

        return servers

"""
UDP Voice & Video Relay Server for LANBOX.
Routes real-time audio (PCM/Opus), video, and screen sharing packets with minimal latency across LAN clients.
"""
import socket
import threading
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import PORT_UDP_VOICE_VIDEO

class VoiceVideoRelay:
    def __init__(self, host: str = "0.0.0.0", port: int = PORT_UDP_VOICE_VIDEO):
        self.host = host
        self.port = port
        self.sock = None
        self.is_running = False
        self.thread = None

        # Maps username -> (client_ip, client_udp_port)
        self.endpoints = {}
        self.lock = threading.Lock()

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
        except Exception:
            pass

        try:
            self.sock.bind((self.host, self.port))
            self.is_running = True
            self.thread = threading.Thread(target=self._relay_loop, daemon=True)
            self.thread.start()
            print(f"[+] UDP Media Relay (Voice/Video/Screen) active on port {self.port}")
        except Exception as e:
            print(f"[!] Media Relay failed to bind to UDP port {self.port}: {e}")

    def _relay_loop(self):
        while self.is_running and self.sock:
            try:
                data, addr = self.sock.recvfrom(65535)
                if not data or len(data) < 4:
                    continue

                # Header Format:
                # [1 byte packet_type] (0x01=REGISTER_UDP, 0x02=AUDIO, 0x03=VIDEO, 0x04=SCREEN)
                # [1 byte target_len]
                # [target_username bytes]
                # [1 byte sender_len]
                # [sender_username bytes]
                # [remaining payload]
                
                pkt_type = data[0]
                target_len = data[1]
                offset = 2
                
                target_user = data[offset:offset + target_len].decode('utf-8', errors='ignore') if target_len > 0 else ""
                offset += target_len

                if offset >= len(data):
                    continue

                sender_len = data[offset]
                offset += 1

                if offset + sender_len > len(data):
                    continue

                sender_user = data[offset:offset + sender_len].decode('utf-8', errors='ignore') if sender_len > 0 else ""
                offset += sender_len

                # Automatically update active sender endpoint
                if sender_user:
                    with self.lock:
                        self.endpoints[sender_user] = addr

                # If this was just a registration packet (0x01), we're done
                if pkt_type == 0x01:
                    continue

                # Route media packet
                if target_user in ('__public__', 'public', ''):
                    # Broadcast to all other registered clients
                    with self.lock:
                        targets = [ep for user, ep in self.endpoints.items() if user != sender_user]
                    for ep in targets:
                        try:
                            self.sock.sendto(data, ep)
                        except Exception:
                            pass
                else:
                    # 1-to-1 direct routing
                    with self.lock:
                        target_addr = self.endpoints.get(target_user)

                    if target_addr:
                        try:
                            self.sock.sendto(data, target_addr)
                        except Exception:
                            pass

            except Exception:
                if not self.is_running:
                    break

    def unregister_user(self, username: str):
        with self.lock:
            if username in self.endpoints:
                del self.endpoints[username]

    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

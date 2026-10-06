"""
Screen Sharing Module for LANBOX.
Captures desktop screen using MSS, compresses as high-definition JPEG, and streams over UDP to peers.
"""
import socket
import threading
import time
import sys
import os
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from common.config import PORT_UDP_VOICE_VIDEO

try:
    import mss
    HAS_MSS = True
except Exception:
    HAS_MSS = False

# Quality Presets: (target_width, base_jpeg_quality)
QUALITY_PROFILES = {
    "1080p": (1600, 75),
    "720p": (1280, 68),
    "fast": (960, 50)
}

class ScreenShareClient:
    def __init__(self, server_host: str, server_udp_port: int = PORT_UDP_VOICE_VIDEO):
        self.server_host = server_host
        self.server_port = server_udp_port
        self.sock = None
        self.is_sharing = False
        self.current_partner = None
        self.current_user = None
        self.quality_preset = "1080p"

        self.share_thread = None
        self.on_remote_screen_frame = None  # fn(frame_bgr)

    def start_sharing(self, username: str, partner_username: str, udp_socket: socket.socket, quality_preset: str = "1080p"):
        self.current_user = username
        self.current_partner = partner_username
        self.sock = udp_socket
        self.quality_preset = quality_preset
        self.is_sharing = True

        self.share_thread = threading.Thread(target=self._capture_screen_loop, daemon=True)
        self.share_thread.start()
        print(f"[+] High-Def Screen sharing active with {partner_username} (Preset: {quality_preset})")

    def _capture_screen_loop(self):
        if not HAS_MSS:
            print("[!] MSS library not available for screen sharing.")
            return

        target_w, base_quality = QUALITY_PROFILES.get(self.quality_preset, (1600, 75))

        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            while self.is_sharing:
                try:
                    sct_img = sct.grab(monitor)
                    frame = np.array(sct_img)
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                    h, w = frame_bgr.shape[:2]
                    # Resize to crisp width maintaining exact aspect ratio
                    if w > target_w:
                        target_h = int(h * (target_w / w))
                        resized = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
                    else:
                        resized = frame_bgr

                    # Iterative adaptive compression to maximize visual fidelity while staying safely under UDP MTU (58 KB)
                    cur_q = base_quality
                    jpeg_bytes = None
                    while cur_q >= 30:
                        _, buffer = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), cur_q])
                        encoded = buffer.tobytes()
                        if len(encoded) <= 58000:
                            jpeg_bytes = encoded
                            break
                        cur_q -= 8

                    # Secondary fallback if still oversized (e.g. extremely noisy screen)
                    if jpeg_bytes is None:
                        fallback_w = int(target_w * 0.8)
                        fallback_h = int(resized.shape[0] * 0.8)
                        smaller = cv2.resize(resized, (fallback_w, fallback_h), interpolation=cv2.INTER_AREA)
                        _, buffer = cv2.imencode('.jpg', smaller, [int(cv2.IMWRITE_JPEG_QUALITY), 40])
                        jpeg_bytes = buffer.tobytes()

                    if self.sock and self.current_partner and len(jpeg_bytes) < 62000:
                        target_bytes = self.current_partner.encode('utf-8')
                        sender_bytes = self.current_user.encode('utf-8')

                        # Packet: [0x04=SCREEN][target_len][target][sender_len][sender][jpeg_bytes]
                        packet = bytearray([0x04, len(target_bytes)]) + target_bytes + bytearray([len(sender_bytes)]) + sender_bytes + jpeg_bytes
                        self.sock.sendto(packet, (self.server_host, self.server_port))

                    time.sleep(0.045)  # ~22 FPS smooth high-res feed
                except Exception as e:
                    time.sleep(0.1)

    def process_incoming_screen_frame(self, jpeg_bytes: bytes):
        if not self.on_remote_screen_frame:
            return
        try:
            np_arr = np.frombuffer(jpeg_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is not None:
                self.on_remote_screen_frame(frame)
        except Exception:
            pass

    def stop_sharing(self):
        self.is_sharing = False
        self.current_partner = None
        print("[*] Screen sharing stopped.")

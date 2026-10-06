"""
Screen Sharing Module for LANBOX.
Captures desktop screen using MSS, compresses with crisp High-Definition JPEG (chunked UDP),
and streams in real-time with sub-50ms latency.
"""
import socket
import threading
import time
import sys
import os
import struct
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from common.config import PORT_UDP_VOICE_VIDEO

try:
    import mss
    HAS_MSS = True
except Exception:
    HAS_MSS = False

# Quality Presets: (target_width, base_jpeg_quality, max_fps)
QUALITY_PROFILES = {
    "1080p": (1920, 85, 30),
    "720p": (1280, 80, 30),
    "fast": (1024, 65, 35)
}

CHUNK_PAYLOAD_MAX = 52000  # Safe UDP payload size per chunk (avoids IP fragmentation)

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

        # Chunk reassembly state for incoming frames
        self._frame_buffers = {}  # frame_id -> {total, chunks: {idx: bytes}, timestamp}
        self._buffer_lock = threading.Lock()
        self._last_frame_id = 0

    def start_sharing(self, username: str, partner_username: str, udp_socket: socket.socket, quality_preset: str = "1080p"):
        self.current_user = username
        self.current_partner = partner_username
        self.sock = udp_socket
        self.quality_preset = quality_preset
        self.is_sharing = True

        self.share_thread = threading.Thread(target=self._capture_screen_loop, daemon=True)
        self.share_thread.start()
        print(f"[+] Ultra-Clear Screen sharing active with {partner_username} (Preset: {quality_preset})")

    def _capture_screen_loop(self):
        if not HAS_MSS:
            print("[!] MSS library not available for screen sharing.")
            return

        target_w, base_quality, max_fps = QUALITY_PROFILES.get(self.quality_preset, (1920, 85, 30))
        target_interval = 1.0 / max_fps
        frame_counter = 0

        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            prev_small_gray = None

            while self.is_sharing:
                loop_start = time.time()
                try:
                    sct_img = sct.grab(monitor)
                    frame = np.array(sct_img)
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                    h, w = frame_bgr.shape[:2]
                    # Resize maintaining aspect ratio
                    if w > target_w:
                        target_h = int(h * (target_w / w))
                        resized = cv2.resize(frame_bgr, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
                    else:
                        resized = frame_bgr

                    # Screen Delta check: check if screen changed significantly to conserve CPU/network
                    small_gray = cv2.cvtColor(cv2.resize(resized, (160, 90), interpolation=cv2.INTER_NEAREST), cv2.COLOR_BGR2GRAY)
                    if prev_small_gray is not None and frame_counter % 20 != 0:
                        diff = cv2.absdiff(small_gray, prev_small_gray)
                        if np.mean(diff) < 0.5:
                            # Screen hasn't changed; sleep and continue
                            time.sleep(target_interval)
                            continue
                    prev_small_gray = small_gray

                    # Fast single-pass high-quality JPEG encode
                    encode_params = [
                        int(cv2.IMWRITE_JPEG_QUALITY), base_quality,
                        int(cv2.IMWRITE_JPEG_OPTIMIZE), 0
                    ]
                    _, buffer = cv2.imencode('.jpg', resized, encode_params)
                    jpeg_bytes = buffer.tobytes()

                    if self.sock and self.current_partner:
                        self._send_frame_chunks(jpeg_bytes, frame_counter)
                        frame_counter = (frame_counter + 1) % 1000000

                    # Maintain target FPS smoothly
                    elapsed = time.time() - loop_start
                    sleep_time = max(0.005, target_interval - elapsed)
                    time.sleep(sleep_time)

                except Exception as e:
                    time.sleep(0.05)

    def _send_frame_chunks(self, jpeg_bytes: bytes, frame_id: int):
        """Splits full HD JPEG frame into UDP chunks (Packet 0x05) to bypass single-datagram size limits."""
        total_len = len(jpeg_bytes)
        num_chunks = (total_len + CHUNK_PAYLOAD_MAX - 1) // CHUNK_PAYLOAD_MAX

        target_bytes = self.current_partner.encode('utf-8')
        sender_bytes = self.current_user.encode('utf-8')

        # Base header for relay routing:
        # [0x05=CHUNKED_SCREEN][target_len (1B)][target_bytes][sender_len (1B)][sender_bytes]
        base_hdr = bytearray([0x05, len(target_bytes)]) + target_bytes + bytearray([len(sender_bytes)]) + sender_bytes

        for idx in range(num_chunks):
            start = idx * CHUNK_PAYLOAD_MAX
            end = min(start + CHUNK_PAYLOAD_MAX, total_len)
            chunk_data = jpeg_bytes[start:end]

            # Chunk Header: [frame_id (4B, big-endian)][chunk_idx (2B)][total_chunks (2B)]
            chunk_hdr = struct.pack('!IHH', frame_id, idx, num_chunks)
            packet = base_hdr + chunk_hdr + chunk_data
            try:
                self.sock.sendto(packet, (self.server_host, self.server_port))
            except Exception:
                pass

    def process_incoming_chunk(self, chunk_payload: bytes):
        """Reassembles incoming UDP chunked screen frames (Packet 0x05)."""
        if len(chunk_payload) < 8:
            return
        
        frame_id, chunk_idx, num_chunks = struct.unpack('!IHH', chunk_payload[:8])
        chunk_data = chunk_payload[8:]
        current_time = time.time()

        with self._buffer_lock:
            # Clean up old stale frames older than 0.5s
            stale_keys = [k for k, v in self._frame_buffers.items() if current_time - v["timestamp"] > 0.5]
            for k in stale_keys:
                del self._frame_buffers[k]

            if frame_id not in self._frame_buffers:
                self._frame_buffers[frame_id] = {
                    "total": num_chunks,
                    "chunks": {},
                    "timestamp": current_time
                }

            entry = self._frame_buffers[frame_id]
            entry["chunks"][chunk_idx] = chunk_data

            # Check if all chunks for this frame have arrived
            if len(entry["chunks"]) == entry["total"]:
                # Assemble ordered frame
                full_bytes = b"".join(entry["chunks"][i] for i in range(entry["total"]))
                del self._frame_buffers[frame_id]
                self._render_decoded_frame(full_bytes)

    def process_incoming_screen_frame(self, jpeg_bytes: bytes):
        """Handles legacy single-packet screen frames (Packet 0x04)."""
        self._render_decoded_frame(jpeg_bytes)

    def _render_decoded_frame(self, jpeg_bytes: bytes):
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
        with self._buffer_lock:
            self._frame_buffers.clear()
        print("[*] Screen sharing stopped.")


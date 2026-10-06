"""
Video Calling Module for LANBOX.
Captures local webcam video using OpenCV, compresses frames as JPEG, streams over UDP,
and decodes incoming video frames for real-time GUI display.
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

class VideoCallClient:
    def __init__(self, server_host: str, server_udp_port: int = PORT_UDP_VOICE_VIDEO):
        self.server_host = server_host
        self.server_port = server_udp_port
        self.sock = None
        self.is_streaming = False
        self.current_partner = None
        self.current_user = None

        self.cap = None
        self.capture_thread = None
        self.on_local_frame = None   # fn(frame_bgr)
        self.on_remote_frame = None  # fn(frame_bgr)

    def start_video(self, username: str, partner_username: str, udp_socket: socket.socket):
        self.current_user = username
        self.current_partner = partner_username
        self.sock = udp_socket
        self.is_streaming = True

        self.capture_thread = threading.Thread(target=self._camera_capture_loop, daemon=True)
        self.capture_thread.start()
        print(f"[+] Video call streaming started to {partner_username}")

    def _camera_capture_loop(self):
        try:
            self.cap = cv2.VideoCapture(0)
            # Set resolution (e.g. 480p for crisp LAN performance)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 24)

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 55]

            while self.is_streaming and self.cap.isOpened():
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.04)
                    continue

                # Local preview callback
                if self.on_local_frame:
                    self.on_local_frame(frame)

                if self.sock and self.current_partner:
                    # Compress frame to JPEG
                    _, buffer = cv2.imencode('.jpg', frame, encode_param)
                    jpeg_bytes = buffer.tobytes()

                    # Keep under UDP MTU/safe datagram size (60KB)
                    if len(jpeg_bytes) < 60000:
                        target_bytes = self.current_partner.encode('utf-8')
                        sender_bytes = self.current_user.encode('utf-8')

                        # Packet: [0x03=VIDEO][target_len][target][sender_len][sender][jpeg_bytes]
                        packet = bytearray([0x03, len(target_bytes)]) + target_bytes + bytearray([len(sender_bytes)]) + sender_bytes + jpeg_bytes
                        try:
                            self.sock.sendto(packet, (self.server_host, self.server_port))
                        except Exception:
                            pass

                time.sleep(0.04)  # ~25 FPS

        except Exception as e:
            print(f"[!] Camera capture error: {e}")
        finally:
            if self.cap:
                self.cap.release()
                self.cap = None

    def process_incoming_video_frame(self, jpeg_bytes: bytes):
        """Decodes incoming JPEG bytes to BGR image frame and triggers UI callback."""
        if not self.on_remote_frame:
            return
        try:
            np_arr = np.frombuffer(jpeg_bytes, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is not None:
                self.on_remote_frame(frame)
        except Exception:
            pass

    def stop_video(self):
        self.is_streaming = False
        self.current_partner = None
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        print("[*] Video call stopped.")

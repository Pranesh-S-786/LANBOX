"""
Voice Calling Module for LANBOX.
Streams real-time low-latency microphone audio over UDP using sounddevice and NumPy.
"""
import socket
import threading
import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from common.config import PORT_UDP_VOICE_VIDEO

try:
    import sounddevice as sd
    HAS_AUDIO_DEVICE = True
except Exception:
    HAS_AUDIO_DEVICE = False

SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_SIZE = 1024  # 1024 samples per frame (~64ms)

class VoiceCallClient:
    def __init__(self, server_host: str, server_udp_port: int = PORT_UDP_VOICE_VIDEO):
        self.server_host = server_host
        self.server_port = server_udp_port
        self.sock = None
        self.is_calling = False
        self.current_partner = None
        self.current_user = None

        self.input_stream = None
        self.output_stream = None
        self.audio_queue = []
        self.lock = threading.Lock()

    def start_call(self, username: str, partner_username: str, udp_socket: socket.socket):
        """Starts capturing microphone audio and sending UDP packets to partner."""
        self.current_user = username
        self.current_partner = partner_username
        self.sock = udp_socket
        self.is_calling = True

        if not HAS_AUDIO_DEVICE:
            print("[!] Audio hardware not accessible or sounddevice unavailable.")
            return

        try:
            # Setup output speaker stream
            self.output_stream = sd.OutputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                blocksize=BLOCK_SIZE
            )
            self.output_stream.start()

            # Setup input mic stream
            self.input_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                blocksize=BLOCK_SIZE,
                callback=self._mic_callback
            )
            self.input_stream.start()
            print(f"[+] Voice call active with {partner_username}")
        except Exception as e:
            print(f"[!] Audio stream error: {e}")

    def _mic_callback(self, indata, frames, time_info, status):
        """Callback from sounddevice when a chunk of audio is recorded."""
        if not self.is_calling or not self.sock or not self.current_partner:
            return

        # Packet: [0x02=AUDIO][target_len][target][sender_len][sender][audio_bytes]
        target_bytes = self.current_partner.encode('utf-8')
        sender_bytes = self.current_user.encode('utf-8')
        payload = indata.tobytes()

        packet = bytearray([0x02, len(target_bytes)]) + target_bytes + bytearray([len(sender_bytes)]) + sender_bytes + payload
        try:
            self.sock.sendto(packet, (self.server_host, self.server_port))
        except Exception:
            pass

    def play_incoming_audio(self, raw_audio_bytes: bytes):
        """Plays received raw PCM audio bytes to speakers."""
        if self.output_stream and self.is_calling:
            try:
                audio_array = np.frombuffer(raw_audio_bytes, dtype=np.int16)
                self.output_stream.write(audio_array)
            except Exception:
                pass

    def stop_call(self):
        """Stops audio capture and playback."""
        self.is_calling = False
        self.current_partner = None

        if self.input_stream:
            try:
                self.input_stream.stop()
                self.input_stream.close()
            except Exception:
                pass
            self.input_stream = None

        if self.output_stream:
            try:
                self.output_stream.stop()
                self.output_stream.close()
            except Exception:
                pass
            self.output_stream = None
        print("[*] Voice call stopped.")

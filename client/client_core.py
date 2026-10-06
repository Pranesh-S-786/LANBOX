"""
Central Client Networking Core for LANBOX.
Coordinates TCP signaling, UDP media streaming, and modular collaboration subsystems.
"""
import socket
import threading
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import (
    PORT_TCP_MAIN, PORT_UDP_VOICE_VIDEO, PORT_TCP_FILE_TRANSFER,
    TYPE_REGISTER, TYPE_LOGIN, TYPE_AUTH_RESPONSE,
    TYPE_USER_LIST, TYPE_DIRECT_MSG, TYPE_BROADCAST_MSG,
    TYPE_MSG_HISTORY, TYPE_MSG_HISTORY_RESPONSE,
    TYPE_ANNOUNCEMENT_POST, TYPE_ANNOUNCEMENT_BROADCAST, TYPE_ANNOUNCEMENT_LIST, TYPE_ANNOUNCEMENT_LIST_RESPONSE,
    TYPE_FILE_OFFER, TYPE_FILE_RESPONSE,
    TYPE_CALL_OFFER, TYPE_CALL_ANSWER, TYPE_CALL_HANGUP, TYPE_CALL_BUSY,
    TYPE_SCREEN_SHARE_START, TYPE_SCREEN_SHARE_STOP,
    TYPE_REMOTE_REQUEST, TYPE_REMOTE_RESPONSE, TYPE_REMOTE_INPUT_EVENT, TYPE_REMOTE_STOP,
    TYPE_PING, TYPE_PONG, TYPE_SERVER_STATS
)
from common.protocol import send_json, recv_json
from client.modules.file_transfer import FileTransferClient
from client.modules.voice_call import VoiceCallClient
from client.modules.video_call import VideoCallClient
from client.modules.screen_share import ScreenShareClient
from client.modules.remote_assist import RemoteAssistanceClient

class LANBoxClient:
    def __init__(self):
        self.sock = None
        self.udp_sock = None
        self.is_connected = False
        self.current_user = None
        self.server_host = None
        self.server_port = None

        self.recv_thread = None
        self.udp_recv_thread = None
        self.lock = threading.Lock()

        # Modular Subsystems
        self.file_transfer = None
        self.voice_call = None
        self.video_call = None
        self.screen_share = None
        self.remote_assist = None

        # GUI Callbacks
        self.on_message_received = None       # fn(msg_dict)
        self.on_user_list_updated = None      # fn(users_list)
        self.on_history_received = None       # fn(target, history_list)
        self.on_announcement_received = None  # fn(announcement_dict)
        self.on_announcements_list = None     # fn(list_of_announcements)
        self.on_file_offered = None           # fn(offer_dict)
        self.on_call_incoming = None          # fn(call_dict)
        self.on_call_response = None          # fn(resp_dict)
        self.on_call_ended = None             # fn(hangup_dict)
        self.on_remote_request = None         # fn(requester_username)
        self.on_remote_response = None        # fn(host_user, accepted)
        self.on_remote_stopped = None         # fn()
        self.on_server_stats = None           # fn(stats_dict)
        self.on_pong = None                   # fn(latency_ms)
        self.on_disconnected = None           # fn(reason_str)

    def connect(self, host: str, port: int = PORT_TCP_MAIN) -> tuple[bool, str]:
        try:
            self.disconnect()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((host, port))
            self.sock.settimeout(None)
            self.server_host = host
            self.server_port = port
            self.is_connected = True

            # Initialize Submodules
            self.file_transfer = FileTransferClient(host, PORT_TCP_FILE_TRANSFER)
            self.voice_call = VoiceCallClient(host, PORT_UDP_VOICE_VIDEO)
            self.video_call = VideoCallClient(host, PORT_UDP_VOICE_VIDEO)
            self.screen_share = ScreenShareClient(host, PORT_UDP_VOICE_VIDEO)
            self.remote_assist = RemoteAssistanceClient(self)

            return True, "Connected to server successfully."
        except Exception as e:
            self.is_connected = False
            return False, f"Failed to connect: {str(e)}"

    def register(self, username: str, password: str) -> tuple[bool, str]:
        if not self.is_connected or not self.sock:
            return False, "Not connected to server."

        req = {"type": TYPE_REGISTER, "username": username, "password": password}
        with self.lock:
            if not send_json(self.sock, req):
                return False, "Connection lost."
            resp = recv_json(self.sock)

        if not resp or resp.get("type") != TYPE_AUTH_RESPONSE:
            return False, "Invalid response from server."

        return resp.get("success", False), resp.get("message", "Unknown response.")

    def login(self, username: str, password: str) -> tuple[bool, str]:
        if not self.is_connected or not self.sock:
            return False, "Not connected to server."

        req = {"type": TYPE_LOGIN, "username": username, "password": password}
        with self.lock:
            if not send_json(self.sock, req):
                return False, "Connection lost."
            resp = recv_json(self.sock)

        if not resp or resp.get("type") != TYPE_AUTH_RESPONSE:
            return False, "Invalid response from server."

        success = resp.get("success", False)
        message = resp.get("message", "Unknown response.")

        if success:
            self.current_user = username
            self._init_udp_media_socket()
            
            # Start background receiving threads
            self.recv_thread = threading.Thread(target=self._tcp_receive_loop, daemon=True)
            self.recv_thread.start()

        return success, message

    def _init_udp_media_socket(self):
        """Binds a local UDP socket and registers with server media relay."""
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 8 * 1024 * 1024)
        except Exception:
            pass

        # Send registration datagram to media relay: [0x01=REGISTER][0=target_len][sender_len] + user_bytes
        user_bytes = self.current_user.encode('utf-8')
        reg_packet = bytearray([0x01, 0, len(user_bytes)]) + user_bytes
        try:
            self.udp_sock.sendto(reg_packet, (self.server_host, PORT_UDP_VOICE_VIDEO))
        except Exception:
            pass

        self.udp_recv_thread = threading.Thread(target=self._udp_media_receive_loop, daemon=True)
        self.udp_recv_thread.start()

    def _tcp_receive_loop(self):
        while self.is_connected and self.sock:
            try:
                msg = recv_json(self.sock)
                if not msg:
                    break

                msg_type = msg.get("type")

                # Messaging
                if msg_type in (TYPE_DIRECT_MSG, TYPE_BROADCAST_MSG):
                    if self.on_message_received:
                        self.on_message_received(msg)

                elif msg_type == TYPE_USER_LIST:
                    if self.on_user_list_updated:
                        self.on_user_list_updated(msg.get("users", []))

                elif msg_type == TYPE_MSG_HISTORY_RESPONSE:
                    if self.on_history_received:
                        self.on_history_received(msg.get("target"), msg.get("history", []))

                # Announcements
                elif msg_type == TYPE_ANNOUNCEMENT_BROADCAST:
                    if self.on_announcement_received:
                        self.on_announcement_received(msg.get("announcement"))

                elif msg_type == TYPE_ANNOUNCEMENT_LIST_RESPONSE:
                    if self.on_announcements_list:
                        self.on_announcements_list(msg.get("announcements", []))

                # File sharing
                elif msg_type == TYPE_FILE_OFFER:
                    if self.on_file_offered:
                        self.on_file_offered(msg)

                # Calling
                elif msg_type == TYPE_CALL_OFFER:
                    if self.on_call_incoming:
                        self.on_call_incoming(msg)

                elif msg_type in (TYPE_CALL_ANSWER, TYPE_CALL_BUSY):
                    if self.on_call_response:
                        self.on_call_response(msg)

                elif msg_type == TYPE_CALL_HANGUP:
                    if self.on_call_ended:
                        self.on_call_ended(msg)

                # Remote Assistance
                elif msg_type == TYPE_REMOTE_REQUEST:
                    if self.on_remote_request:
                        self.on_remote_request(msg.get("requester"))

                elif msg_type == TYPE_REMOTE_RESPONSE:
                    if self.on_remote_response:
                        self.on_remote_response(msg.get("host_user"), msg.get("accepted", False))

                elif msg_type == TYPE_REMOTE_INPUT_EVENT:
                    if self.remote_assist:
                        self.remote_assist.handle_incoming_input_event(msg.get("event", {}))

                elif msg_type == TYPE_REMOTE_STOP:
                    if self.remote_assist:
                        self.remote_assist.stop_session()
                    if self.on_remote_stopped:
                        self.on_remote_stopped()

                # Dashboard & Ping
                elif msg_type == TYPE_PONG:
                    sent_time = msg.get("client_time", 0)
                    rtt_ms = int((time.time() - sent_time) * 1000)
                    if self.on_pong:
                        self.on_pong(rtt_ms)

                elif msg_type == TYPE_SERVER_STATS:
                    if self.on_server_stats:
                        self.on_server_stats(msg)

            except Exception:
                break

        was_connected = self.is_connected
        self.is_connected = False
        if was_connected and self.on_disconnected:
            self.on_disconnected("Disconnected from LAN server.")

    def _udp_media_receive_loop(self):
        """Listens for audio, video, and screen sharing datagrams from UDP relay."""
        while self.is_connected and self.udp_sock:
            try:
                data, addr = self.udp_sock.recvfrom(65535)
                if not data or len(data) < 4:
                    continue

                pkt_type = data[0]
                target_len = data[1]
                offset = 2 + target_len
                if offset >= len(data):
                    continue
                sender_len = data[offset]
                offset += 1 + sender_len
                payload = data[offset:]

                if pkt_type == 0x02:  # Audio
                    if self.voice_call:
                        self.voice_call.play_incoming_audio(payload)

                elif pkt_type == 0x03:  # Video
                    if self.video_call:
                        self.video_call.process_incoming_video_frame(payload)

                elif pkt_type == 0x04:  # Legacy Screen Share
                    if self.screen_share:
                        self.screen_share.process_incoming_screen_frame(payload)

                elif pkt_type == 0x05:  # Chunked Ultra-HD Screen Share
                    if self.screen_share:
                        self.screen_share.process_incoming_chunk(payload)

            except Exception:
                if not self.is_connected:
                    break

    def send_raw(self, data: dict) -> bool:
        if not self.is_connected or not self.sock:
            return False
        with self.lock:
            return send_json(self.sock, data)

    def send_direct_message(self, recipient: str, text: str) -> bool:
        return self.send_raw({"type": TYPE_DIRECT_MSG, "recipient": recipient, "content": text})

    def send_broadcast_message(self, text: str) -> bool:
        return self.send_raw({"type": TYPE_BROADCAST_MSG, "content": text})

    def post_announcement(self, title: str, content: str, priority: str = "normal") -> bool:
        return self.send_raw({
            "type": TYPE_ANNOUNCEMENT_POST,
            "title": title,
            "content": content,
            "priority": priority
        })

    def request_announcements(self):
        self.send_raw({"type": TYPE_ANNOUNCEMENT_LIST})

    def offer_file(self, recipient: str, file_id: str, filename: str, filesize: int) -> bool:
        return self.send_raw({
            "type": TYPE_FILE_OFFER,
            "recipient": recipient,
            "file_id": file_id,
            "filename": filename,
            "file_size": filesize
        })

    def start_call(self, target_user: str, call_type: str = "audio") -> bool:
        return self.send_raw({
            "type": TYPE_CALL_OFFER,
            "target": target_user,
            "call_type": call_type,
            "caller": self.current_user
        })

    def answer_call(self, caller: str, accept: bool, call_type: str = "audio") -> bool:
        return self.send_raw({
            "type": TYPE_CALL_ANSWER,
            "target": caller,
            "accepted": accept,
            "call_type": call_type,
            "responder": self.current_user
        })

    def hangup_call(self, target_user: str):
        if self.voice_call:
            self.voice_call.stop_call()
        if self.video_call:
            self.video_call.stop_video()
        self.send_raw({
            "type": TYPE_CALL_HANGUP,
            "target": target_user,
            "sender": self.current_user
        })

    def request_remote_assistance(self, target_user: str):
        self.send_raw({"type": TYPE_REMOTE_REQUEST, "target": target_user})

    def respond_remote_assistance(self, requester: str, accept: bool):
        self.send_raw({"type": TYPE_REMOTE_RESPONSE, "requester": requester, "accepted": accept})

    def request_server_stats(self):
        self.send_raw({"type": TYPE_SERVER_STATS})

    def send_ping(self):
        self.send_raw({"type": TYPE_PING, "timestamp": time.time()})

    def request_history(self, target: str | None):
        self.send_raw({"type": TYPE_MSG_HISTORY, "target": target})

    def refresh_user_list(self):
        self.send_raw({"type": TYPE_USER_LIST})

    def disconnect(self):
        self.is_connected = False
        self.current_user = None

        if self.voice_call:
            self.voice_call.stop_call()
        if self.video_call:
            self.video_call.stop_video()
        if self.screen_share:
            self.screen_share.stop_sharing()
        if self.remote_assist:
            self.remote_assist.stop_session()

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass
            self.udp_sock = None

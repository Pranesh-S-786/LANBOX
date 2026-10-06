"""
Central TCP Server Core for LANBOX.
Orchestrates messaging, user presence, calling signaling, file offers, announcements,
and network metrics for all connected LAN clients.
"""
import socket
import threading
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.config import (
    DEFAULT_SERVER_HOST, PORT_TCP_MAIN,
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
from server.database import DatabaseManager
from server.discovery_service import DiscoveryService
from server.file_server import FileTransferServer
from server.voice_video_relay import VoiceVideoRelay
from server.remote_relay import RemoteAssistanceManager

class LANBoxServer:
    def __init__(self, host: str = DEFAULT_SERVER_HOST, port: int = PORT_TCP_MAIN, db_path: str = "lanbox.db"):
        self.host = host
        self.port = port
        self.db = DatabaseManager(db_path)
        self.server_socket = None
        self.is_running = False
        self.start_time = time.time()

        # Connected clients management: username -> socket, and socket -> username
        self.clients_by_user = {}  # {username: socket}
        self.users_by_socket = {}  # {socket: username}
        self.client_ips = {}       # {username: ip}
        self.lock = threading.Lock()

        # Subservices
        self.discovery_svc = DiscoveryService()
        self.file_svc = FileTransferServer()
        self.media_relay = VoiceVideoRelay()
        self.remote_mgr = RemoteAssistanceManager(self)

        # Statistics
        self.total_messages_routed = 0
        self.total_files_shared = 0

    def get_client_socket(self, username: str) -> socket.socket | None:
        with self.lock:
            return self.clients_by_user.get(username)

    def start(self):
        """Starts all subservices and the main TCP signaling server."""
        self.discovery_svc.start()
        self.file_svc.start()
        self.media_relay.start()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(25)
        self.is_running = True

        print(f"[+] LANBOX Central Hub listening on {self.host}:{self.port}")

        try:
            while self.is_running:
                client_sock, client_addr = self.server_socket.accept()
                thread = threading.Thread(
                    target=self._client_handler,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                thread.start()
        except OSError:
            pass
        finally:
            self.stop()

    def _client_handler(self, sock: socket.socket, addr: tuple):
        authenticated_user = None
        try:
            # Phase 1: Authentication Loop
            while self.is_running and not authenticated_user:
                msg = recv_json(sock)
                if not msg:
                    return

                msg_type = msg.get("type")

                if msg_type == TYPE_REGISTER:
                    username = msg.get("username", "").strip()
                    password = msg.get("password", "")
                    success, reason = self.db.register_user(username, password)
                    
                    send_json(sock, {
                        "type": TYPE_AUTH_RESPONSE,
                        "success": success,
                        "action": "register",
                        "message": reason,
                        "username": username if success else None
                    })

                elif msg_type == TYPE_LOGIN:
                    username = msg.get("username", "").strip()
                    password = msg.get("password", "")
                    
                    with self.lock:
                        if username in self.clients_by_user:
                            send_json(sock, {
                                "type": TYPE_AUTH_RESPONSE,
                                "success": False,
                                "action": "login",
                                "message": f"User '{username}' is already logged in on this LAN."
                            })
                            continue

                    success, reason = self.db.authenticate_user(username, password)
                    send_json(sock, {
                        "type": TYPE_AUTH_RESPONSE,
                        "success": success,
                        "action": "login",
                        "message": reason,
                        "username": username if success else None
                    })

                    if success:
                        authenticated_user = username
                        with self.lock:
                            self.clients_by_user[username] = sock
                            self.users_by_socket[sock] = username
                            self.client_ips[username] = addr[0]

                        print(f"[+] User '{username}' logged in from {addr[0]}")
                        self.broadcast_user_list()
                        break

            # Phase 2: Active Session Packet Dispatch
            while self.is_running:
                msg = recv_json(sock)
                if not msg:
                    break

                self._process_message(authenticated_user, sock, msg)

        except (ConnectionResetError, BrokenPipeError, socket.error):
            pass
        finally:
            self._cleanup_client(sock, authenticated_user)

    def _process_message(self, sender: str, sock: socket.socket, msg: dict):
        msg_type = msg.get("type")

        # --- Messaging ---
        if msg_type == TYPE_DIRECT_MSG:
            recipient = msg.get("recipient")
            content = msg.get("content", "").strip()
            if not recipient or not content:
                return

            saved_msg = self.db.save_message(sender, recipient, content)
            self.total_messages_routed += 1

            with self.lock:
                target_sock = self.clients_by_user.get(recipient)

            payload = {
                "type": TYPE_DIRECT_MSG,
                "sender": sender,
                "recipient": recipient,
                "content": content,
                "timestamp": saved_msg["timestamp"]
            }

            if target_sock:
                send_json(target_sock, payload)
            send_json(sock, payload)

        elif msg_type == TYPE_BROADCAST_MSG:
            content = msg.get("content", "").strip()
            if not content:
                return

            saved_msg = self.db.save_message(sender, None, content)
            self.total_messages_routed += 1

            payload = {
                "type": TYPE_BROADCAST_MSG,
                "sender": sender,
                "content": content,
                "timestamp": saved_msg["timestamp"]
            }

            with self.lock:
                active_sockets = list(self.clients_by_user.values())

            for s in active_sockets:
                send_json(s, payload)

        elif msg_type == TYPE_MSG_HISTORY:
            target = msg.get("target")
            if target in (None, 'public', '__public__'):
                history = self.db.get_broadcast_history()
            else:
                history = self.db.get_direct_history(sender, target)

            send_json(sock, {
                "type": TYPE_MSG_HISTORY_RESPONSE,
                "target": target,
                "history": history
            })

        # --- Announcements ---
        elif msg_type == TYPE_ANNOUNCEMENT_POST:
            title = msg.get("title", "")
            content = msg.get("content", "")
            priority = msg.get("priority", "normal")
            ann = self.db.create_announcement(sender, title, content, priority)

            broadcast_ann = {
                "type": TYPE_ANNOUNCEMENT_BROADCAST,
                "announcement": ann
            }
            with self.lock:
                active_sockets = list(self.clients_by_user.values())
            for s in active_sockets:
                send_json(s, broadcast_ann)

        elif msg_type == TYPE_ANNOUNCEMENT_LIST:
            anns = self.db.get_announcements()
            send_json(sock, {
                "type": TYPE_ANNOUNCEMENT_LIST_RESPONSE,
                "announcements": anns
            })

        # --- File Offers & Notifications ---
        elif msg_type == TYPE_FILE_OFFER:
            recipient = msg.get("recipient")
            file_id = msg.get("file_id")
            filename = msg.get("filename")
            file_size = msg.get("file_size")

            self.db.record_shared_file(file_id, sender, recipient, filename, file_size)
            self.total_files_shared += 1

            with self.lock:
                target_sock = self.clients_by_user.get(recipient)

            if target_sock:
                send_json(target_sock, {
                    "type": TYPE_FILE_OFFER,
                    "sender": sender,
                    "file_id": file_id,
                    "filename": filename,
                    "file_size": file_size
                })

        # --- Voice & Video Signaling ---
        elif msg_type in (TYPE_CALL_OFFER, TYPE_CALL_ANSWER, TYPE_CALL_HANGUP, TYPE_CALL_BUSY):
            target = msg.get("target")
            with self.lock:
                target_sock = self.clients_by_user.get(target)

            if target_sock:
                send_json(target_sock, msg)
            elif msg_type == TYPE_CALL_OFFER:
                send_json(sock, {"type": TYPE_CALL_BUSY, "target": target, "reason": "User is offline."})

        # --- Screen Share Signaling ---
        elif msg_type in (TYPE_SCREEN_SHARE_START, TYPE_SCREEN_SHARE_STOP):
            target = msg.get("target")
            with self.lock:
                target_sock = self.clients_by_user.get(target) if target else None

            if target_sock:
                send_json(target_sock, msg)
            elif not target:
                # Broadcast screen share notice to lobby
                with self.lock:
                    for s in list(self.clients_by_user.values()):
                        if s != sock:
                            send_json(s, msg)

        # --- Remote Assistance Routing ---
        elif msg_type == TYPE_REMOTE_REQUEST:
            target = msg.get("target")
            self.remote_mgr.handle_request(sender, target)

        elif msg_type == TYPE_REMOTE_RESPONSE:
            requester = msg.get("requester")
            accepted = msg.get("accepted", False)
            self.remote_mgr.handle_response(sender, requester, accepted)

        elif msg_type == TYPE_REMOTE_INPUT_EVENT:
            self.remote_mgr.handle_input_event(sender, msg)

        elif msg_type == TYPE_REMOTE_STOP:
            self.remote_mgr.terminate_session(sender)

        # --- Dashboard & Network Diagnostics ---
        elif msg_type == TYPE_PING:
            send_json(sock, {"type": TYPE_PONG, "client_time": msg.get("timestamp")})

        elif msg_type == TYPE_SERVER_STATS:
            self._send_server_stats_to(sock)

        elif msg_type == TYPE_USER_LIST:
            self._send_user_list_to(sock)

    def _send_server_stats_to(self, sock: socket.socket):
        uptime_sec = int(time.time() - self.start_time)
        with self.lock:
            online_count = len(self.clients_by_user)
            active_users = [
                {"username": u, "ip": self.client_ips.get(u, "Unknown")}
                for u in self.clients_by_user.keys()
            ]

        send_json(sock, {
            "type": TYPE_SERVER_STATS,
            "uptime_seconds": uptime_sec,
            "online_users_count": online_count,
            "active_users": active_users,
            "total_messages": self.total_messages_routed,
            "total_files": self.total_files_shared
        })

    def broadcast_user_list(self):
        with self.lock:
            active_sockets = list(self.clients_by_user.values())
        for s in active_sockets:
            self._send_user_list_to(s)

    def _send_user_list_to(self, sock: socket.socket):
        all_users = self.db.get_all_registered_users()
        with self.lock:
            online_users = set(self.clients_by_user.keys())

        user_status_list = [
            {"username": u, "online": (u in online_users), "ip": self.client_ips.get(u, "")}
            for u in all_users
        ]

        send_json(sock, {
            "type": TYPE_USER_LIST,
            "users": user_status_list
        })

    def _cleanup_client(self, sock: socket.socket, username: str | None):
        with self.lock:
            if username and username in self.clients_by_user:
                del self.clients_by_user[username]
            if sock in self.users_by_socket:
                del self.users_by_socket[sock]
            if username and username in self.client_ips:
                del self.client_ips[username]

        if username:
            self.media_relay.unregister_user(username)
            self.remote_mgr.terminate_session(username)

        try:
            sock.close()
        except OSError:
            pass

        if username:
            print(f"[-] User '{username}' disconnected.")
            self.broadcast_user_list()

    def stop(self):
        self.is_running = False
        self.discovery_svc.stop()
        self.file_svc.stop()
        self.media_relay.stop()

        with self.lock:
            for sock in list(self.users_by_socket.keys()):
                try:
                    sock.close()
                except OSError:
                    pass
            self.clients_by_user.clear()
            self.users_by_socket.clear()

        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
        print("[*] LANBOX Server stopped.")

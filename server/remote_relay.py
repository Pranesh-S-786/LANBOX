"""
Remote Assistance Session & Input Relay for LANBOX Server.
Manages permission-based remote control sessions between client pairs.
"""
import threading
import json
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import (
    TYPE_REMOTE_REQUEST, TYPE_REMOTE_RESPONSE, TYPE_REMOTE_INPUT_EVENT, TYPE_REMOTE_STOP
)
from common.protocol import send_json

class RemoteAssistanceManager:
    def __init__(self, server_core):
        self.server = server_core
        # Active sessions: {target_user: controller_user}
        self.active_sessions = {}
        self.lock = threading.Lock()

    def handle_request(self, requester: str, target: str):
        """Routes a remote assistance request to the target computer with accept/deny prompt."""
        target_sock = self.server.get_client_socket(target)
        if not target_sock:
            return False, "Target user is offline."

        send_json(target_sock, {
            "type": TYPE_REMOTE_REQUEST,
            "requester": requester
        })
        return True, "Request sent to host."

    def handle_response(self, host_user: str, requester: str, accepted: bool):
        """Processes the host's accept or deny response."""
        req_sock = self.server.get_client_socket(requester)
        with self.lock:
            if accepted:
                self.active_sessions[host_user] = requester
            elif host_user in self.active_sessions:
                del self.active_sessions[host_user]

        if req_sock:
            send_json(req_sock, {
                "type": TYPE_REMOTE_RESPONSE,
                "host_user": host_user,
                "accepted": accepted
            })

    def handle_input_event(self, controller: str, event_data: dict):
        """Relays mouse move, click, scroll, and key press events to the host computer."""
        target_user = event_data.get("target")
        with self.lock:
            # Verify that controller is authorized for this host
            if self.active_sessions.get(target_user) != controller:
                return

        target_sock = self.server.get_client_socket(target_user)
        if target_sock:
            send_json(target_sock, {
                "type": TYPE_REMOTE_INPUT_EVENT,
                "controller": controller,
                "event": event_data.get("event")
            })

    def terminate_session(self, user: str):
        """Ends any active remote assistance session involving this user."""
        with self.lock:
            for host, ctrl in list(self.active_sessions.items()):
                if user in (host, ctrl):
                    other = ctrl if user == host else host
                    del self.active_sessions[host]
                    other_sock = self.server.get_client_socket(other)
                    if other_sock:
                        send_json(other_sock, {
                            "type": TYPE_REMOTE_STOP,
                            "initiator": user
                        })

    def is_session_active(self, host: str, controller: str) -> bool:
        with self.lock:
            return self.active_sessions.get(host) == controller

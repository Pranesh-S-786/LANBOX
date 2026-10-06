"""
Remote Assistance Module for LANBOX.
Enables permission-based remote desktop viewing and control using screen streaming and PyAutoGUI input execution.
"""
import threading
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from common.config import TYPE_REMOTE_INPUT_EVENT, TYPE_REMOTE_STOP

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Moving mouse to upper-left corner aborts control
    HAS_PYAUTOGUI = True
except Exception:
    HAS_PYAUTOGUI = False

class RemoteAssistanceClient:
    def __init__(self, client_core):
        self.client = client_core
        self.is_hosting = False
        self.is_controlling = False
        self.current_partner = None

    def start_host_session(self, controller_user: str):
        """Called when local user agrees to give remote assistance to controller_user."""
        self.is_hosting = True
        self.current_partner = controller_user
        # Start streaming desktop to controller
        self.client.screen_share.start_sharing(self.client.current_user, controller_user, self.client.udp_sock)
        print(f"[+] Remote assistance session started. {controller_user} is controlling.")

    def handle_incoming_input_event(self, event_data: dict):
        """Executes mouse/keyboard commands on the local machine sent by the authorized remote controller."""
        if not self.is_hosting or not HAS_PYAUTOGUI:
            return

        try:
            evt_type = event_data.get("type")
            screen_w, screen_h = pyautogui.size()

            if evt_type == "mouse_move":
                rx = event_data.get("rx", 0.0)
                ry = event_data.get("ry", 0.0)
                pyautogui.moveTo(int(rx * screen_w), int(ry * screen_h), _pause=False)

            elif evt_type == "mouse_click":
                rx = event_data.get("rx", 0.0)
                ry = event_data.get("ry", 0.0)
                btn = event_data.get("btn", "left")
                pyautogui.click(int(rx * screen_w), int(ry * screen_h), button=btn, _pause=False)

            elif evt_type == "mouse_double_click":
                rx = event_data.get("rx", 0.0)
                ry = event_data.get("ry", 0.0)
                pyautogui.doubleClick(int(rx * screen_w), int(ry * screen_h), _pause=False)

            elif evt_type == "key_press":
                key = event_data.get("key")
                if key:
                    pyautogui.press(key, _pause=False)

            elif evt_type == "key_write":
                text = event_data.get("text")
                if text:
                    pyautogui.write(text, _pause=False)

        except Exception as e:
            print(f"[!] Input execution error: {e}")

    def send_control_event(self, target_host: str, event_dict: dict):
        """Sends mouse or keyboard action to remote host."""
        if not self.is_controlling:
            return
        
        req = {
            "type": TYPE_REMOTE_INPUT_EVENT,
            "target": target_host,
            "event": event_dict
        }
        self.client.send_raw(req)

    def stop_session(self):
        """Terminates control session and screen stream."""
        if self.is_hosting:
            self.client.screen_share.stop_sharing()
            self.is_hosting = False
        
        if self.is_controlling:
            self.is_controlling = False

        if self.current_partner:
            self.client.send_raw({
                "type": TYPE_REMOTE_STOP
            })
            self.current_partner = None
        print("[*] Remote assistance session closed.")

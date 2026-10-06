"""
Messaging & Channels View Widget for LANBOX.
Supports 1-to-1 direct messaging and public LAN lobby with rich message history.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QLineEdit, QPushButton, QFrame, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class ChatViewWidget(QWidget):
    # Signals for quick actions from chat toolbar
    start_call_requested = pyqtSignal(str, str)         # (target_user, "audio"|"video")
    send_file_requested = pyqtSignal(str)               # (target_user)
    request_remote_requested = pyqtSignal(str)          # (target_user)

    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.current_target = '__public__'
        self.chat_history_cache = {'__public__': []}

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header card
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 6, 12, 6)

        self.title_lbl = QLabel("📢 Public LAN Lobby")
        self.title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.title_lbl.setStyleSheet("color: #f8fafc;")
        h_layout.addWidget(self.title_lbl)

        h_layout.addStretch()

        # Action Buttons for active target
        self.voice_btn = QPushButton("📞 Voice")
        self.voice_btn.setProperty("class", "SecondaryBtn")
        self.voice_btn.clicked.connect(lambda: self._trigger_call("audio"))
        h_layout.addWidget(self.voice_btn)

        self.video_btn = QPushButton("📹 Video")
        self.video_btn.setProperty("class", "SecondaryBtn")
        self.video_btn.clicked.connect(lambda: self._trigger_call("video"))
        h_layout.addWidget(self.video_btn)

        self.file_btn = QPushButton("📁 Send File")
        self.file_btn.setProperty("class", "SecondaryBtn")
        self.file_btn.clicked.connect(self._trigger_file)
        h_layout.addWidget(self.file_btn)

        self.remote_btn = QPushButton("💻 Remote Help")
        self.remote_btn.setProperty("class", "SecondaryBtn")
        self.remote_btn.clicked.connect(self._trigger_remote)
        h_layout.addWidget(self.remote_btn)

        layout.addWidget(header_card)

        # Chat history display browser
        self.chat_display = QTextBrowser()
        self.chat_display.setOpenExternalLinks(True)
        self.chat_display.setStyleSheet("""
            QTextBrowser {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.chat_display, stretch=1)

        # Message Input Area
        input_card = QFrame()
        input_card.setStyleSheet("background-color: #1e293b; border-radius: 8px;")
        input_layout = QHBoxLayout(input_card)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type your message here... (Press Enter to send)")
        self.msg_input.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.msg_input, stretch=1)

        send_btn = QPushButton("Send")
        send_btn.setProperty("class", "PrimaryBtn")
        send_btn.clicked.connect(self._send_message)
        input_layout.addWidget(send_btn)

        layout.addWidget(input_card)

        self._update_action_buttons_visibility()

    def set_target(self, target: str, is_online: bool = True):
        self.current_target = target
        if target == '__public__':
            self.title_lbl.setText("📢 Public LAN Lobby")
        else:
            status_str = "<span style='color:#10b981;'>● Online</span>" if is_online else "<span style='color:#94a3b8;'>○ Offline</span>"
            self.title_lbl.setText(f"💬 Chat with {target} ({status_str})")

        self._update_action_buttons_visibility()

        if target not in self.chat_history_cache:
            self.chat_history_cache[target] = []
            self.client.request_history(target)
        else:
            self._render_conversation(target)

    def _update_action_buttons_visibility(self):
        is_dm = (self.current_target != '__public__')
        self.voice_btn.setVisible(is_dm)
        self.video_btn.setVisible(is_dm)
        self.file_btn.setVisible(is_dm)
        self.remote_btn.setVisible(is_dm)

    def _trigger_call(self, call_type: str):
        if self.current_target != '__public__':
            self.start_call_requested.emit(self.current_target, call_type)

    def _trigger_file(self):
        if self.current_target != '__public__':
            self.send_file_requested.emit(self.current_target)

    def _trigger_remote(self):
        if self.current_target != '__public__':
            self.request_remote_requested.emit(self.current_target)

    def _send_message(self):
        text = self.msg_input.text().strip()
        if not text:
            return
        self.msg_input.clear()

        if self.current_target == '__public__':
            self.client.send_broadcast_message(text)
        else:
            self.client.send_direct_message(self.current_target, text)

    def append_message(self, msg: dict):
        sender = msg.get("sender")
        recipient = msg.get("recipient")

        if msg.get("type") == "BROADCAST_MSG":
            conv_key = '__public__'
        else:
            conv_key = recipient if sender == self.client.current_user else sender

        if conv_key not in self.chat_history_cache:
            self.chat_history_cache[conv_key] = []
        self.chat_history_cache[conv_key].append(msg)

        if self.current_target == conv_key:
            self._append_single_html_message(msg)

    def set_history(self, target: str | None, history: list):
        conv_key = '__public__' if target in (None, 'public', '__public__') else target
        self.chat_history_cache[conv_key] = history
        if self.current_target == conv_key:
            self._render_conversation(conv_key)

    def _render_conversation(self, conv_key: str):
        self.chat_display.clear()
        messages = self.chat_history_cache.get(conv_key, [])
        for msg in messages:
            self._append_single_html_message(msg)

    def _append_single_html_message(self, msg: dict):
        sender = msg.get("sender", "Unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        is_me = (sender == self.client.current_user)

        if is_me:
            header_color = "#38bdf8"
            sender_label = "You"
            bubble_bg = "#1e3a8a"
        else:
            header_color = "#34d399"
            sender_label = sender
            bubble_bg = "#334155"

        # Sanitize HTML
        safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

        html = f"""
        <div style="margin-bottom: 10px;">
            <span style="font-weight: bold; color: {header_color};">{sender_label}</span>
            <span style="color: #64748b; font-size: 11px; margin-left: 8px;">[{timestamp}]</span><br>
            <div style="display: inline-block; background-color: {bubble_bg}; color: #f8fafc; padding: 6px 10px; border-radius: 6px; margin-top: 3px;">
                {safe_content}
            </div>
        </div>
        """
        self.chat_display.append(html)

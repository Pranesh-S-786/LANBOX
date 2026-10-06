"""
Main Application Window for LANBOX.
Integrates all collaboration modules: messaging, file transfer, calling, screen share,
remote assistance, announcements, and network diagnostics within a unified PyQt6 desktop UI.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QListWidget, QListWidgetItem, QMessageBox, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon

from client.ui.styles import MAIN_STYLESHEET
from client.ui.widgets.chat_view import ChatViewWidget
from client.ui.widgets.file_transfer_view import FileTransferViewWidget
from client.ui.widgets.call_view import CallViewWidget
from client.ui.widgets.screen_share_view import ScreenShareViewWidget
from client.ui.widgets.remote_assist_view import RemoteAssistViewWidget
from client.ui.widgets.announcements_view import AnnouncementsViewWidget
from client.ui.widgets.dashboard_view import DashboardViewWidget

class MainWindow(QMainWindow):
    # Signals to safely bridge background networking threads to the PyQt6 main UI loop
    msg_received_signal = pyqtSignal(dict)
    users_updated_signal = pyqtSignal(list)
    history_received_signal = pyqtSignal(object, list)
    announcement_signal = pyqtSignal(dict)
    announcements_list_signal = pyqtSignal(list)
    file_offered_signal = pyqtSignal(dict)
    call_incoming_signal = pyqtSignal(dict)
    call_response_signal = pyqtSignal(dict)
    call_ended_signal = pyqtSignal(dict)
    remote_request_signal = pyqtSignal(str)
    remote_response_signal = pyqtSignal(str, bool)
    remote_stopped_signal = pyqtSignal()
    server_stats_signal = pyqtSignal(dict)
    pong_signal = pyqtSignal(int)
    disconnected_signal = pyqtSignal(str)

    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.setWindowTitle("LANBOX - LAN Communication & Collaboration Platform")
        self.resize(1100, 700)
        self.setMinimumSize(900, 580)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._bind_client_signals()
        self._init_ui()

    def _bind_client_signals(self):
        # Bridge background client callbacks to Qt signals
        self.client.on_message_received = lambda m: self.msg_received_signal.emit(m)
        self.client.on_user_list_updated = lambda u: self.users_updated_signal.emit(u)
        self.client.on_history_received = lambda t, h: self.history_received_signal.emit(t, h)
        self.client.on_announcement_received = lambda a: self.announcement_signal.emit(a)
        self.client.on_announcements_list = lambda l: self.announcements_list_signal.emit(l)
        self.client.on_file_offered = lambda f: self.file_offered_signal.emit(f)
        self.client.on_call_incoming = lambda c: self.call_incoming_signal.emit(c)
        self.client.on_call_response = lambda r: self.call_response_signal.emit(r)
        self.client.on_call_ended = lambda e: self.call_ended_signal.emit(e)
        self.client.on_remote_request = lambda r: self.remote_request_signal.emit(r)
        self.client.on_remote_response = lambda h, acc: self.remote_response_signal.emit(h, acc)
        self.client.on_remote_stopped = lambda: self.remote_stopped_signal.emit()
        self.client.on_server_stats = lambda s: self.server_stats_signal.emit(s)
        self.client.on_pong = lambda p: self.pong_signal.emit(p)
        self.client.on_disconnected = lambda d: self.disconnected_signal.emit(d)

        # Connect Qt signals to UI handlers
        self.msg_received_signal.connect(self._handle_msg_received)
        self.users_updated_signal.connect(self._handle_users_updated)
        self.history_received_signal.connect(self._handle_history_received)
        self.announcement_signal.connect(self._handle_announcement)
        self.announcements_list_signal.connect(self._handle_announcements_list)
        self.file_offered_signal.connect(self._handle_file_offered)
        self.call_incoming_signal.connect(self._handle_call_incoming)
        self.call_response_signal.connect(self._handle_call_response)
        self.call_ended_signal.connect(self._handle_call_ended)
        self.remote_request_signal.connect(self._handle_remote_request)
        self.remote_response_signal.connect(self._handle_remote_response)
        self.remote_stopped_signal.connect(self._handle_remote_stopped)
        self.server_stats_signal.connect(self._handle_server_stats)
        self.pong_signal.connect(self._handle_pong)
        self.disconnected_signal.connect(self._handle_disconnected)

    def _init_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header Bar
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(54)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)

        logo_lbl = QLabel("📦 LANBOX")
        logo_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        logo_lbl.setStyleSheet("color: #38bdf8;")
        h_layout.addWidget(logo_lbl)

        self.user_lbl = QLabel(f"👤 {self.client.current_user or 'User'}")
        self.user_lbl.setStyleSheet("color: #f8fafc; font-weight: 600; margin-left: 16px;")
        h_layout.addWidget(self.user_lbl)

        self.server_lbl = QLabel(f"🌐 Server: {self.client.server_host}:{self.client.server_port}")
        self.server_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; margin-left: 12px;")
        h_layout.addWidget(self.server_lbl)

        h_layout.addStretch()

        logout_btn = QPushButton("Logout")
        logout_btn.setProperty("class", "DangerBtn")
        logout_btn.clicked.connect(self.close)
        h_layout.addWidget(logout_btn)

        root_layout.addWidget(header)

        # 2. Main Body: Sidebar (Left) + Stacked Views (Right)
        body = QWidget()
        b_layout = QHBoxLayout(body)
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(0)

        # Left Sidebar Frame
        sidebar = QFrame()
        sidebar.setObjectName("SidebarFrame")
        sidebar.setFixedWidth(240)
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(10, 14, 10, 14)
        s_layout.setSpacing(6)

        # Navigation Buttons Group
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.btn_chat = self._add_nav_button("💬 Messages & Chat", 0, s_layout)
        self.btn_files = self._add_nav_button("📁 File Transfer", 1, s_layout)
        self.btn_calls = self._add_nav_button("📞 Voice & Video", 2, s_layout)
        self.btn_screen = self._add_nav_button("🖥️ Screen Sharing", 3, s_layout)
        self.btn_remote = self._add_nav_button("🛠️ Remote Help", 4, s_layout)
        self.btn_announcements = self._add_nav_button("📢 Announcements", 5, s_layout)
        self.btn_dashboard = self._add_nav_button("📊 Network Stats", 6, s_layout)

        self.btn_chat.setChecked(True)

        # Online LAN Users List Section
        s_layout.addSpacing(12)
        users_title = QLabel("ONLINE PEERS")
        users_title.setStyleSheet("color: #94a3b8; font-size: 10px; font-weight: bold; margin-left: 6px;")
        s_layout.addWidget(users_title)

        self.users_list = QListWidget()
        self.users_list.itemClicked.connect(self._on_user_item_clicked)
        s_layout.addWidget(self.users_list, stretch=1)

        b_layout.addWidget(sidebar)

        # Right Stacked Central Area
        self.stack = QStackedWidget()

        self.chat_view = ChatViewWidget(self.client)
        self.chat_view.start_call_requested.connect(self._initiate_call)
        self.chat_view.send_file_requested.connect(self._switch_to_files_for_user)
        self.chat_view.request_remote_requested.connect(self._switch_to_remote_for_user)

        self.file_view = FileTransferViewWidget(self.client)
        self.call_view = CallViewWidget(self.client)
        self.call_view.start_call_requested.connect(self._initiate_call)
        self.screen_view = ScreenShareViewWidget(self.client)
        self.remote_view = RemoteAssistViewWidget(self.client)
        self.announcements_view = AnnouncementsViewWidget(self.client)
        self.dashboard_view = DashboardViewWidget(self.client)

        self.stack.addWidget(self.chat_view)           # 0
        self.stack.addWidget(self.file_view)           # 1
        self.stack.addWidget(self.call_view)           # 2
        self.stack.addWidget(self.screen_view)         # 3
        self.stack.addWidget(self.remote_view)         # 4
        self.stack.addWidget(self.announcements_view)  # 5
        self.stack.addWidget(self.dashboard_view)      # 6

        b_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(body, stretch=1)

        # Initial data requests
        self.client.refresh_user_list()
        self.client.request_history('__public__')
        self.client.request_announcements()

    def _add_nav_button(self, label: str, index: int, layout: QVBoxLayout) -> QPushButton:
        btn = QPushButton(label)
        btn.setProperty("class", "NavBtn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.stack.setCurrentIndex(index))
        self.nav_group.addButton(btn)
        layout.addWidget(btn)
        return btn

    def _on_user_item_clicked(self, item: QListWidgetItem):
        target = item.data(Qt.ItemDataRole.UserRole)
        is_online = item.data(Qt.ItemDataRole.UserRole + 1)
        self.btn_chat.setChecked(True)
        self.stack.setCurrentIndex(0)
        self.chat_view.set_target(target, is_online)

    def _switch_to_files_for_user(self, target: str):
        self.btn_files.setChecked(True)
        self.stack.setCurrentIndex(1)
        # Select target in combo
        idx = self.file_view.recipient_combo.findText(target)
        if idx >= 0:
            self.file_view.recipient_combo.setCurrentIndex(idx)

    def _switch_to_remote_for_user(self, target: str):
        self.btn_remote.setChecked(True)
        self.stack.setCurrentIndex(4)
        idx = self.remote_view.host_combo.findText(target)
        if idx >= 0:
            self.remote_view.host_combo.setCurrentIndex(idx)

    def _initiate_call(self, target: str, call_type: str):
        self.btn_calls.setChecked(True)
        self.stack.setCurrentIndex(2)
        type_str = "Video Call" if call_type == "video" else "Voice Call"
        self.call_view.status_lbl.setText(f"📞 Calling {target} ({type_str})...")
        self.call_view.remote_video_lbl.setText(f"Ringing {target}...\nWaiting for peer to accept the {type_str}.")
        self.client.start_call(target, call_type)

    # ------------------ Event Handlers ------------------

    def _handle_msg_received(self, msg: dict):
        self.chat_view.append_message(msg)

    def _handle_users_updated(self, users: list):
        self.users_list.clear()

        # Public lobby item at the top
        lobby_item = QListWidgetItem("📢 Public LAN Lobby")
        lobby_item.setData(Qt.ItemDataRole.UserRole, '__public__')
        lobby_item.setData(Qt.ItemDataRole.UserRole + 1, True)
        self.users_list.addItem(lobby_item)

        for u in users:
            name = u.get("username")
            if name == self.client.current_user:
                continue
            is_online = u.get("online", False)
            icon_str = "●" if is_online else "○"
            status_text = "Online" if is_online else "Offline"
            item = QListWidgetItem(f"{icon_str} {name} ({status_text})")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setData(Qt.ItemDataRole.UserRole + 1, is_online)
            self.users_list.addItem(item)

        # Update sub-widgets user selection combos
        self.file_view.update_user_list(users)
        self.call_view.update_user_list(users)
        self.screen_view.update_user_list(users)
        self.remote_view.update_user_list(users)

    def _handle_history_received(self, target: str | None, history: list):
        self.chat_view.set_history(target, history)

    def _handle_announcement(self, ann: dict):
        self.announcements_view.add_single_announcement(ann)
        QMessageBox.information(self, f"📢 Announcement: {ann.get('title')}", ann.get('content', ''))

    def _handle_announcements_list(self, ann_list: list):
        self.announcements_view.set_announcements(ann_list)

    def _handle_file_offered(self, offer: dict):
        self.file_view.add_incoming_file(offer)
        sender = offer.get("sender")
        filename = offer.get("filename")
        QMessageBox.information(self, "New File Shared", f"{sender} shared '{filename}' with you!\nCheck the File Transfer tab to download it.")

    def _handle_call_incoming(self, call_data: dict):
        caller = call_data.get("caller")
        call_type = call_data.get("call_type", "audio")

        reply = QMessageBox.question(
            self,
            f"Incoming {call_type.capitalize()} Call",
            f"{caller} is calling you via {call_type}.\nDo you want to accept?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.client.answer_call(caller, True, call_type)
            self.btn_calls.setChecked(True)
            self.stack.setCurrentIndex(2)
            self.call_view.start_call_session(caller, call_type)
        else:
            self.client.answer_call(caller, False, call_type)

    def _handle_call_response(self, resp_data: dict):
        accepted = resp_data.get("accepted", False)
        responder = resp_data.get("responder")
        call_type = resp_data.get("call_type", "audio")

        if accepted:
            self.call_view.start_call_session(responder, call_type)
        else:
            QMessageBox.warning(self, "Call Rejected", f"{responder} declined the call.")
            self.call_view.stop_call_session()

    def _handle_call_ended(self, hangup_data: dict):
        self.call_view.stop_call_session()
        QMessageBox.information(self, "Call Ended", "The call was ended by the peer.")

    def _handle_remote_request(self, requester: str):
        reply = QMessageBox.question(
            self,
            "Remote Assistance Permission Request",
            f"User '{requester}' wants to view and control your screen for remote assistance.\n\nGrant permission?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.client.respond_remote_assistance(requester, True)
            self.client.remote_assist.start_host_session(requester)
            QMessageBox.information(self, "Remote Assistance Active", f"Control granted to {requester}.\nMove your mouse to the top-left corner to abort anytime.")
        else:
            self.client.respond_remote_assistance(requester, False)

    def _handle_remote_response(self, host_user: str, accepted: bool):
        self.remote_view.on_permission_granted(host_user, accepted)

    def _handle_remote_stopped(self):
        QMessageBox.information(self, "Remote Assistance Ended", "The remote assistance session has ended.")

    def _handle_server_stats(self, stats: dict):
        self.dashboard_view.set_server_stats(stats)

    def _handle_pong(self, latency_ms: int):
        self.dashboard_view.set_latency(latency_ms)

    def _handle_disconnected(self, reason: str):
        QMessageBox.critical(self, "Connection Lost", reason)

    def closeEvent(self, event):
        self.client.disconnect()
        event.accept()

"""
Authentication and LAN Auto-Discovery Window for LANBOX.
Provides login, user registration, and one-click UDP auto-discovery of active LAN servers.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from common.config import DEFAULT_SERVER_PORT, DEFAULT_CLIENT_CONNECT_HOST
from client.discovery import LANDiscoveryClient

class AuthDialog(QDialog):
    login_success = pyqtSignal()

    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.setWindowTitle("LANBOX - Connect & Sign In")
        self.setFixedSize(440, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
        """)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # Title Card
        title_lbl = QLabel("📦 LANBOX")
        title_lbl.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #38bdf8;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel("LAN Communication & Collaboration Platform")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_lbl)

        layout.addSpacing(10)

        # Connection Row
        conn_row = QHBoxLayout()
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Server IP")
        self.host_input.setText(DEFAULT_CLIENT_CONNECT_HOST)
        conn_row.addWidget(self.host_input, stretch=2)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Port")
        self.port_input.setText(str(DEFAULT_SERVER_PORT))
        conn_row.addWidget(self.port_input, stretch=1)

        layout.addLayout(conn_row)

        # Auto-Discovery Button
        self.discover_btn = QPushButton("🔍 Auto-Discover LAN Server")
        self.discover_btn.setProperty("class", "SecondaryBtn")
        self.discover_btn.clicked.connect(self._auto_discover)
        layout.addWidget(self.discover_btn)

        layout.addSpacing(6)

        # Credentials Fields
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        layout.addWidget(self.user_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.returnPressed.connect(lambda: self._handle_auth("login"))
        layout.addWidget(self.pass_input)

        # Status Message
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color: #ef4444; font-size: 11px;")
        layout.addWidget(self.status_lbl)

        layout.addSpacing(6)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.login_btn = QPushButton("Log In")
        self.login_btn.setProperty("class", "PrimaryBtn")
        self.login_btn.clicked.connect(lambda: self._handle_auth("login"))
        btn_row.addWidget(self.login_btn)

        self.reg_btn = QPushButton("Register")
        self.reg_btn.setProperty("class", "SecondaryBtn")
        self.reg_btn.clicked.connect(lambda: self._handle_auth("register"))
        btn_row.addWidget(self.reg_btn)

        layout.addLayout(btn_row)

    def _auto_discover(self):
        self.status_lbl.setText("Scanning LAN for active LANBOX servers...")
        self.status_lbl.setStyleSheet("color: #38bdf8;")
        self.repaint()

        servers = LANDiscoveryClient.discover_servers(timeout=1.2)
        if servers:
            s = servers[0]
            self.host_input.setText(s["server_ip"])
            self.port_input.setText(str(s["tcp_port"]))
            self.status_lbl.setText(f"Found: {s['server_name']} ({s['server_ip']})")
            self.status_lbl.setStyleSheet("color: #10b981;")
        else:
            self.status_lbl.setText("No servers found via broadcast. Enter IP manually.")
            self.status_lbl.setStyleSheet("color: #f59e0b;")

    def _handle_auth(self, action: str):
        host = self.host_input.text().strip()
        port_str = self.port_input.text().strip()
        user = self.user_input.text().strip()
        pwd = self.pass_input.text()

        if not host or not port_str:
            self.status_lbl.setText("Server host and port required.")
            return
        try:
            port = int(port_str)
        except ValueError:
            self.status_lbl.setText("Port must be numeric.")
            return

        if not user or not pwd:
            self.status_lbl.setText("Username and password required.")
            return

        # Connect
        if not self.client.is_connected:
            self.status_lbl.setText("Connecting...")
            self.status_lbl.setStyleSheet("color: #38bdf8;")
            self.repaint()
            ok, msg = self.client.connect(host, port)
            if not ok:
                self.status_lbl.setText(f"Connection failed: {msg}")
                self.status_lbl.setStyleSheet("color: #ef4444;")
                return

        if action == "register":
            ok, msg = self.client.register(user, pwd)
            if ok:
                self.status_lbl.setText(f"{msg} You can now log in!")
                self.status_lbl.setStyleSheet("color: #10b981;")
            else:
                self.status_lbl.setText(f"Registration error: {msg}")
                self.status_lbl.setStyleSheet("color: #ef4444;")

        elif action == "login":
            ok, msg = self.client.login(user, pwd)
            if ok:
                self.accept()
                self.login_success.emit()
            else:
                self.status_lbl.setText(f"Login error: {msg}")
                self.status_lbl.setStyleSheet("color: #ef4444;")

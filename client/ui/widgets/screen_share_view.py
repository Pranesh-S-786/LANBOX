"""
Screen Sharing & Presentation View Widget for LANBOX.
Allows sharing desktop screen with connected peers or viewing incoming screen streams with adjustable quality.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap
import cv2

class ScreenShareViewWidget(QWidget):
    remote_frame_signal = pyqtSignal(object)

    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.is_broadcasting = False
        self.active_target = None

        self.remote_frame_signal.connect(self._render_frame)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Bar
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 6, 12, 6)
        h_layout.setSpacing(10)

        self.status_lbl = QLabel("🖥️ Screen Sharing Hub")
        self.status_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color: #f8fafc;")
        h_layout.addWidget(self.status_lbl)

        h_layout.addStretch()

        # Quality Preset Selector
        h_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("⚡ Ultra HD (1080p)", "1080p")
        self.quality_combo.addItem("⚙️ High Def (720p)", "720p")
        self.quality_combo.addItem("🚀 Fast / Smooth", "fast")
        h_layout.addWidget(self.quality_combo)

        # Target Selector
        h_layout.addWidget(QLabel("Share With:"))
        self.target_combo = QComboBox()
        self.target_combo.addItem("📢 Public Lobby", "__public__")
        h_layout.addWidget(self.target_combo)

        # Share Toggle Button
        self.toggle_share_btn = QPushButton("Start Screen Share")
        self.toggle_share_btn.setProperty("class", "PrimaryBtn")
        self.toggle_share_btn.clicked.connect(self._toggle_share)
        h_layout.addWidget(self.toggle_share_btn)

        layout.addWidget(header_card)

        # Large Screen Viewer Canvas
        self.canvas_card = QFrame()
        self.canvas_card.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #334155;")
        c_layout = QVBoxLayout(self.canvas_card)
        c_layout.setContentsMargins(4, 4, 4, 4)

        self.screen_lbl = QLabel("No active incoming screen share.\nClick 'Start Screen Share' above to broadcast your screen.")
        self.screen_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.screen_lbl.setStyleSheet("color: #64748b; font-size: 14px;")
        c_layout.addWidget(self.screen_lbl, stretch=1)

        layout.addWidget(self.canvas_card, stretch=1)

        # Setup incoming stream callback
        if self.client.screen_share:
            self.client.screen_share.on_remote_screen_frame = lambda f: self.remote_frame_signal.emit(f)

    def update_user_list(self, users: list):
        current_data = self.target_combo.currentData()
        self.target_combo.clear()
        self.target_combo.addItem("📢 Public Lobby", "__public__")
        for u in users:
            name = u.get("username")
            if name != self.client.current_user:
                self.target_combo.addItem(f"👤 {name}", name)

        if current_data:
            idx = self.target_combo.findData(current_data)
            if idx >= 0:
                self.target_combo.setCurrentIndex(idx)

    def _toggle_share(self):
        if not self.is_broadcasting:
            target = self.target_combo.currentData()
            quality = self.quality_combo.currentData() or "1080p"
            self.active_target = target
            self.is_broadcasting = True
            self.toggle_share_btn.setText("Stop Sharing")
            self.toggle_share_btn.setProperty("class", "DangerBtn")
            self.toggle_share_btn.style().polish(self.toggle_share_btn)
            self.quality_combo.setEnabled(False)
            self.target_combo.setEnabled(False)
            self.status_lbl.setText("🟢 Broadcasting Screen Live (HD)")

            if self.client.screen_share:
                self.client.screen_share.start_sharing(
                    self.client.current_user, target, self.client.udp_sock, quality_preset=quality
                )
        else:
            self.is_broadcasting = False
            self.toggle_share_btn.setText("Start Screen Share")
            self.toggle_share_btn.setProperty("class", "PrimaryBtn")
            self.toggle_share_btn.style().polish(self.toggle_share_btn)
            self.quality_combo.setEnabled(True)
            self.target_combo.setEnabled(True)
            self.status_lbl.setText("🖥️ Screen Sharing Hub")

            if self.client.screen_share:
                self.client.screen_share.stop_sharing()

    def _render_frame(self, frame_bgr):
        rgb_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.screen_lbl.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.screen_lbl.setPixmap(pix)

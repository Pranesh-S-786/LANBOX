"""
Voice and Video Calling View Widget for LANBOX.
Renders real-time remote video feed, local camera preview, peer call initiator, and in-call controls.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QImage, QPixmap
import cv2

class CallViewWidget(QWidget):
    start_call_requested = pyqtSignal(str, str)  # (partner_username, "audio"|"video")
    hangup_requested = pyqtSignal()
    remote_frame_signal = pyqtSignal(object)
    local_frame_signal = pyqtSignal(object)

    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.active_partner = None
        self.call_type = "audio"
        self.is_mic_muted = False
        self.is_video_muted = False
        self.call_seconds = 0

        self.call_timer = QTimer(self)
        self.call_timer.timeout.connect(self._update_timer)

        self.remote_frame_signal.connect(self._render_remote_frame)
        self.local_frame_signal.connect(self._render_local_frame)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Top Header & Launcher Bar
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 6, 12, 6)
        h_layout.setSpacing(10)

        self.status_lbl = QLabel("📞 Voice & Video Hub")
        self.status_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color: #f8fafc;")
        h_layout.addWidget(self.status_lbl)

        self.timer_lbl = QLabel("⏱️ 00:00")
        self.timer_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.timer_lbl.setStyleSheet("color: #10b981; margin-left: 8px;")
        self.timer_lbl.setVisible(False)
        h_layout.addWidget(self.timer_lbl)

        h_layout.addStretch()

        # Peer Selector & Call Launch Controls
        self.peer_lbl = QLabel("Select Peer:")
        self.peer_lbl.setStyleSheet("color: #94a3b8; font-weight: 600;")
        h_layout.addWidget(self.peer_lbl)

        self.peer_combo = QComboBox()
        self.peer_combo.setMinimumWidth(160)
        h_layout.addWidget(self.peer_combo)

        self.btn_start_voice = QPushButton("📞 Voice Call")
        self.btn_start_voice.setProperty("class", "SuccessBtn")
        self.btn_start_voice.clicked.connect(lambda: self._on_start_call_clicked("audio"))
        h_layout.addWidget(self.btn_start_voice)

        self.btn_start_video = QPushButton("📹 Video Call")
        self.btn_start_video.setProperty("class", "PrimaryBtn")
        self.btn_start_video.clicked.connect(lambda: self._on_start_call_clicked("video"))
        h_layout.addWidget(self.btn_start_video)

        layout.addWidget(header_card)

        # 2. Video Display Container
        self.video_container = QFrame()
        self.video_container.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #334155;")
        v_layout = QVBoxLayout(self.video_container)
        v_layout.setContentsMargins(8, 8, 8, 8)

        # Remote Video Screen
        self.remote_video_lbl = QLabel("No active call.\nSelect a peer above and click 'Voice Call' or 'Video Call' to connect.")
        self.remote_video_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.remote_video_lbl.setStyleSheet("color: #64748b; font-size: 15px; font-weight: 500;")
        self.remote_video_lbl.setMinimumSize(480, 320)
        v_layout.addWidget(self.remote_video_lbl, stretch=1)

        # Small Local Preview
        preview_row = QHBoxLayout()
        preview_row.addStretch()
        self.local_preview_lbl = QLabel("Local Preview")
        self.local_preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.local_preview_lbl.setFixedSize(180, 135)
        self.local_preview_lbl.setStyleSheet("background-color: #1e293b; border: 1px solid #475569; border-radius: 6px; color: #94a3b8;")
        self.local_preview_lbl.setVisible(False)
        preview_row.addWidget(self.local_preview_lbl)
        v_layout.addLayout(preview_row)

        layout.addWidget(self.video_container, stretch=1)

        # 3. In-Call Controls Bar (Mute, Camera Toggle, End Call)
        self.controls_card = QFrame()
        self.controls_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 8px;")
        c_layout = QHBoxLayout(self.controls_card)
        c_layout.setSpacing(16)
        c_layout.addStretch()

        self.mute_btn = QPushButton("🎤 Mute Mic")
        self.mute_btn.setProperty("class", "SecondaryBtn")
        self.mute_btn.clicked.connect(self._toggle_mute)
        c_layout.addWidget(self.mute_btn)

        self.cam_btn = QPushButton("📹 Stop Cam")
        self.cam_btn.setProperty("class", "SecondaryBtn")
        self.cam_btn.clicked.connect(self._toggle_cam)
        c_layout.addWidget(self.cam_btn)

        self.hangup_btn = QPushButton("❌ End Call")
        self.hangup_btn.setProperty("class", "DangerBtn")
        self.hangup_btn.clicked.connect(self._end_call)
        c_layout.addWidget(self.hangup_btn)

        c_layout.addStretch()
        self.controls_card.setVisible(False)  # Hidden when no call is active
        layout.addWidget(self.controls_card)

    def update_user_list(self, users: list):
        """Populates the peer dropdown with online peers."""
        current_data = self.peer_combo.currentData()
        self.peer_combo.clear()
        
        has_peers = False
        for u in users:
            name = u.get("username")
            if name and name != self.client.current_user:
                is_online = u.get("online", False)
                status_icon = "🟢" if is_online else "⚪"
                status_text = "Online" if is_online else "Offline"
                self.peer_combo.addItem(f"{status_icon} {name} ({status_text})", name)
                has_peers = True

        if not has_peers:
            self.peer_combo.addItem("(No other peers online)", "")
            self.btn_start_voice.setEnabled(False)
            self.btn_start_video.setEnabled(False)
        else:
            self.btn_start_voice.setEnabled(True)
            self.btn_start_video.setEnabled(True)

        if current_data:
            idx = self.peer_combo.findData(current_data)
            if idx >= 0:
                self.peer_combo.setCurrentIndex(idx)

    def _on_start_call_clicked(self, call_type: str):
        target = self.peer_combo.currentData()
        if not target:
            return
        self.start_call_requested.emit(target, call_type)

    def start_call_session(self, partner: str, call_type: str = "audio"):
        self.active_partner = partner
        self.call_type = call_type
        self.call_seconds = 0
        self.is_mic_muted = False
        self.is_video_muted = False
        self.mute_btn.setText("🎤 Mute Mic")
        self.cam_btn.setText("📹 Stop Cam")

        type_str = "Video Call" if call_type == "video" else "Voice Call"
        self.status_lbl.setText(f"🟢 In {type_str} with {partner}")
        self.timer_lbl.setText("⏱️ 00:00")
        self.timer_lbl.setVisible(True)
        self.call_timer.start(1000)

        # Update UI Controls state
        self.peer_lbl.setVisible(False)
        self.peer_combo.setVisible(False)
        self.btn_start_voice.setVisible(False)
        self.btn_start_video.setVisible(False)
        self.controls_card.setVisible(True)

        # Bind callbacks
        if self.client.video_call:
            self.client.video_call.on_remote_frame = lambda f: self.remote_frame_signal.emit(f)
            self.client.video_call.on_local_frame = lambda f: self.local_frame_signal.emit(f)

        # Start hardware streams
        if self.client.voice_call:
            self.client.voice_call.start_call(self.client.current_user, partner, self.client.udp_sock)

        if call_type == "video" and self.client.video_call:
            self.client.video_call.start_video(self.client.current_user, partner, self.client.udp_sock)
            self.local_preview_lbl.setVisible(True)
            self.cam_btn.setVisible(True)
            self.remote_video_lbl.setText("Connecting camera stream...")
        else:
            self.local_preview_lbl.setVisible(False)
            self.cam_btn.setVisible(False)
            self.remote_video_lbl.setText(f"🎙️ High-Definition Voice Call Active with {partner}\nMicrophone streaming over UDP")

    def _update_timer(self):
        self.call_seconds += 1
        mins = self.call_seconds // 60
        secs = self.call_seconds % 60
        self.timer_lbl.setText(f"⏱️ {mins:02d}:{secs:02d}")

    def _render_remote_frame(self, frame_bgr):
        rgb_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.remote_video_lbl.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.remote_video_lbl.setPixmap(pix)

    def _render_local_frame(self, frame_bgr):
        rgb_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.local_preview_lbl.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.local_preview_lbl.setPixmap(pix)

    def _toggle_mute(self):
        self.is_mic_muted = not self.is_mic_muted
        if self.is_mic_muted:
            self.mute_btn.setText("🔇 Unmute Mic")
            if self.client.voice_call:
                self.client.voice_call.is_calling = False
        else:
            self.mute_btn.setText("🎤 Mute Mic")
            if self.client.voice_call and self.active_partner:
                self.client.voice_call.start_call(self.client.current_user, self.active_partner, self.client.udp_sock)

    def _toggle_cam(self):
        self.is_video_muted = not self.is_video_muted
        if self.is_video_muted:
            self.cam_btn.setText("📹 Start Cam")
            if self.client.video_call:
                self.client.video_call.stop_video()
            self.local_preview_lbl.setText("Camera Off")
        else:
            self.cam_btn.setText("📹 Stop Cam")
            if self.client.video_call and self.active_partner:
                self.client.video_call.start_video(self.client.current_user, self.active_partner, self.client.udp_sock)

    def _end_call(self):
        if self.active_partner:
            self.client.hangup_call(self.active_partner)
        self.stop_call_session()
        self.hangup_requested.emit()

    def stop_call_session(self):
        self.call_timer.stop()
        if self.client.voice_call:
            self.client.voice_call.stop_call()
        if self.client.video_call:
            self.client.video_call.stop_video()
        self.active_partner = None
        self.status_lbl.setText("📞 Voice & Video Hub")
        self.timer_lbl.setVisible(False)
        self.remote_video_lbl.clear()
        self.remote_video_lbl.setText("No active call.\nSelect a peer above and click 'Voice Call' or 'Video Call' to connect.")
        self.local_preview_lbl.clear()
        self.local_preview_lbl.setVisible(False)

        # Restore launcher controls
        self.peer_lbl.setVisible(True)
        self.peer_combo.setVisible(True)
        self.btn_start_voice.setVisible(True)
        self.btn_start_video.setVisible(True)
        self.controls_card.setVisible(False)

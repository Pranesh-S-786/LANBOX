import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QImage, QPixmap, QMouseEvent, QKeyEvent, QWheelEvent
import cv2

class RemoteDisplayCanvas(QLabel):
    """Custom QLabel that intercepts mouse and keyboard events with precise coordinate mapping and throttled transmission."""
    input_event_generated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._last_move_time = 0
        self._last_rx = -1.0
        self._last_ry = -1.0
        self._rendered_rect = None  # (offset_x, offset_y, draw_w, draw_h)

    def set_rendered_rect(self, ox: int, oy: int, dw: int, dh: int):
        self._rendered_rect = (ox, oy, dw, dh)

    def _normalize_coords(self, pos) -> tuple[float, float]:
        if not self.pixmap() or self.pixmap().isNull():
            return None, None

        if self._rendered_rect:
            ox, oy, dw, dh = self._rendered_rect
            if dw > 0 and dh > 0:
                rx = (pos.x() - ox) / dw
                ry = (pos.y() - oy) / dh
                return max(0.0, min(1.0, rx)), max(0.0, min(1.0, ry))

        return max(0.0, min(1.0, pos.x() / max(1, self.width()))), max(0.0, min(1.0, pos.y() / max(1, self.height())))

    def mouseMoveEvent(self, ev: QMouseEvent):
        now = time.time()
        if now - self._last_move_time >= 0.025:  # ~40 Hz update rate to eliminate network backlog
            rx, ry = self._normalize_coords(ev.position())
            if rx is not None and (abs(rx - self._last_rx) > 0.001 or abs(ry - self._last_ry) > 0.001):
                self._last_move_time = now
                self._last_rx = rx
                self._last_ry = ry
                self.input_event_generated.emit({
                    "type": "mouse_move",
                    "rx": rx,
                    "ry": ry
                })
        super().mouseMoveEvent(ev)

    def mousePressEvent(self, ev: QMouseEvent):
        rx, ry = self._normalize_coords(ev.position())
        if rx is not None:
            btn = "left" if ev.button() == Qt.MouseButton.LeftButton else "right"
            self.input_event_generated.emit({
                "type": "mouse_click",
                "rx": rx,
                "ry": ry,
                "btn": btn
            })
        super().mousePressEvent(ev)

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        rx, ry = self._normalize_coords(ev.position())
        if rx is not None:
            self.input_event_generated.emit({
                "type": "mouse_double_click",
                "rx": rx,
                "ry": ry
            })
        super().mouseDoubleClickEvent(ev)

    def wheelEvent(self, ev: QWheelEvent):
        delta = ev.angleDelta().y() // 120
        if delta != 0:
            self.input_event_generated.emit({
                "type": "mouse_scroll",
                "delta": delta * 50
            })
        super().wheelEvent(ev)

    def keyPressEvent(self, ev: QKeyEvent):
        key_text = ev.text()
        if key_text:
            self.input_event_generated.emit({
                "type": "key_write",
                "text": key_text
            })
        super().keyPressEvent(ev)

class RemoteAssistViewWidget(QWidget):
    remote_frame_signal = pyqtSignal(object)

    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.active_host = None
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

        self.status_lbl = QLabel("🛠️ Remote Assistance Control")
        self.status_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.status_lbl.setStyleSheet("color: #f8fafc;")
        h_layout.addWidget(self.status_lbl)

        h_layout.addStretch()

        h_layout.addWidget(QLabel("Target PC:"))
        self.host_combo = QComboBox()
        self.host_combo.setStyleSheet("background-color: #0f172a; color: #f8fafc; padding: 4px;")
        h_layout.addWidget(self.host_combo)

        self.req_btn = QPushButton("Request Control")
        self.req_btn.setProperty("class", "PrimaryBtn")
        self.req_btn.clicked.connect(self._send_request)
        h_layout.addWidget(self.req_btn)

        self.stop_btn = QPushButton("Stop Session")
        self.stop_btn.setProperty("class", "DangerBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_session)
        h_layout.addWidget(self.stop_btn)

        layout.addWidget(header_card)

        # Interactive Canvas
        self.canvas_card = QFrame()
        self.canvas_card.setStyleSheet("background-color: #0f172a; border-radius: 12px; border: 1px solid #334155;")
        c_layout = QVBoxLayout(self.canvas_card)
        c_layout.setContentsMargins(4, 4, 4, 4)

        self.display_canvas = RemoteDisplayCanvas()
        self.display_canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display_canvas.setText("No active remote assistance session.\n(Select a peer and click 'Request Control')")
        self.display_canvas.setStyleSheet("color: #64748b; font-size: 14px;")
        self.display_canvas.input_event_generated.connect(self._on_input_event)
        c_layout.addWidget(self.display_canvas, stretch=1)

        layout.addWidget(self.canvas_card, stretch=1)

    def update_user_list(self, users: list):
        self.host_combo.clear()
        for u in users:
            name = u.get("username")
            if name != self.client.current_user:
                self.host_combo.addItem(name)

    def _send_request(self):
        target = self.host_combo.currentText()
        if not target:
            return
        self.active_host = target
        self.status_lbl.setText(f"⏳ Waiting for {target} to grant permission...")
        self.client.request_remote_assistance(target)

    def on_permission_granted(self, host_user: str, accepted: bool):
        if accepted:
            self.active_host = host_user
            self.client.remote_assist.is_controlling = True
            self.status_lbl.setText(f"🟢 Controlling {host_user}'s PC (Interactive)")
            self.stop_btn.setEnabled(True)
            self.req_btn.setEnabled(False)

            if self.client.screen_share:
                self.client.screen_share.on_remote_screen_frame = lambda f: self.remote_frame_signal.emit(f)
        else:
            self.status_lbl.setText("❌ Remote assistance request was declined.")
            QMessageBox.warning(self, "Permission Denied", f"{host_user} declined your remote assistance request.")

    def _on_input_event(self, event_dict: dict):
        if self.active_host and self.client.remote_assist:
            self.client.remote_assist.send_control_event(self.active_host, event_dict)

    def _stop_session(self):
        if self.client.remote_assist:
            self.client.remote_assist.stop_session()
        self.active_host = None
        self.status_lbl.setText("🛠️ Remote Assistance Control")
        self.stop_btn.setEnabled(False)
        self.req_btn.setEnabled(True)
        self.display_canvas.clear()
        self.display_canvas.setText("Session ended.")

    def _render_frame(self, frame_bgr):
        rgb_image = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(q_img).scaled(
            self.display_canvas.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        cw = self.display_canvas.width()
        ch = self.display_canvas.height()
        pw = pix.width()
        ph = pix.height()
        ox = (cw - pw) // 2
        oy = (ch - ph) // 2
        self.display_canvas.set_rendered_rect(ox, oy, pw, ph)
        self.display_canvas.setPixmap(pix)

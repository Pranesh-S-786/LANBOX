"""
Announcements & Bulletin Board View Widget for LANBOX.
Displays broadcast announcements with priority badges (Urgent/High/Normal) and author metadata.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QTextEdit, QComboBox, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class AnnouncementsViewWidget(QWidget):
    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.announcements = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header Bar
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 6, 12, 6)

        title_lbl = QLabel("📢 LAN Broadcast & Announcements Board")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f8fafc;")
        h_layout.addWidget(title_lbl)

        h_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setProperty("class", "SecondaryBtn")
        refresh_btn.clicked.connect(lambda: self.client.request_announcements())
        h_layout.addWidget(refresh_btn)

        layout.addWidget(header_card)

        # Create New Announcement Card
        post_card = QFrame()
        post_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 12px;")
        p_layout = QVBoxLayout(post_card)
        p_layout.setSpacing(8)

        p_header = QLabel("✍️ Post New Announcement")
        p_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p_header.setStyleSheet("color: #38bdf8;")
        p_layout.addWidget(p_header)

        form_row = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Announcement Title...")
        form_row.addWidget(self.title_input, stretch=2)

        self.priority_combo = QComboBox()
        self.priority_combo.setStyleSheet("background-color: #0f172a; color: #f8fafc; padding: 6px;")
        self.priority_combo.addItem("Normal Priority", "normal")
        self.priority_combo.addItem("⚠️ High Priority", "high")
        self.priority_combo.addItem("🚨 Urgent Alert", "urgent")
        form_row.addWidget(self.priority_combo, stretch=1)

        p_layout.addLayout(form_row)

        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Write announcement details here...")
        self.content_input.setMaximumHeight(70)
        p_layout.addWidget(self.content_input)

        post_btn = QPushButton("Broadcast to Entire LAN")
        post_btn.setProperty("class", "PrimaryBtn")
        post_btn.clicked.connect(self._submit_announcement)
        p_layout.addWidget(post_btn)

        layout.addWidget(post_card)

        # Scrollable Announcements Stream
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        self.stream_container = QWidget()
        self.stream_layout = QVBoxLayout(self.stream_container)
        self.stream_layout.setSpacing(10)
        self.stream_layout.setContentsMargins(0, 0, 0, 0)
        self.stream_layout.addStretch()

        scroll.setWidget(self.stream_container)
        layout.addWidget(scroll, stretch=1)

    def _submit_announcement(self):
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        priority = self.priority_combo.currentData()

        if not title or not content:
            QMessageBox.warning(self, "Incomplete Form", "Please fill in both title and content.")
            return

        self.client.post_announcement(title, content, priority)
        self.title_input.clear()
        self.content_input.clear()

    def set_announcements(self, ann_list: list):
        self.announcements = ann_list
        # Clear existing
        while self.stream_layout.count() > 1:
            item = self.stream_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for ann in ann_list:
            self._render_card(ann)

    def add_single_announcement(self, ann: dict):
        self.announcements.insert(0, ann)
        self._render_card(ann, prepend=True)

    def _render_card(self, ann: dict, prepend: bool = False):
        card = QFrame()
        card.setStyleSheet("background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; padding: 12px;")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(6)

        # Top line: Title & Priority Badge
        top_row = QHBoxLayout()
        title_lbl = QLabel(ann.get("title", ""))
        title_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f8fafc;")
        top_row.addWidget(title_lbl)

        top_row.addStretch()

        priority = ann.get("priority", "normal")
        badge = QLabel()
        if priority == "urgent":
            badge.setText("🚨 URGENT")
            badge.setStyleSheet("background-color: #ef4444; color: white; border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 10px;")
        elif priority == "high":
            badge.setText("⚠️ HIGH")
            badge.setStyleSheet("background-color: #f59e0b; color: black; border-radius: 4px; padding: 2px 8px; font-weight: bold; font-size: 10px;")
        else:
            badge.setText("ℹ️ NORMAL")
            badge.setStyleSheet("background-color: #2563eb; color: white; border-radius: 4px; padding: 2px 8px; font-size: 10px;")
        top_row.addWidget(badge)

        c_layout.addLayout(top_row)

        # Content
        content_lbl = QLabel(ann.get("content", ""))
        content_lbl.setWordWrap(True)
        content_lbl.setStyleSheet("color: #cbd5e1; font-size: 12px; margin-top: 4px;")
        c_layout.addWidget(content_lbl)

        # Metadata footer
        author = ann.get("author", "Unknown")
        timestamp = ann.get("timestamp", "")
        meta_lbl = QLabel(f"Posted by {author} • {timestamp}")
        meta_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        c_layout.addWidget(meta_lbl)

        if prepend:
            self.stream_layout.insertWidget(0, card)
        else:
            self.stream_layout.insertWidget(self.stream_layout.count() - 1, card)

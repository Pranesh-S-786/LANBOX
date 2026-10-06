"""
Network & Server Metrics Dashboard View Widget for LANBOX.
Displays real-time latency ping, online connected node metrics, server uptime, and traffic counters.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

class DashboardViewWidget(QWidget):
    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core

        self._init_ui()

        # Periodic refresh timer (every 4 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_metrics)
        self.timer.start(4000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Header Bar
        header_card = QFrame()
        header_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 6, 12, 6)

        title_lbl = QLabel("📊 LAN Network & Server Dashboard")
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f8fafc;")
        h_layout.addWidget(title_lbl)

        h_layout.addStretch()

        self.ping_btn = QPushButton("⚡ Ping Server")
        self.ping_btn.setProperty("class", "PrimaryBtn")
        self.ping_btn.clicked.connect(self._do_ping)
        h_layout.addWidget(self.ping_btn)

        layout.addWidget(header_card)

        # Stat Cards Grid (4 KPI boxes)
        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)

        self.card_latency = self._create_stat_card("LAN Latency (RTT)", "-- ms", "#38bdf8")
        stats_grid.addWidget(self.card_latency, 0, 0)

        self.card_uptime = self._create_stat_card("Server Uptime", "--", "#34d399")
        stats_grid.addWidget(self.card_uptime, 0, 1)

        self.card_users = self._create_stat_card("Online Devices", "--", "#a855f7")
        stats_grid.addWidget(self.card_users, 0, 2)

        self.card_traffic = self._create_stat_card("Messages Routed", "--", "#f59e0b")
        stats_grid.addWidget(self.card_traffic, 0, 3)

        layout.addLayout(stats_grid)

        # Connected LAN Nodes Table
        table_card = QFrame()
        table_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 12px;")
        t_layout = QVBoxLayout(table_card)
        t_layout.setSpacing(8)

        t_lbl = QLabel("🌐 Active LAN Nodes & Connections")
        t_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #cbd5e1;")
        t_layout.addWidget(t_lbl)

        self.nodes_table = QTableWidget(0, 3)
        self.nodes_table.setHorizontalHeaderLabels(["Username", "IP Address", "Status"])
        self.nodes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.nodes_table.setStyleSheet("background-color: #0f172a; color: #f8fafc; border: 1px solid #334155;")
        t_layout.addWidget(self.nodes_table)

        layout.addWidget(table_card, stretch=1)

    def _create_stat_card(self, title: str, value: str, accent_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; padding: 12px;")
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        title_l = QLabel(title)
        title_l.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        layout.addWidget(title_l)

        val_l = QLabel(value)
        val_l.setObjectName("ValueLabel")
        val_l.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        val_l.setStyleSheet(f"color: {accent_color};")
        layout.addWidget(val_l)

        return card

    def _do_ping(self):
        self.client.send_ping()

    def set_latency(self, latency_ms: int):
        val_lbl = self.card_latency.findChild(QLabel, "ValueLabel")
        if val_lbl:
            val_lbl.setText(f"{latency_ms} ms")

    def set_server_stats(self, stats: dict):
        uptime_sec = stats.get("uptime_seconds", 0)
        h = uptime_sec // 3600
        m = (uptime_sec % 3600) // 60
        s = uptime_sec % 60
        uptime_str = f"{h:02d}:{m:02d}:{s:02d}"

        val_uptime = self.card_uptime.findChild(QLabel, "ValueLabel")
        if val_uptime:
            val_uptime.setText(uptime_str)

        val_users = self.card_users.findChild(QLabel, "ValueLabel")
        if val_users:
            val_users.setText(str(stats.get("online_users_count", 0)))

        val_traffic = self.card_traffic.findChild(QLabel, "ValueLabel")
        if val_traffic:
            val_traffic.setText(str(stats.get("total_messages", 0)))

        # Update table
        active_users = stats.get("active_users", [])
        self.nodes_table.setRowCount(0)
        for u in active_users:
            row = self.nodes_table.rowCount()
            self.nodes_table.insertRow(row)
            self.nodes_table.setItem(row, 0, QTableWidgetItem(u.get("username", "")))
            self.nodes_table.setItem(row, 1, QTableWidgetItem(u.get("ip", "")))
            self.nodes_table.setItem(row, 2, QTableWidgetItem("🟢 Connected"))

    def _refresh_metrics(self):
        if self.client.is_connected:
            self.client.send_ping()
            self.client.request_server_stats()

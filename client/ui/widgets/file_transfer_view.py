"""
File Transfer & Sharing View Widget for LANBOX.
Supports uploading files to peers/server and downloading with real-time transfer progress bars.
"""
import os
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class FileTransferViewWidget(QWidget):
    progress_updated = pyqtSignal(int)
    transfer_finished = pyqtSignal(bool, str)

    def __init__(self, client_core, parent=None):
        super().__init__(parent)
        self.client = client_core
        self.selected_file_path = None
        self.offers = []  # list of offered file dicts

        self.progress_updated.connect(self._on_progress)
        self.transfer_finished.connect(self._on_finished)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # Title Card
        title_card = QFrame()
        title_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        t_layout = QVBoxLayout(title_card)
        t_layout.setContentsMargins(12, 8, 12, 8)

        lbl = QLabel("📁 High-Speed LAN File Sharing")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet("color: #f8fafc;")
        t_layout.addWidget(lbl)

        sub_lbl = QLabel("Transfer documents, images, and archives directly across your Local Area Network.")
        sub_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        t_layout.addWidget(sub_lbl)

        layout.addWidget(title_card)

        # Send File Section
        send_card = QFrame()
        send_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 12px;")
        s_layout = QVBoxLayout(send_card)
        s_layout.setSpacing(10)

        s_header = QLabel("📤 Send File to Peer")
        s_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        s_header.setStyleSheet("color: #38bdf8;")
        s_layout.addWidget(s_header)

        # Controls Row
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        self.recipient_combo = QComboBox()
        self.recipient_combo.setStyleSheet("background-color: #0f172a; color: #f8fafc; padding: 6px;")
        self.recipient_combo.setMinimumWidth(160)
        ctrl_layout.addWidget(QLabel("Recipient:"))
        ctrl_layout.addWidget(self.recipient_combo)

        self.browse_btn = QPushButton("Browse File...")
        self.browse_btn.setProperty("class", "SecondaryBtn")
        self.browse_btn.clicked.connect(self._browse_file)
        ctrl_layout.addWidget(self.browse_btn)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #94a3b8;")
        ctrl_layout.addWidget(self.file_label, stretch=1)

        self.upload_btn = QPushButton("Send Now")
        self.upload_btn.setProperty("class", "PrimaryBtn")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self._start_upload)
        ctrl_layout.addWidget(self.upload_btn)

        s_layout.addLayout(ctrl_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        s_layout.addWidget(self.progress_bar)

        layout.addWidget(send_card)

        # Incoming / Available Files Table
        files_card = QFrame()
        files_card.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 12px;")
        f_layout = QVBoxLayout(files_card)
        f_layout.setSpacing(10)

        f_header = QLabel("📥 Incoming Shared Files")
        f_header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        f_header.setStyleSheet("color: #34d399;")
        f_layout.addWidget(f_header)

        self.files_table = QTableWidget(0, 4)
        self.files_table.setHorizontalHeaderLabels(["Sender", "Filename", "Size", "Action"])
        self.files_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.files_table.setStyleSheet("background-color: #0f172a; color: #f8fafc; border: 1px solid #334155;")
        f_layout.addWidget(self.files_table)

        layout.addWidget(files_card, stretch=1)

    def update_user_list(self, users: list):
        self.recipient_combo.clear()
        current = self.client.current_user
        for u in users:
            name = u.get("username")
            if name != current:
                self.recipient_combo.addItem(name)

    def _browse_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select File to Share")
        if filepath:
            self.selected_file_path = filepath
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            self.file_label.setText(f"{os.path.basename(filepath)} ({size_mb:.2f} MB)")
            self.upload_btn.setEnabled(True)

    def _start_upload(self):
        if not self.selected_file_path or not self.client.file_transfer:
            return

        recipient = self.recipient_combo.currentText()
        if not recipient:
            QMessageBox.warning(self, "Select Recipient", "Please select a recipient user.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.upload_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)

        def worker():
            ok, file_id, msg = self.client.file_transfer.upload_file(
                self.selected_file_path,
                progress_callback=lambda pct: self.progress_updated.emit(pct)
            )
            if ok:
                filesize = os.path.getsize(self.selected_file_path)
                filename = os.path.basename(self.selected_file_path)
                self.client.offer_file(recipient, file_id, filename, filesize)
            self.transfer_finished.emit(ok, msg)

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, pct: int):
        self.progress_bar.setValue(pct)

    def _on_finished(self, success: bool, msg: str):
        self.upload_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, "Transfer Success", "File sent to peer successfully!")
            self.file_label.setText("No file selected")
            self.selected_file_path = None
        else:
            QMessageBox.critical(self, "Transfer Failed", msg)

    def add_incoming_file(self, offer_data: dict):
        self.offers.append(offer_data)
        row = self.files_table.rowCount()
        self.files_table.insertRow(row)

        sender = offer_data.get("sender", "Unknown")
        filename = offer_data.get("filename", "file.bin")
        file_id = offer_data.get("file_id")
        size_bytes = offer_data.get("file_size", 0)
        size_str = f"{size_bytes / (1024*1024):.2f} MB" if size_bytes >= 1024*1024 else f"{size_bytes / 1024:.1f} KB"

        self.files_table.setItem(row, 0, QTableWidgetItem(sender))
        self.files_table.setItem(row, 1, QTableWidgetItem(filename))
        self.files_table.setItem(row, 2, QTableWidgetItem(size_str))

        download_btn = QPushButton("Download")
        download_btn.setProperty("class", "SuccessBtn")
        download_btn.clicked.connect(lambda _, fid=file_id: self._download_file(fid))
        self.files_table.setCellWidget(row, 3, download_btn)

    def _download_file(self, file_id: str):
        save_dir = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if not save_dir:
            return

        def worker():
            ok, path_or_err = self.client.file_transfer.download_file(file_id, save_dir)
            if ok:
                self.transfer_finished.emit(True, f"File saved to:\n{path_or_err}")
            else:
                self.transfer_finished.emit(False, path_or_err)

        threading.Thread(target=worker, daemon=True).start()

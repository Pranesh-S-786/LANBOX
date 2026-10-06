"""
Design Stylesheet and Theme for LANBOX PyQt6 Application.
Provides a modern dark theme with clean slate, navy, and vibrant accents.
"""

MAIN_STYLESHEET = """
QMainWindow, QWidget#CentralWidget {
    background-color: #0f172a;
    color: #f8fafc;
    font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
    font-size: 13px;
}

/* Sidebar Navigation */
QFrame#SidebarFrame {
    background-color: #1e293b;
    border-right: 1px solid #334155;
}

QPushButton.NavBtn {
    background-color: transparent;
    color: #94a3b8;
    text-align: left;
    padding: 12px 16px;
    font-size: 13px;
    font-weight: 600;
    border: none;
    border-radius: 8px;
    margin: 2px 8px;
}

QPushButton.NavBtn:hover {
    background-color: #334155;
    color: #f8fafc;
}

QPushButton.NavBtn:checked {
    background-color: #2563eb;
    color: #ffffff;
}

/* Top Header Bar */
QFrame#HeaderBar {
    background-color: #1e293b;
    border-bottom: 1px solid #334155;
}

/* Content Area */
QFrame.CardFrame {
    background-color: #1e293b;
    border-radius: 12px;
    border: 1px solid #334155;
    padding: 16px;
}

/* Common Controls */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #38bdf8;
}

QPushButton.PrimaryBtn {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
}

QPushButton.PrimaryBtn:hover {
    background-color: #1d4ed8;
}

QPushButton.SuccessBtn {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
}

QPushButton.SuccessBtn:hover {
    background-color: #059669;
}

QPushButton.DangerBtn {
    background-color: #ef4444;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 8px;
    padding: 9px 18px;
}

QPushButton.DangerBtn:hover {
    background-color: #dc2626;
}

QPushButton.SecondaryBtn {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 14px;
}

QPushButton.SecondaryBtn:hover {
    background-color: #475569;
}

/* Lists & Tables */
QListWidget, QTreeWidget, QTableWidget {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 0px;
}

QListWidget::item:hover {
    background-color: #1e293b;
}

QListWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Progress Bars */
QProgressBar {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 5px;
}

/* Dropdowns & Combo Boxes */
QComboBox {
    background-color: #0f172a;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 12px;
    min-height: 22px;
    font-size: 13px;
}

QComboBox:hover {
    border: 1px solid #475569;
}

QComboBox:focus {
    border: 1px solid #38bdf8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f8fafc;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    border: 1px solid #334155;
    border-radius: 6px;
    outline: none;
    padding: 4px;
}
"""


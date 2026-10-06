"""
Main Client Launcher for LANBOX.
Initializes the PyQt6 Application, opens the Auto-Discovery / Sign-In dialog,
and launches the full LANBOX collaboration dashboard upon authentication.
"""
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from client.client_core import LANBoxClient
from client.ui.auth_window import AuthDialog
from client.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    client = LANBoxClient()

    # Step 1: Open Login / Auto-Discovery Dialog
    auth_dialog = AuthDialog(client)
    if auth_dialog.exec() == AuthDialog.DialogCode.Accepted:
        # Step 2: Open Main Dashboard
        main_win = MainWindow(client)
        main_win.show()
        sys.exit(app.exec())
    else:
        client.disconnect()
        sys.exit(0)

if __name__ == "__main__":
    main()

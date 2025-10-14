# ui.py - NetPulse main GUI
import sys, os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTabWidget, QMessageBox
from utils import ensure_npcap_installed
from main_app import NetPulseApp

if __name__ == '__main__':
    # Ensure Npcap installed on Windows (will attempt to download & install if missing)
    try:
        installed = ensure_npcap_installed()
    except Exception as e:
        installed = False
    if not installed:
        QMessageBox.warning(None, "Npcap Required", "Npcap installation failed or was canceled. NetPulse requires Npcap for full capture. Exiting.")
        sys.exit(1)

    app = QApplication(sys.argv)
    window = NetPulseApp()
    window.show()
    sys.exit(app.exec_())

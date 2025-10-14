# NetPulse - Advanced Network Monitoring Tool (with TCP retrans detection)
===================================================================

## Overview
--------
NetPulse is a Python desktop application for real-time network monitoring, scheduled tests,
historical reporting, and automated report generation. This build includes TCP retransmission
detection using Scapy and requires Npcap for full packet capture on Windows.

>**Important:** For TCP retransmission detection requires administrator privileges and Npcap.
>On first run NetPulse will attempt to download and install Npcap automatically (user consent required).

##Quick Start (developer)
-----------------------
1. Extract the ZIP to a folder.
2. Create and activate a Python virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate3. Install dependencies:

3. Install Dependencies
## pip install -r src/requirements.txt

4. Run NetPulse (as Administrator on Windows):
   python src/ui.py (ui.py is a simplified version to test startup)

# Building a standalone executable (Windows)
-----------------------------------------
1. Install PyInstaller:
bash
   pip install pyinstaller

2. From project root run:
bash
   pyinstaller --onefile --windowed src/main_app.py --name NetPulse --icon=icons\netpulse.ico

3. The executable will be in dist\NetPulse.exe

# Creating an installer (Inno Setup)
---------------------------------
1. Install Inno Setup (https://jrsoftware.org/)
2. Open build_inno_installer.iss and adjust paths if needed
3. Build (F9). Output: NetPulse_Setup.exe

#Project Structure
src/
├─ main_app.py        # Main GUI application
├─ job_scheduler.py   # APScheduler integration
├─ network_tests.py   # Ping, traceroute, DNS lookup, TCP retrans detection
├─ database.py        # SQLite database handling
├─ reporting.py       # Export to Excel/PDF
├─ utils.py           # Helper functions
└─ requirements.txt   # Python dependencies
icons/
└─ netpulse.ico       # Application icon


# Notes
-----
## - Administrator privileges are required for packet capture and installing Npcap.
## - If automatic Npcap download fails, download it manually from https://nmap.org/npcap/ and run it before starting NetPulse.

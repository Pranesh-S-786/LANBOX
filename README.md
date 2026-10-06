# LANBOX - LAN Communication & Collaboration Platform

**LANBOX** is a comprehensive Local Area Network (LAN) collaboration and communication platform built with **Python 3**, **PyQt6**, **Socket Programming (TCP/UDP)**, **SQLite**, and **Multimedia pipelines (OpenCV, SoundDevice, MSS, PyAutoGUI)**.

---

## 🌟 Features Overview

- 🔐 **User Authentication & Session Management**: Salted SHA-256 password hashing stored in SQLite with multi-session control.
- 🔍 **Zero-Config LAN Auto-Discovery**: Automatic server discovery over UDP broadcast (`5051`) without manual IP typing.
- 🟢 **Real-Time Presence Tracking**: Dynamic online/offline device monitoring across the LAN.
- 💬 **Private DMs & Public LAN Lobby**: Real-time messaging with persistent chat history.
- 📁 **High-Speed Chunked File Sharing**: Dedicated TCP file server (`5052`) with live transfer progress bars.
- 📞 **Low-Latency Voice Calling**: Real-time microphone audio capture and playback via UDP stream (`5053`).
- 📹 **Video Calling**: Real-time webcam streaming using OpenCV with JPEG frame compression.
- 🖥️ **Desktop Screen Sharing**: Live desktop streaming using MSS for team presentations.
- 🛠️ **Permission-Based Remote Assistance**: Screen streaming and remote mouse/keyboard control with user accept/deny prompts and emergency abort.
- 📢 **Broadcast Announcements Board**: Priority-tiered bulletin board (Urgent / High / Normal) with LAN popups.
- 📊 **Network & Server Metrics Dashboard**: Live RTT latency ping, connected node table, and server uptime monitor.

---

## 📁 Project Architecture & Modular Structure

```
LANBOX/
│
├── common/                         # Shared protocol & configuration
│   ├── __init__.py
│   ├── config.py                   # Port allocations, constants & IP utilities
│   └── protocol.py                 # TCP/UDP framing (JSON & Binary payloads)
│
├── server/                         # Server backend & relays
│   ├── __init__.py
│   ├── database.py                 # SQLite database (Users, Messages, Announcements, Files)
│   ├── discovery_service.py        # UDP Broadcast auto-discovery responder (Port 5051)
│   ├── file_server.py              # Dedicated TCP file transfer server (Port 5052)
│   ├── voice_video_relay.py        # Low-latency UDP media packet router (Port 5053)
│   ├── remote_relay.py             # Remote assistance session manager
│   ├── server_core.py              # Central TCP signaling, messaging & routing engine (Port 5050)
│   └── main_server.py              # Server CLI launcher & diagnostics
│
├── client/                         # Client frontend application
│   ├── __init__.py
│   ├── client_core.py              # Client networking core & event dispatch
│   ├── discovery.py                # UDP LAN broadcast scanner
│   ├── modules/                    # Feature subsystems
│   │   ├── __init__.py
│   │   ├── file_transfer.py        # Upload/download engine with progress callbacks
│   │   ├── voice_call.py           # Audio PCM capture (SoundDevice) & speaker playback
│   │   ├── video_call.py           # OpenCV camera capture & JPEG compressor
│   │   ├── screen_share.py         # MSS screen capture pipeline
│   │   └── remote_assist.py        # Remote desktop controller & PyAutoGUI executor
│   ├── ui/                         # Modern PyQt6 Desktop GUI
│   │   ├── __init__.py
│   │   ├── styles.py               # Dark theme stylesheet & widgets styling
│   │   ├── auth_window.py          # Sign In & Auto-Discovery dialog
│   │   ├── main_window.py          # Unified main dashboard window with navigation
│   │   └── widgets/                # Modular view widgets
│   │       ├── __init__.py
│   │       ├── chat_view.py          # Chat & channels view
│   │       ├── file_transfer_view.py # File sharing manager with progress bars
│   │       ├── call_view.py          # Voice & Video call canvas
│   │       ├── screen_share_view.py  # Screen presentation viewer
│   │       ├── remote_assist_view.py # Remote desktop control canvas
│   │       ├── announcements_view.py # Bulletin board
│   │       └── dashboard_view.py     # Network diagnostics & stats
│   └── main_client.py              # Client launcher
│
├── test_lanbox.py                  # Integration test suite
├── requirements.txt                # Python dependencies
└── README.md                       # Documentation
```

---

## 🔌 Network Port Allocations

| Port | Protocol | Purpose |
|---|---|---|
| `5050` | TCP | Central signaling, presence, 1-to-1 DMs, group chat, and announcements |
| `5051` | UDP | Zero-configuration LAN server broadcast auto-discovery |
| `5052` | TCP | Dedicated chunked high-speed file transfer |
| `5053` | UDP | Low-latency audio, video, and screen sharing media relay |

---

## 🚀 How to Run LANBOX

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

---

### 2. Start the Server
Open a terminal in the project folder:
```bash
python server/main_server.py
```
*The server will initialize the database, UDP auto-discovery, TCP file streamer, and media relays, displaying your LAN IP.*

---

### 3. Start Client Applications
Open one or more client windows (on the same computer or any device on the same LAN/Wi-Fi):
```bash
python client/main_client.py
```

1. Click **🔍 Auto-Discover LAN Server** (or enter Server IP).
2. Enter username (e.g. `alice`) and password.
3. Click **Register** (first time), then **Log In**.
4. Access all collaboration modules from the left navigation drawer:
   - 💬 **Messages & Chat**: Send direct messages or chat in the Public Lobby.
   - 📁 **File Transfer**: Select recipient, browse file, and send with real-time progress.
   - 📞 **Voice & Video**: Start voice or webcam video calls with peers.
   - 🖥️ **Screen Sharing**: Broadcast your screen to the lobby or direct peers.
   - 🛠️ **Remote Help**: Request permission-based remote desktop control.
   - 📢 **Announcements**: Post priority broadcast alerts to the entire LAN.
   - 📊 **Network Stats**: Monitor ping latency, active nodes, and server uptime.

---

## 🧪 Automated Testing
Run the automated test suite to verify all core services:
```bash
python test_lanbox.py
```

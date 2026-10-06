"""
LANBOX Configuration & Protocol Constants.
Defines network ports, buffer sizes, and message action types for all collaboration modules.
"""
import socket

# Network Ports Configuration
PORT_TCP_MAIN = 5050          # Central messaging, presence & signaling
PORT_UDP_DISCOVERY = 5051     # LAN automatic server/peer discovery beacon
PORT_TCP_FILE_TRANSFER = 5052 # High-speed chunked file transfer
PORT_UDP_VOICE_VIDEO = 5053   # Low-latency UDP Audio / Video streaming
PORT_TCP_REMOTE_ASSIST = 5054 # Remote desktop control & screen frames

DEFAULT_SERVER_PORT = PORT_TCP_MAIN
DEFAULT_SERVER_HOST = '0.0.0.0'
DEFAULT_CLIENT_CONNECT_HOST = '127.0.0.1'
DEFAULT_BROADCAST_IP = '255.255.255.255'

BUFFER_SIZE = 8192
FILE_CHUNK_SIZE = 64 * 1024   # 64 KB chunks for fast LAN file transfers
HEADER_SIZE = 4               # 4-byte prefix for TCP length framing

# ----------------- Message Types (Action Protocol) -----------------

# Authentication & Session
TYPE_REGISTER = 'REGISTER'
TYPE_LOGIN = 'LOGIN'
TYPE_AUTH_RESPONSE = 'AUTH_RESPONSE'
TYPE_LOGOUT = 'LOGOUT'
TYPE_USER_LIST = 'USER_LIST'
TYPE_USER_STATUS = 'USER_STATUS'

# Chat & Messaging
TYPE_DIRECT_MSG = 'DIRECT_MSG'
TYPE_BROADCAST_MSG = 'BROADCAST_MSG'
TYPE_MSG_HISTORY = 'MSG_HISTORY'
TYPE_MSG_HISTORY_RESPONSE = 'MSG_HISTORY_RESPONSE'

# Announcements & Bulletin Board
TYPE_ANNOUNCEMENT_POST = 'ANNOUNCEMENT_POST'
TYPE_ANNOUNCEMENT_BROADCAST = 'ANNOUNCEMENT_BROADCAST'
TYPE_ANNOUNCEMENT_LIST = 'ANNOUNCEMENT_LIST'
TYPE_ANNOUNCEMENT_LIST_RESPONSE = 'ANNOUNCEMENT_LIST_RESPONSE'

# File Sharing
TYPE_FILE_OFFER = 'FILE_OFFER'
TYPE_FILE_RESPONSE = 'FILE_RESPONSE'   # Accept / Reject
TYPE_FILE_READY = 'FILE_READY'

# Voice & Video Calling (Signaling)
TYPE_CALL_OFFER = 'CALL_OFFER'         # audio or video
TYPE_CALL_ANSWER = 'CALL_ANSWER'       # accept or decline
TYPE_CALL_HANGUP = 'CALL_HANGUP'
TYPE_CALL_BUSY = 'CALL_BUSY'

# Screen Sharing (Signaling)
TYPE_SCREEN_SHARE_START = 'SCREEN_SHARE_START'
TYPE_SCREEN_SHARE_STOP = 'SCREEN_SHARE_STOP'
TYPE_SCREEN_SHARE_FRAME = 'SCREEN_SHARE_FRAME'

# Remote Assistance (Permission-Based)
TYPE_REMOTE_REQUEST = 'REMOTE_REQUEST'
TYPE_REMOTE_RESPONSE = 'REMOTE_RESPONSE' # Accept / Deny
TYPE_REMOTE_INPUT_EVENT = 'REMOTE_INPUT_EVENT'
TYPE_REMOTE_STOP = 'REMOTE_STOP'

# Network & Server Dashboard
TYPE_PING = 'PING'
TYPE_PONG = 'PONG'
TYPE_SERVER_STATS = 'SERVER_STATS'
TYPE_ERROR = 'ERROR'

# ----------------- Utility Functions -----------------

def get_local_lan_ip() -> str:
    """
    Returns the primary outbound LAN IPv4 address of this machine.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

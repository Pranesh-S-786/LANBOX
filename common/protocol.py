"""
Protocol module for LANBOX.
Handles framing, serialization, and deserialization of JSON packets and binary payloads over TCP/UDP sockets.
"""
import json
import struct
import socket

def send_json(sock: socket.socket, data: dict) -> bool:
    """
    Serializes a dictionary to JSON, encodes as UTF-8, prefixes with 4-byte big-endian length,
    and sends the entire message over the socket.
    """
    try:
        payload = json.dumps(data).encode('utf-8')
        header = struct.pack('!I', len(payload))
        sock.sendall(header + payload)
        return True
    except (socket.error, OSError, BrokenPipeError, ConnectionResetError):
        return False

def recv_exact(sock: socket.socket, num_bytes: int) -> bytes | None:
    """
    Helper to reliably receive exactly `num_bytes` from a stream socket.
    Returns None if the connection closes before receiving all bytes.
    """
    data = bytearray()
    while len(data) < num_bytes:
        try:
            packet = sock.recv(num_bytes - len(data))
            if not packet:
                return None
            data.extend(packet)
        except (socket.error, OSError, ConnectionResetError):
            return None
    return bytes(data)

def recv_json(sock: socket.socket) -> dict | None:
    """
    Reads a 4-byte length header, then reads the corresponding payload and deserializes as JSON.
    Returns the parsed dictionary, or None if the socket is closed or corrupted.
    """
    try:
        header = recv_exact(sock, 4)
        if not header:
            return None
        
        payload_length = struct.unpack('!I', header)[0]
        if payload_length == 0:
            return {}

        payload_bytes = recv_exact(sock, payload_length)
        if not payload_bytes:
            return None

        return json.loads(payload_bytes.decode('utf-8'))
    except (json.JSONDecodeError, struct.error, OSError):
        return None

def send_binary_frame(sock: socket.socket, frame_type: int, payload: bytes) -> bool:
    """
    Sends a binary payload with a 1-byte frame_type indicator and 4-byte length prefix.
    Header format: [1 byte frame_type][4 bytes length]
    """
    try:
        header = struct.pack('!BI', frame_type, len(payload))
        sock.sendall(header + payload)
        return True
    except (socket.error, OSError):
        return False

def recv_binary_frame(sock: socket.socket) -> tuple[int, bytes] | tuple[None, None]:
    """
    Receives a binary frame: (frame_type: int, payload: bytes).
    """
    try:
        header = recv_exact(sock, 5)
        if not header:
            return None, None
        frame_type, length = struct.unpack('!BI', header)
        payload = recv_exact(sock, length)
        if payload is None:
            return None, None
        return frame_type, payload
    except (struct.error, OSError):
        return None, None

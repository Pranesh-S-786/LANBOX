"""
Dedicated TCP File Transfer Server for LANBOX.
Handles high-speed chunked file uploads, storage, and downloads with progress tracking.
"""
import socket
import threading
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import PORT_TCP_FILE_TRANSFER, FILE_CHUNK_SIZE
from common.protocol import send_json, recv_json, recv_exact

class FileTransferServer:
    def __init__(self, host: str = "0.0.0.0", port: int = PORT_TCP_FILE_TRANSFER, storage_dir: str = "server_storage"):
        self.host = host
        self.port = port
        self.storage_dir = storage_dir
        self.sock = None
        self.is_running = False
        self.thread = None

        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen(15)
            self.is_running = True
            self.thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.thread.start()
            print(f"[+] TCP File Transfer Server listening on port {self.port}")
        except Exception as e:
            print(f"[!] File Transfer Server failed to bind to port {self.port}: {e}")

    def _accept_loop(self):
        while self.is_running and self.sock:
            try:
                conn, addr = self.sock.accept()
                t = threading.Thread(target=self._handle_transfer, args=(conn, addr), daemon=True)
                t.start()
            except OSError:
                break

    def _handle_transfer(self, sock: socket.socket, addr: tuple):
        try:
            req = recv_json(sock)
            if not req:
                return

            action = req.get("action")

            if action == "UPLOAD":
                filename = os.path.basename(req.get("filename", "file.bin"))
                file_size = req.get("file_size", 0)
                file_id = str(uuid.uuid4())[:8] + "_" + filename
                save_path = os.path.join(self.storage_dir, file_id)

                send_json(sock, {"status": "READY", "file_id": file_id})

                received = 0
                with open(save_path, "wb") as f:
                    while received < file_size:
                        to_read = min(FILE_CHUNK_SIZE, file_size - received)
                        chunk = recv_exact(sock, to_read)
                        if not chunk:
                            break
                        f.write(chunk)
                        received += len(chunk)

                if received == file_size:
                    send_json(sock, {"status": "SUCCESS", "file_id": file_id, "size": received})
                    print(f"[+] File uploaded successfully: {filename} ({received} bytes)")
                else:
                    send_json(sock, {"status": "FAILED", "reason": "Incomplete transfer"})

            elif action == "DOWNLOAD":
                file_id = req.get("file_id")
                file_path = os.path.join(self.storage_dir, file_id)
                if not os.path.exists(file_path):
                    send_json(sock, {"status": "NOT_FOUND"})
                    return

                size = os.path.getsize(file_path)
                send_json(sock, {"status": "READY", "file_size": size})

                with open(file_path, "rb") as f:
                    while True:
                        chunk = f.read(FILE_CHUNK_SIZE)
                        if not chunk:
                            break
                        sock.sendall(chunk)

                print(f"[+] File streamed to client {addr[0]}: {file_id}")

        except Exception as e:
            print(f"[-] File transfer error with {addr}: {e}")
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def stop(self):
        self.is_running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

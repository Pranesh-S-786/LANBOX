"""
File Transfer Client Module for LANBOX.
Handles high-speed chunked uploading and downloading with real-time percentage callbacks.
"""
import socket
import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from common.config import PORT_TCP_FILE_TRANSFER, FILE_CHUNK_SIZE
from common.protocol import send_json, recv_json, recv_exact

class FileTransferClient:
    def __init__(self, host: str, port: int = PORT_TCP_FILE_TRANSFER):
        self.host = host
        self.port = port

    def upload_file(self, filepath: str, progress_callback=None) -> tuple[bool, str, str]:
        """
        Uploads a file to the LANBOX file server.
        Returns (success: bool, file_id: str, message: str).
        """
        if not os.path.exists(filepath):
            return False, "", "File not found."

        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            
            # Step 1: Handshake
            req = {"action": "UPLOAD", "filename": filename, "file_size": filesize}
            if not send_json(sock, req):
                return False, "", "Failed to send upload handshake."

            resp = recv_json(sock)
            if not resp or resp.get("status") != "READY":
                return False, "", "Server rejected file upload."

            file_id = resp.get("file_id")

            # Step 2: Stream File Chunks
            sent = 0
            with open(filepath, "rb") as f:
                while sent < filesize:
                    chunk = f.read(FILE_CHUNK_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    sent += len(chunk)
                    if progress_callback:
                        progress_callback(int((sent / filesize) * 100))

            # Step 3: Final confirmation
            final_resp = recv_json(sock)
            if final_resp and final_resp.get("status") == "SUCCESS":
                return True, file_id, "Upload completed successfully."
            else:
                return False, "", "Server reported upload failure."

        except Exception as e:
            return False, "", f"Upload error: {str(e)}"
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def download_file(self, file_id: str, save_destination_dir: str, progress_callback=None) -> tuple[bool, str]:
        """
        Downloads a file by file_id from the LANBOX file server.
        Returns (success: bool, saved_filepath_or_err: str).
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))

            req = {"action": "DOWNLOAD", "file_id": file_id}
            if not send_json(sock, req):
                return False, "Failed to send download request."

            resp = recv_json(sock)
            if not resp or resp.get("status") != "READY":
                return False, "File not found or server not ready."

            filesize = resp.get("file_size", 0)
            # Extract clean filename from file_id (e.g. uuid_filename.ext)
            clean_filename = file_id.split("_", 1)[-1] if "_" in file_id else file_id
            save_path = os.path.join(save_destination_dir, clean_filename)

            # Ensure unique filename if already exists
            base, ext = os.path.splitext(save_path)
            counter = 1
            while os.path.exists(save_path):
                save_path = f"{base}_{counter}{ext}"
                counter += 1

            received = 0
            with open(save_path, "wb") as f:
                while received < filesize:
                    to_read = min(FILE_CHUNK_SIZE, filesize - received)
                    chunk = recv_exact(sock, to_read)
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)
                    if progress_callback and filesize > 0:
                        progress_callback(int((received / filesize) * 100))

            if received == filesize:
                return True, save_path
            else:
                return False, "Incomplete download."

        except Exception as e:
            return False, f"Download error: {str(e)}"
        finally:
            try:
                sock.close()
            except Exception:
                pass

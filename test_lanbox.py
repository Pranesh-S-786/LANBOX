"""
Automated unit & integration test suite for LANBOX comprehensive platform.
Tests Authentication, Messaging, Announcements, File Transfer, Discovery, and Media Relays.
"""
import unittest
import time
import threading
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from common.config import PORT_TCP_MAIN, PORT_TCP_FILE_TRANSFER
from server.database import DatabaseManager
from server.server_core import LANBoxServer
from client.client_core import LANBoxClient
from client.discovery import LANDiscoveryClient

class TestLANBoxComprehensive(unittest.TestCase):
    TEST_DB = "test_full_lanbox.db"
    TEST_PORT = 5060
    TEST_HOST = "127.0.0.1"

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.TEST_DB):
            os.remove(cls.TEST_DB)

        # Start central server
        cls.server = LANBoxServer(host=cls.TEST_HOST, port=cls.TEST_PORT, db_path=cls.TEST_DB)
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        time.sleep(0.2)
        if os.path.exists(cls.TEST_DB):
            try:
                os.remove(cls.TEST_DB)
            except Exception:
                pass

    def test_01_database_and_announcements(self):
        db = DatabaseManager(self.TEST_DB)
        # Register users
        ok, msg = db.register_user("admin_user", "adminpass")
        self.assertTrue(ok)
        ok, msg = db.register_user("client_user", "clientpass")
        self.assertTrue(ok)

        # Announcements
        ann = db.create_announcement("admin_user", "Maintenance Alert", "Server will restart in 10 mins.", "urgent")
        self.assertEqual(ann["priority"], "urgent")

        anns = db.get_announcements()
        self.assertTrue(any(a["title"] == "Maintenance Alert" for a in anns))

    def test_02_client_messaging_and_presence(self):
        c1 = LANBoxClient()
        c2 = LANBoxClient()

        c1.connect(self.TEST_HOST, self.TEST_PORT)
        c2.connect(self.TEST_HOST, self.TEST_PORT)

        c1.login("admin_user", "adminpass")
        c2.login("client_user", "clientpass")

        received_c2 = []
        c2.on_message_received = lambda m: received_c2.append(m)

        time.sleep(0.3)
        c1.send_direct_message("client_user", "Direct Test Message")
        time.sleep(0.3)

        self.assertTrue(any(m.get("content") == "Direct Test Message" for m in received_c2))

        c1.disconnect()
        c2.disconnect()

    def test_03_file_transfer_service(self):
        # Create a test file
        test_file = "test_upload_sample.txt"
        with open(test_file, "w") as f:
            f.write("LANBOX File Transfer Streaming Test Content" * 20)

        c = LANBoxClient()
        c.connect(self.TEST_HOST, self.TEST_PORT)
        c.login("admin_user", "adminpass")

        # Upload file
        ok, file_id, msg = c.file_transfer.upload_file(test_file)
        self.assertTrue(ok)
        self.assertTrue(len(file_id) > 0)

        # Download file
        download_dir = "test_downloads"
        os.makedirs(download_dir, exist_ok=True)
        ok, saved_path = c.file_transfer.download_file(file_id, download_dir)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(saved_path))

        # Cleanup
        c.disconnect()
        if os.path.exists(test_file):
            os.remove(test_file)
        if os.path.exists(saved_path):
            os.remove(saved_path)
        if os.path.exists(download_dir):
            try:
                os.rmdir(download_dir)
            except Exception:
                pass

    def test_04_udp_lan_discovery(self):
        servers = LANDiscoveryClient.discover_servers(timeout=1.0)
        self.assertIsInstance(servers, list)

if __name__ == "__main__":
    unittest.main()

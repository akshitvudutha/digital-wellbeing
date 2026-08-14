"""
manual_updater_test.py - Safe manual test for the updater UI flow.

Run this script to launch Digital Wellbeing with a mocked GitHub release
to verify the updater dialog and download UI without publishing a real release.
"""
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import hashlib

# Start a local HTTP server to serve a fake installer and checksum
FAKE_INSTALLER_PORT = 8080

class FakeInstallerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/DigitalWellbeingSetup-2.5.3.exe":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msdownload")
            self.send_header("Content-Length", "1024000") # 1MB fake file
            self.end_headers()
            
            # Send 1MB of zeroes
            fake_data = b"0" * 1024000
            self.wfile.write(fake_data)
            
            # Calculate SHA256 of the fake data to use in the checksum request
            self.server.fake_sha256 = hashlib.sha256(fake_data).hexdigest()
            
        elif self.path == "/DigitalWellbeingSetup-2.5.3.exe.sha256":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            
            if hasattr(self.server, "fake_sha256"):
                self.wfile.write(self.server.fake_sha256.encode("utf-8"))
            else:
                self.wfile.write(b"fakehash")
                
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress logs

def run_fake_server():
    server = HTTPServer(("localhost", FAKE_INSTALLER_PORT), FakeInstallerHandler)
    server.serve_forever()

if __name__ == "__main__":
    print("Starting fake installer server on port", FAKE_INSTALLER_PORT)
    t = threading.Thread(target=run_fake_server, daemon=True)
    t.start()

    from PySide6.QtWidgets import QApplication
    from core.updater import set_mock_release_data
    from tracker.manager import TrackingManager
    from ui.main_window import MainWindow

    # Set mock data claiming v2.5.3 is available
    mock_data = [
        {
            "tag_name": "v2.5.3",
            "draft": False,
            "prerelease": False,
            "body": "• Fake release notes for testing\n• Verifies the update dialog UI\n• Tests the download progress bar\n• Checks SHA-256 verification",
            "assets": [
                {
                    "name": "DigitalWellbeingSetup-2.5.3.exe", 
                    "browser_download_url": f"http://localhost:{FAKE_INSTALLER_PORT}/DigitalWellbeingSetup-2.5.3.exe"
                },
                {
                    "name": "DigitalWellbeingSetup-2.5.3.exe.sha256", 
                    "browser_download_url": f"http://localhost:{FAKE_INSTALLER_PORT}/DigitalWellbeingSetup-2.5.3.exe.sha256"
                }
            ]
        }
    ]
    set_mock_release_data(mock_data)

    print("Launching Digital Wellbeing with mock updater data...")
    print("Go to Settings -> Updates and click 'Check for Updates' to test the flow.")

    app = QApplication(sys.argv)
    
    # Normally we'd start full tracking, but for a simple UI test this is enough
    tracker = TrackingManager()
    
    window = MainWindow(tracker=tracker)
    window.show()
    
    sys.exit(app.exec())

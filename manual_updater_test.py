"""
manual_updater_test.py - Safe manual test for the updater UI flow.

Run this script to launch Digital Wellbeing with a mocked GitHub release
to verify the updater dialog and download UI without publishing a real release.
"""
import sys
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import hashlib
import json

# Start a local HTTP server to serve a fake installer and checksum
FAKE_INSTALLER_PORT = 8080

class FakeInstallerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/repos/akshitvudutha/digital-wellbeing/releases":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            mock_data = [
                {
                    "tag_name": "v9.9.9",
                    "draft": False,
                    "prerelease": False,
                    "body": "• Fake release notes for testing\n• Verifies the update dialog UI\n• Tests the download progress bar\n• Checks SHA-256 verification",
                    "assets": [
                        {
                            "name": "DigitalWellbeingSetup-9.9.9.exe", 
                            "browser_download_url": f"http://localhost:{FAKE_INSTALLER_PORT}/DigitalWellbeingSetup-9.9.9.exe"
                        },
                        {
                            "name": "DigitalWellbeingSetup-9.9.9.exe.sha256", 
                            "browser_download_url": f"http://localhost:{FAKE_INSTALLER_PORT}/DigitalWellbeingSetup-9.9.9.exe.sha256"
                        }
                    ]
                }
            ]
            self.wfile.write(json.dumps(mock_data).encode("utf-8"))

        elif self.path == "/DigitalWellbeingSetup-9.9.9.exe":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msdownload")
            self.send_header("Content-Length", "1024000") # 1MB fake file
            self.end_headers()
            
            # Send 1MB of zeroes
            fake_data = b"0" * 1024000
            self.wfile.write(fake_data)
            
            # Calculate SHA256 of the fake data to use in the checksum request
            self.server.fake_sha256 = hashlib.sha256(fake_data).hexdigest()
            
        elif self.path == "/DigitalWellbeingSetup-9.9.9.exe.sha256":
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

    os.environ["GITHUB_API_BASE"] = f"http://localhost:{FAKE_INSTALLER_PORT}"

    print("Launching Digital Wellbeing with mock updater data...")
    print("Go to Settings -> Updates and click 'Check for Updates' to test the flow.")

    from ui.app import DigitalWellbeingApp
    app = DigitalWellbeingApp()
    sys.exit(app.run(start_minimized=False))

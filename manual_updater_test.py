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
                    "tag_name": "v3.6.2",
                    "draft": False,
                    "prerelease": False,
                    "body": "• Notch 3.6.2 Feature & Stability Update\n• In-app update verification\n• SHA-256 verified package",
                    "assets": [
                        {
                            "name": "NotchSetup-3.6.2.exe", 
                            "browser_download_url": f"http://localhost:{FAKE_INSTALLER_PORT}/NotchSetup-3.6.2.exe"
                        },
                        {
                            "name": "NotchSetup-3.6.2.exe.sha256", 
                            "browser_download_url": f"http://localhost:{FAKE_INSTALLER_PORT}/NotchSetup-3.6.2.exe.sha256"
                        }
                    ]
                }
            ]
            self.wfile.write(json.dumps(mock_data).encode("utf-8"))

        elif self.path == "/NotchSetup-3.6.2.exe":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msdownload")
            fake_data = b"MZ\x90\x00" + b"\x00" * 512000 # 500KB fake installer
            self.send_header("Content-Length", str(len(fake_data)))
            self.end_headers()
            self.wfile.write(fake_data)
            self.server.fake_sha256 = hashlib.sha256(fake_data).hexdigest()
            
        elif self.path == "/NotchSetup-3.6.2.exe.sha256":
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

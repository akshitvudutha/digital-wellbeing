import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import hashlib
from pathlib import Path
import pytest

from core.updater import check_for_update, set_mock_release_data, download_update, verify_update, launch_installer

FAKE_PORT = 8081

class FakeInstallerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/update.exe":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msdownload")
            fake_data = b"MZ" + b"0" * 1024
            self.send_header("Content-Length", str(len(fake_data)))
            self.end_headers()
            self.wfile.write(fake_data)
            self.server.fake_sha256 = hashlib.sha256(fake_data).hexdigest()
        elif self.path == "/update.exe.sha256":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(self.server.fake_sha256.encode("utf-8"))
        elif self.path == "/corrupt.exe":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-msdownload")
            fake_data = b"corrupt data"
            self.send_header("Content-Length", str(len(fake_data)))
            self.end_headers()
            self.wfile.write(fake_data)
        elif self.path == "/corrupt.exe.sha256":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"badhash")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args): pass

@pytest.fixture(scope="module")
def fake_server():
    server = HTTPServer(("localhost", FAKE_PORT), FakeInstallerHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield server
    server.shutdown()

def test_full_update_flow(fake_server, monkeypatch):
    mock_data = [
        {
            "tag_name": "v2.5.2",
            "draft": False,
            "prerelease": False,
            "body": "Update notes",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.5.2.exe", "browser_download_url": f"http://localhost:{FAKE_PORT}/update.exe"},
                {"name": "DigitalWellbeingSetup-2.5.2.exe.sha256", "browser_download_url": f"http://localhost:{FAKE_PORT}/update.exe.sha256"}
            ]
        },
        {"tag_name": "v2.5.3-beta", "draft": False, "prerelease": True, "assets": []},
        {"tag_name": "v2.5.1", "draft": False, "prerelease": False, "assets": []}
    ]
    set_mock_release_data(mock_data)
    
    # 1. GitHub release discovery & stable filtering & version comparison
    info = check_for_update("2.5.1")
    assert info is not None
    assert info.version == "2.5.2"
    assert info.installer_url == f"http://localhost:{FAKE_PORT}/update.exe"
    
    # 2. Download
    progress_calls = []
    def progress_cb(dl, tot):
        progress_calls.append((dl, tot))
        
    installer_path = download_update(info, progress_cb)
    assert installer_path.exists()
    assert len(progress_calls) > 0
    assert progress_calls[-1][0] == progress_calls[-1][1]
    
    # 3. SHA-256 verification
    assert verify_update(installer_path) is True
    
    # 4. Installer Launch and Handoff
    import subprocess
    launch_called = []
    def mock_popen(args, **kwargs):
        launch_called.append(args)
        class MockProcess:
            def pid(self): return 1234
        return MockProcess()
        
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    
    success = launch_installer(installer_path)
    assert success is True
    assert len(launch_called) == 1
    assert launch_called[0][0] == str(installer_path)
    assert "/SILENT" in launch_called[0]
    assert "/NORESTART" not in launch_called[0]  # Depends on the implementation
    
    installer_path.unlink()

def test_failure_handling(fake_server):
    mock_data = [
        {
            "tag_name": "v2.5.2",
            "draft": False,
            "prerelease": False,
            "body": "Update notes",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.5.2.exe", "browser_download_url": f"http://localhost:{FAKE_PORT}/corrupt.exe"},
                {"name": "DigitalWellbeingSetup-2.5.2.exe.sha256", "browser_download_url": f"http://localhost:{FAKE_PORT}/corrupt.exe.sha256"}
            ]
        }
    ]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.1")
    
    installer_path = download_update(info, lambda d,t: None)
    
    # Verification should fail
    assert verify_update(installer_path) is False
    
    if installer_path.exists():
        installer_path.unlink()

def test_dynamic_url_generation_v252():
    mock_data = [
        {
            "tag_name": "v2.5.2",
            "draft": False,
            "prerelease": False,
            "body": "Release 2.5.2 notes",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.5.2.exe", "browser_download_url": f"http://localhost:{FAKE_PORT}/update_252.exe"}
            ]
        }
    ]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.1")
    assert info is not None
    assert info.version == "2.5.2"
    assert info.installer_url == f"http://localhost:{FAKE_PORT}/update_252.exe"
    assert info.installer_filename == "DigitalWellbeingSetup-2.5.2.exe"
    assert "2.0.1" not in info.installer_url

def test_dynamic_url_generation_v253():
    mock_data = [
        {
            "tag_name": "v2.5.3",
            "draft": False,
            "prerelease": False,
            "body": "Release 2.5.3 notes",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.5.3.exe", "browser_download_url": f"http://localhost:{FAKE_PORT}/update_253.exe"}
            ]
        }
    ]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.2")
    assert info is not None
    assert info.version == "2.5.3"
    assert info.installer_url == f"http://localhost:{FAKE_PORT}/update_253.exe"
    assert info.installer_filename == "DigitalWellbeingSetup-2.5.3.exe"
    assert "2.0.1" not in info.installer_url
    assert "2.5.2" not in info.installer_url

def test_dynamic_url_generation_ignores_old_tags():
    mock_data = [
        {
            "tag_name": "v2.0.1",
            "draft": False,
            "prerelease": False,
            "body": "Old release notes",
            "assets": [
                {"name": "DigitalWellbeingSetup-2.0.1.exe", "browser_download_url": f"http://localhost:{FAKE_PORT}/old.exe"}
            ]
        }
    ]
    set_mock_release_data(mock_data)
    info = check_for_update("2.5.2")
    # Should not offer an update since 2.0.1 is older than 2.5.2
    assert info is None

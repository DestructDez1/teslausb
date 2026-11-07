#!/usr/bin/env python3
"""
TeslaUSB Setup Studio Local Web Server
Bridges the web UI directly to disk flashing and configuration.
Runs on standard Python 3 with zero external dependencies.
"""

import ctypes
from ctypes import wintypes
import http.server
import json
import os
import platform
import re
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
import zipfile

PORT = 8000
STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(STUDIO_DIR)
CACHE_DIR = os.path.join(PROJECT_DIR, "cache")
ZIP_CACHE_PATH = os.path.join(CACHE_DIR, "teslausb-image.zip")
IMAGE_URL = "https://github.com/marcone/teslausb/releases/download/v3.2/teslausb-20211106-2.zip"

# Win32 API
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

try:
    CreateFileW = ctypes.windll.kernel32.CreateFileW
    CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
    ]
    CreateFileW.restype = wintypes.HANDLE

    WriteFile = ctypes.windll.kernel32.WriteFile
    WriteFile.argtypes = [
        wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID
    ]
    WriteFile.restype = wintypes.BOOL

    CloseHandle = ctypes.windll.kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL
except Exception:
    pass

# Global Flashing State
flash_state = {
    "status": "idle", # idle, downloading, flashing, configuring, complete, error
    "progress": 0.0,
    "speed": "",
    "message": "",
    "error": None
}

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def verify_safe_external_disk(disk_number):
    """
    CRITICAL SAFETY CHECK:
    Verifies that the target disk is STRICTLY an external USB / SD card drive.
    Permanently rejects internal SATA, NVMe, IDE, SCSI, RAID, and system/boot disks.
    """
    ps_cmd = (
        f"Get-Disk -Number {disk_number} | "
        "Select-Object Number, FriendlyName, BusType, IsBoot, IsSystem, Size | "
        "ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True, errors="ignore")
        d = json.loads(out)
        if isinstance(d, list):
            d = d[0]

        bus = str(d.get("BusType", "")).upper()
        if bus not in ["USB", "SD", "MMC"]:
            return False, f"SAFETY BLOCK: Disk {disk_number} is an internal drive ({bus}). Only external USB/SD drives are allowed!"

        if d.get("IsBoot") is True or d.get("IsSystem") is True:
            return False, f"SAFETY BLOCK: Disk {disk_number} is the Windows Boot/System drive!"

        # Partition check for Windows drive letters like C:
        part_cmd = (
            f"Get-Partition -DiskNumber {disk_number} | "
            "Select-Object DiskNumber, PartitionNumber, DriveLetter, IsBoot, IsSystem | "
            "ConvertTo-Json -Compress"
        )
        try:
            part_out = subprocess.check_output(["powershell", "-NoProfile", "-Command", part_cmd], text=True, errors="ignore")
            parts = json.loads(part_out)
            if isinstance(parts, dict):
                parts = [parts]
            for p in parts:
                if str(p.get("DriveLetter", "")).upper() == "C" or p.get("IsBoot") or p.get("IsSystem"):
                    return False, f"SAFETY BLOCK: Disk {disk_number} contains Windows System partition (C:)!"
        except Exception:
            pass

        return True, "Safe external USB drive"
    except Exception as e:
        return False, f"Verification failed: {e}"

def get_disk_list():
    """Retrieve ONLY verified external USB and removable disks using PowerShell"""
    ps_cmd = (
        "Get-Disk | "
        "Select-Object Number, FriendlyName, BusType, IsBoot, IsSystem, Size | "
        "ConvertTo-Json -Compress"
    )
    try:
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True, errors="ignore")
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        
        results = []
        for d in data:
            bus = str(d.get("BusType", "")).upper()
            # STRICT FILTER: MUST BE USB OR SD OR MMC
            if bus not in ["USB", "SD", "MMC"]:
                continue
            # NEVER ALLOW BOOT OR SYSTEM DISK
            if d.get("IsBoot") is True or d.get("IsSystem") is True:
                continue

            idx = d.get("Number")
            safe, reason = verify_safe_external_disk(idx)
            if not safe:
                continue

            model = d.get("FriendlyName", "USB Drive")
            size_raw = d.get("Size")
            size_gb = round(int(size_raw) / (1024**3), 1) if size_raw else 0
            
            results.append({
                "index": idx,
                "model": model,
                "size_gb": size_gb,
                "interface": bus,
                "is_usb": True,
                "display": f"External USB Disk {idx}: {model} ({size_gb} GB)"
            })
        return results
    except Exception as e:
        return [{"error": str(e)}]

def clean_disk_with_diskpart(disk_number):
    script = f"select disk {disk_number}\nattributes disk clear readonly\nclean\n"
    res = subprocess.run(["diskpart"], input=script, text=True, capture_output=True)
    time.sleep(1.5)

def download_image_progress():
    global flash_state
    os.makedirs(CACHE_DIR, exist_ok=True)
    if os.path.exists(ZIP_CACHE_PATH) and os.path.getsize(ZIP_CACHE_PATH) > 100 * 1024 * 1024:
        flash_state["message"] = "Cached TeslaUSB image verified."
        return ZIP_CACHE_PATH

    flash_state["status"] = "downloading"
    flash_state["message"] = "Downloading official TeslaUSB image from GitHub..."

    req = urllib.request.Request(IMAGE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(ZIP_CACHE_PATH, "wb") as f:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        start_time = time.time()
        chunk_size = 1024 * 1024

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            elapsed = max(0.1, time.time() - start_time)
            speed_mb = (downloaded / (1024 * 1024)) / elapsed
            pct = round((downloaded / total_size * 100), 1) if total_size > 0 else 0
            flash_state["progress"] = pct
            flash_state["speed"] = f"{speed_mb:.1f} MB/s"
            flash_state["message"] = f"Downloading image: {downloaded // (1024*1024)} / {total_size // (1024*1024)} MB"

    return ZIP_CACHE_PATH

def flash_worker(disk_number, config_content):
    global flash_state
    try:
        # ABSOLUTE SAFETY GUARD: Verify target is strictly an external USB drive
        safe, reason = verify_safe_external_disk(disk_number)
        if not safe:
            raise PermissionError(f"SAFETY ABORT: {reason}")

        flash_state["status"] = "downloading"
        flash_state["progress"] = 0.0
        flash_state["error"] = None
        
        # Step 1: Download
        zip_path = download_image_progress()

        # Step 2: Prepare disk
        flash_state["status"] = "flashing"
        flash_state["message"] = f"Preparing target disk (PhysicalDrive{disk_number})..."
        clean_disk_with_diskpart(disk_number)

        # Step 3: Open zip & raw disk
        zf = zipfile.ZipFile(zip_path, "r")
        img_names = [n for n in zf.namelist() if n.endswith(".img")]
        if not img_names:
            raise ValueError("No .img file found inside zip!")
        img_name = img_names[0]
        total_bytes = zf.getinfo(img_name).file_size

        drive_path = f"\\\\.\\PHYSICALDRIVE{disk_number}"
        handle = CreateFileW(
            drive_path,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None
        )

        if handle == -1 or handle == 0:
            err = ctypes.GetLastError()
            raise PermissionError(f"Could not open {drive_path}. Access Denied (Error {err}). Please run server as Administrator.")

        buffer_size = 4 * 1024 * 1024
        written = 0
        start_time = time.time()

        try:
            with zf.open(img_name, "r") as img_stream:
                bytes_written = wintypes.DWORD(0)
                while True:
                    chunk = img_stream.read(buffer_size)
                    if not chunk:
                        break
                    rem = len(chunk) % 512
                    if rem != 0:
                        chunk += b'\x00' * (512 - rem)

                    success = WriteFile(handle, chunk, len(chunk), ctypes.byref(bytes_written), None)
                    if not success:
                        raise IOError(f"Write error at byte {written}. Code: {ctypes.GetLastError()}")

                    written += len(chunk)
                    elapsed = max(0.1, time.time() - start_time)
                    speed_mb = (written / (1024 * 1024)) / elapsed
                    pct = min(100.0, round((written / total_bytes) * 100, 1))

                    flash_state["progress"] = pct
                    flash_state["speed"] = f"{speed_mb:.1f} MB/s"
                    flash_state["message"] = f"Writing raw image: {written // (1024*1024)} / {total_bytes // (1024*1024)} MB"
        finally:
            CloseHandle(handle)

        # Step 4: Configure
        flash_state["status"] = "configuring"
        flash_state["message"] = "Rescanning partitions and locating 'boot' drive..."
        time.sleep(2)
        subprocess.run(["diskpart"], input=f"select disk {disk_number}\nrescan\nselect partition 1\nassign\n", text=True, capture_output=True)
        time.sleep(3)

        # Find boot letter
        ps_cmd = (
            f"Get-Partition -DiskNumber {disk_number} | "
            "Where-Object { $_.DriveLetter } | "
            "Select-Object DiskNumber, PartitionNumber, DriveLetter | "
            "ConvertTo-Json -Compress"
        )
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True, errors="ignore")
        boot_letter = None
        try:
            parts = json.loads(out)
            if isinstance(parts, dict):
                parts = [parts]
            for p in parts:
                letter = p.get("DriveLetter")
                if letter:
                    boot_letter = letter
                    break
        except:
            pass

        if not boot_letter:
            import string
            for l in string.ascii_uppercase:
                candidate = f"{l}:\\"
                if os.path.exists(os.path.join(candidate, "config.txt")) or os.path.exists(os.path.join(candidate, "cmdline.txt")):
                    boot_letter = l
                    break

        if not boot_letter:
            raise RuntimeError("Flashed successfully, but Windows did not mount the 'boot' partition. Please reinsert card.")

        boot_path = f"{boot_letter.upper()}:\\"
        conf_dest = os.path.join(boot_path, "teslausb_setup_variables.conf")
        with open(conf_dest, "w", newline="\n", encoding="utf-8") as f:
            f.write(config_content)

        flash_state["status"] = "complete"
        flash_state["progress"] = 100.0
        flash_state["message"] = f"✓ Complete! Wrote configuration to {boot_path}teslausb_setup_variables.conf."

    except Exception as e:
        flash_state["status"] = "error"
        flash_state["error"] = str(e)
        flash_state["message"] = f"Error: {e}"

def get_network_shares():
    r"""Retrieve Windows mapped network connections (e.g. Y: -> \\GONZSERG00\TeslaCam)"""
    ps_cmd = (
        "Get-CimInstance Win32_NetworkConnection | "
        "Select-Object LocalName, RemoteName, RemotePath, Status | "
        "ConvertTo-Json -Compress"
    )
    shares = []
    try:
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True, errors="ignore")
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        for conn in data:
            local = conn.get("LocalName", "")
            remote = conn.get("RemoteName", "") or conn.get("RemotePath", "")
            unc = re.match(r'^[\\/]{2}([^/\\:]+)[\/\\]+([^\\\/].*)$', remote)
            if unc:
                shares.append({
                    "letter": local,
                    "remote": remote,
                    "server": unc.group(1),
                    "share": unc.group(2).replace('\\', '/').rstrip('/'),
                    "display": f"{local} ({remote})" if local else remote
                })
    except Exception:
        pass
    return shares

class StudioHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STUDIO_DIR, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/api/network_shares":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = json.dumps({"shares": get_network_shares()}).encode("utf-8")
            self.wfile.write(data)
            return

        if self.path == "/api/disks":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = json.dumps({"disks": get_disk_list(), "is_admin": is_admin()}).encode("utf-8")
            self.wfile.write(data)
            return

        if self.path == "/api/flash_status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = json.dumps(flash_state).encode("utf-8")
            self.wfile.write(data)
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/flash":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                payload = json.loads(body.decode("utf-8"))
                disk_idx = int(payload.get("diskIndex"))
                config_str = payload.get("config", "")

                if not is_admin():
                    raise PermissionError("Server is not running with Administrator privileges. Please restart with Run as Administrator.")

                # Start worker in background thread
                t = threading.Thread(target=flash_worker, args=(disk_idx, config_str), daemon=True)
                t.start()

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
            return

        self.send_error(404)

def run():
    print("=" * 60)
    print(" 🚗  TeslaUSB Setup Studio Web Server")
    print(f"     Running on: http://localhost:{PORT}")
    print(f"     Admin Privileges: {'YES ✓' if is_admin() else 'NO (Flashing requires Admin)'}")
    print("=" * 60)
    
    server_address = ("127.0.0.1", PORT)
    httpd = socketserver.TCPServer(server_address, StudioHandler)
    
    # Open default browser
    webbrowser.open(f"http://localhost:{PORT}/")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")

if __name__ == "__main__":
    run()


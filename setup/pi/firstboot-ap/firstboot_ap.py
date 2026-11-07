#!/usr/bin/env python3
"""
TeslaUSB First-Boot Fallback Captive Portal Server
Provides zero-friction onboarding when WiFi is unavailable or setup variables are missing.
Runs on standard Python 3 with zero external dependencies.
"""

import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse

PORT = 80
PORTAL_DIR = os.path.dirname(os.path.abspath(__file__))
SETUP_LOG_FILE = "/teslausb/teslausb-headless-setup.log"
TARGET_CONF_FILE = "/root/teslausb_setup_variables.conf"

def bash_quote(val):
    """Safely escape bash variables"""
    if val is None:
        return "''"
    s = str(val)
    if re.match(r'^[a-zA-Z0-9_\-\.\/]+$', s):
        return s
    if "'" not in s:
        return f"'{s}'"
    escaped = s.replace('\\', '\\\\').replace("'", "\\'")
    return f"$'{escaped}'"

def scan_wifi_networks():
    """Scan for local wireless SSIDs using nmcli or iwlist"""
    networks = []
    seen = set()
    
    # Try nmcli first
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "dev", "wifi", "list", "--rescan", "yes"],
            stderr=subprocess.DEVNULL,
            timeout=8
        ).decode("utf-8", errors="ignore")
        for line in out.strip().split("\n"):
            parts = line.split(":")
            if len(parts) >= 1 and parts[0].strip():
                ssid = parts[0].strip()
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    signal = f"{parts[1]}%" if len(parts) > 1 and parts[1] else ""
                    networks.append({"ssid": ssid, "signal": signal})
        if networks:
            return networks
    except Exception:
        pass

    # Fallback to iwlist
    try:
        out = subprocess.check_output(
            ["iwlist", "wlan0", "scan"],
            stderr=subprocess.DEVNULL,
            timeout=8
        ).decode("utf-8", errors="ignore")
        for line in out.split("\n"):
            match = re.search(r'ESSID:"([^"]+)"', line)
            if match:
                ssid = match.group(1).strip()
                if ssid and ssid not in seen:
                    seen.add(ssid)
                    networks.append({"ssid": ssid, "signal": ""})
    except Exception:
        pass

    return networks

class CaptivePortalHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Keep console clean
        pass

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        # Captive Portal detection probes for iOS, Android, Windows
        captive_probes = [
            "/generate_204", "/gen_204", "/hotspot-detect.html",
            "/ncsi.txt", "/connecttest.txt", "/canonical.html"
        ]

        host = self.headers.get("Host", "")
        # If client is requesting an external host or captive probe, redirect to portal root
        if any(probe in path for probe in captive_probes) or (host and not host.startswith("192.168.4.1") and not host.startswith("localhost")):
            self.send_response(302)
            self.send_header("Location", "http://192.168.4.1/")
            self.end_headers()
            return

        if path == "/" or path == "/index.html":
            self.serve_portal_html()
            return

        if path == "/api/scan_wifi":
            self.handle_scan_wifi()
            return

        if path == "/api/setup_log":
            self.handle_setup_log()
            return

        if path == "/api/status":
            self.handle_status()
            return

        # Serve static files from PORTAL_DIR if needed
        super().do_GET()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        path = url.path

        if path == "/api/apply_and_start":
            self.handle_apply_and_start()
            return

        self.send_error(404, "Not Found")

    def serve_portal_html(self):
        portal_path = os.path.join(PORTAL_DIR, "setup_portal.html")
        if os.path.exists(portal_path):
            with open(portal_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"TeslaUSB Setup Portal")

    def handle_scan_wifi(self):
        networks = scan_wifi_networks()
        data = json.dumps({"networks": networks}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_setup_log(self):
        content = b""
        if os.path.exists(SETUP_LOG_FILE):
            try:
                with open(SETUP_LOG_FILE, "rb") as f:
                    f.seek(max(0, os.path.getsize(SETUP_LOG_FILE) - 10000))
                    content = f.read()
            except Exception as e:
                content = str(e).encode("utf-8")
        else:
            content = b"Waiting for setup initialization..."

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_status(self):
        finished = os.path.exists("/teslausb/TESLAUSB_SETUP_FINISHED")
        started = os.path.exists("/teslausb/TESLAUSB_SETUP_STARTED")
        data = json.dumps({"started": started, "finished": finished}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_apply_and_start(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len)
        try:
            payload = json.loads(post_body.decode("utf-8"))
            ssid = payload.get("ssid", "").strip()
            wifi_pass = payload.get("wifiPass", "")
            archive_sys = payload.get("archiveSystem", "cifs")

            if not ssid:
                raise ValueError("WiFi SSID is required.")

            # Make root fs writable if helper exists
            if os.path.exists("/root/bin/remountfs_rw"):
                subprocess.run(["/root/bin/remountfs_rw"], check=False)

            # Build config lines
            lines = [
                "#####################################################################",
                "# TESLAUSB CONFIGURATION FILE (Configured via First-Boot Hotspot)",
                f"# Generated {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "#####################################################################",
                "",
                "# === WiFi Settings ===",
                f"export SSID={bash_quote(ssid)}",
                f"export WIFIPASS={bash_quote(wifi_pass)}",
                "",
                "# === Drive Sizes ===",
                "export CAM_SIZE=40G",
                "",
                "# === Archive System ===",
                f"export ARCHIVE_SYSTEM={bash_quote(archive_sys)}",
            ]

            if archive_sys == "cifs":
                cifs_server = payload.get("cifsServer", "")
                cifs_share = payload.get("cifsShare", "TeslaCam")
                cifs_user = payload.get("cifsUser", "")
                cifs_pass = payload.get("cifsPass", "")
                lines.extend([
                    f"export ARCHIVE_SERVER={bash_quote(cifs_server)}",
                    f"export SHARE_NAME={bash_quote(cifs_share)}",
                    f"export SHARE_USER={bash_quote(cifs_user)}",
                    f"export SHARE_PASSWORD={bash_quote(cifs_pass)}",
                ])

            # Write config file
            conf_str = "\n".join(lines) + "\n"
            os.makedirs(os.path.dirname(TARGET_CONF_FILE), exist_ok=True)
            with open(TARGET_CONF_FILE, "w") as f:
                f.write(conf_str)

            # Mark trigger file
            with open("/teslausb/WIFI_SETUP_VIA_PORTAL", "w") as f:
                f.write("configured\n")

            # Spawn setup execution in separate background thread
            def run_setup_transition():
                time.sleep(2)
                # Call /etc/rc.local or trigger setup
                subprocess.Popen(["/bin/bash", "/etc/rc.local"])

            threading.Thread(target=run_setup_transition, daemon=True).start()

            resp = json.dumps({"success": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

        except Exception as e:
            err = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err)))
            self.end_headers()
            self.wfile.write(err)

def run():
    print(f"Starting TeslaUSB Captive Portal on port {PORT}...")
    server_address = ("", PORT)
    httpd = socketserver.TCPServer(server_address, CaptivePortalHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run()


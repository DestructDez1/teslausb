#!/usr/bin/env python3
"""
TeslaUSB 1-Click All-in-One Flasher & Automated Configurator
Downloads the official image, flashes directly to the target SD card/USB drive,
and automatically writes the pre-configured teslausb_setup_variables.conf.
Zero external dependencies.
"""

import ctypes
from ctypes import wintypes
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.request
import zipfile

# Constants & Win32 API definitions
IMAGE_URL = "https://github.com/marcone/teslausb/releases/download/v3.2/teslausb-20211106-2.zip"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
ZIP_CACHE_PATH = os.path.join(CACHE_DIR, "teslausb-image.zip")

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

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

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def bash_quote(val):
    if val is None:
        return "''"
    s = str(val)
    if re.match(r'^[a-zA-Z0-9_\-\.\/]+$', s):
        return s
    if "'" not in s:
        return f"'{s}'"
    escaped = s.replace('\\', '\\\\').replace("'", "\\'")
    return f"$'{escaped}'"

def get_current_wifi_ssid():
    """Attempt to detect currently connected WiFi SSID on Windows"""
    try:
        out = subprocess.check_output(["netsh", "wlan", "show", "interfaces"], text=True, errors="ignore")
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("SSID") and ":" in line:
                val = line.split(":", 1)[1].strip()
                if val and val != "None":
                    return val
    except:
        pass
    return ""

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

def list_drives():
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
                "Index": idx,
                "Model": model,
                "Size": size_raw,
                "SizeGB": size_gb,
                "InterfaceType": bus
            })
        return results
    except Exception as e:
        return []

def prompt_input(prompt, default=None, is_secret=False):
    p = f"{prompt} [{default}]: " if default is not None else f"{prompt}: "
    while True:
        try:
            val = input(p).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(1)
        if not val and default is not None:
            return default
        if val or default is not None:
            return val

def download_image():
    """Download the official TeslaUSB prebuilt image with a progress bar"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    if os.path.exists(ZIP_CACHE_PATH) and os.path.getsize(ZIP_CACHE_PATH) > 100 * 1024 * 1024:
        print(f"✓ Found cached TeslaUSB image ({os.path.getsize(ZIP_CACHE_PATH) // (1024*1024)} MB). Skipping download.")
        return ZIP_CACHE_PATH

    print(f"📥 Downloading official TeslaUSB image...")
    print(f"   URL: {IMAGE_URL}")

    req = urllib.request.Request(IMAGE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(ZIP_CACHE_PATH, "wb") as f:
        total_size = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        start_time = time.time()
        chunk_size = 1024 * 1024 # 1 MB

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            f.write(chunk)
            downloaded += len(chunk)
            elapsed = max(0.1, time.time() - start_time)
            speed_mb = (downloaded / (1024 * 1024)) / elapsed
            pct = (downloaded / total_size * 100) if total_size > 0 else 0
            bar = "█" * int(pct // 2.5) + " " * (40 - int(pct // 2.5))
            sys.stdout.write(f"\r   [{bar}] {pct:.1f}% ({downloaded // (1024*1024)}/{total_size // (1024*1024)} MB @ {speed_mb:.1f} MB/s) ")
            sys.stdout.flush()

    print("\n✓ Download completed successfully!")
    return ZIP_CACHE_PATH

def clean_disk_with_diskpart(disk_number):
    """Run diskpart script to clean the target disk before writing"""
    script = f"select disk {disk_number}\nattributes disk clear readonly\nclean\n"
    res = subprocess.run(["diskpart"], input=script, text=True, capture_output=True)
    if res.returncode != 0:
        print(f"Warning during diskpart clean: {res.stderr}")
    time.sleep(1.5)

def flash_image_to_disk(zip_path, disk_number):
    """Stream raw image sectors from ZIP directly to PhysicalDrive"""
    safe, reason = verify_safe_external_disk(disk_number)
    if not safe:
        raise PermissionError(f"SAFETY ABORT: {reason}")

    print(f"\n⚡ Preparing target disk (PhysicalDrive{disk_number})...")
    clean_disk_with_diskpart(disk_number)

    # Open ZIP and find image
    zf = zipfile.ZipFile(zip_path, "r")
    img_names = [n for n in zf.namelist() if n.endswith(".img")]
    if not img_names:
        raise ValueError("No .img file found inside downloaded zip!")
    img_name = img_names[0]
    img_info = zf.getinfo(img_name)
    total_uncompressed_bytes = img_info.file_size
    print(f"   Image found: {img_name} ({total_uncompressed_bytes // (1024*1024)} MB)")

    # Open PhysicalDrive handle
    drive_path = f"\\\\.\\PHYSICALDRIVE{disk_number}"
    print(f"   Opening {drive_path} for raw block writing...")
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
        raise PermissionError(f"Failed to open {drive_path} for writing. Error code: {err}. Please ensure no Explorer window is viewing the drive.")

    try:
        print(f"🚀 Flashing raw image to PhysicalDrive{disk_number}...")
        buffer_size = 4 * 1024 * 1024 # 4 MB sector-aligned
        written_total = 0
        start_time = time.time()

        with zf.open(img_name, "r") as img_stream:
            bytes_written = wintypes.DWORD(0)
            while True:
                chunk = img_stream.read(buffer_size)
                if not chunk:
                    break

                # Ensure sector alignment (pad with 0s if last chunk is not a multiple of 512)
                rem = len(chunk) % 512
                if rem != 0:
                    chunk += b'\x00' * (512 - rem)

                chunk_len = len(chunk)
                success = WriteFile(
                    handle,
                    chunk,
                    chunk_len,
                    ctypes.byref(bytes_written),
                    None
                )

                if not success:
                    err = ctypes.GetLastError()
                    raise IOError(f"WriteFile failed at byte {written_total}. Win32 Error: {err}")

                written_total += len(chunk)
                elapsed = max(0.1, time.time() - start_time)
                speed_mb = (written_total / (1024 * 1024)) / elapsed
                pct = min(100.0, (written_total / total_uncompressed_bytes) * 100)
                bar = "█" * int(pct // 2.5) + " " * (40 - int(pct // 2.5))
                sys.stdout.write(f"\r   [{bar}] {pct:.1f}% ({written_total // (1024*1024)} MB @ {speed_mb:.1f} MB/s) ")
                sys.stdout.flush()

        print("\n✓ Raw disk writing completed successfully!")
    finally:
        CloseHandle(handle)

def mount_and_write_config(disk_number, config_content):
    """Rescan disk, find FAT32 boot partition, and write teslausb_setup_variables.conf"""
    print(f"\n📂 Rescanning partitions on PhysicalDrive{disk_number}...")
    subprocess.run(["diskpart"], input=f"select disk {disk_number}\nrescan\nselect partition 1\nassign\n", text=True, capture_output=True)
    time.sleep(3)

    # Find drive letter using PowerShell
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
        # Fallback check standard drive letters for typical Pi boot files
        import string
        for letter in string.ascii_uppercase:
            candidate = f"{letter}:\\"
            if os.path.exists(os.path.join(candidate, "config.txt")) or os.path.exists(os.path.join(candidate, "cmdline.txt")):
                boot_letter = letter
                break

    if not boot_letter:
        print("⚠️ Windows did not automatically assign a drive letter to the boot partition.")
        boot_letter = prompt_input("Please enter the drive letter shown in File Explorer for the 'boot' drive (e.g. E)")

    boot_path = f"{boot_letter.upper()}:\\" if not boot_letter.endswith(":\\") else boot_letter.upper()
    print(f"✓ Detected boot partition at: {boot_path}")

    conf_dest = os.path.join(boot_path, "teslausb_setup_variables.conf")
    with open(conf_dest, "w", newline="\n", encoding="utf-8") as f:
        f.write(config_content)

    print(f"✓ Wrote pre-configured {conf_dest} (Verified ✓)")

def parse_network_share(p):
    """Parse Windows UNC, SMB or simple share names"""
    p = p.strip()
    unc = re.match(r'^[\\\/]{2}([^\/\\:]+)[\/\\]+([^\\\/].*)$', p)
    if unc:
        return unc.group(1), unc.group(2).replace('\\', '/').rstrip('/')
    smb = re.match(r'^(?:smb|cifs):\/\/(?:([^:@]+)(?::([^@]+))?@)?([^\/:]+)(?::\d+)?\/(.+)$', p, re.IGNORECASE)
    if smb:
        return smb.group(3), smb.group(4).rstrip('/')
    return None, None

def main():
    print("=" * 70)
    print(" 🚗  TESLAUSB ALL-IN-ONE FLASHER & AUTOMATED CONFIGURATOR")
    print("     Flash image and configure settings in ONE seamless step")
    print("=" * 70)

    if not is_admin():
        print("\n❌ Error: This tool requires Administrator privileges to write to raw physical drives.")
        print("Please right-click '1-Click-Flash-And-Setup.bat' and select 'Run as Administrator'.")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # 1. Detect connected disks
    print("\n🔍 Detecting connected storage drives...")
    drives = list_drives()
    usb_drives = [d for d in drives if d.get("InterfaceType") == "USB" or (d.get("MediaType") and "Removable" in d.get("MediaType"))]

    if not drives:
        print("❌ No storage drives found. Please plug in your MicroSD card or USB drive.")
        input("Press Enter to exit...")
        sys.exit(1)

    print("\nAvailable USB / Removable Drives:")
    candidates = usb_drives if usb_drives else drives
    for idx, d in enumerate(candidates, 1):
        num = d.get("Index")
        model = d.get("Model", "Unknown")
        size_raw = d.get("Size")
        size_gb = f"{int(size_raw) // (1024**3)} GB" if size_raw else "Unknown Size"
        iface = d.get("InterfaceType", "")
        print(f"  [{idx}] Disk {num}: {model} ({size_gb}) [{iface}]")

    print("  [0] Refresh drive list")
    
    choice_idx = prompt_input("\nSelect the drive number to flash", default="1")
    if choice_idx == "0":
        return main()

    try:
        selected_drive = candidates[int(choice_idx) - 1]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return main()

    target_disk_num = selected_drive.get("Index")
    model_name = selected_drive.get("Model", "Unknown")
    size_gb = f"{int(selected_drive.get('Size', 0)) // (1024**3)} GB" if selected_drive.get('Size') else ""

    print("\n" + "!" * 70)
    print(f" ⚠️  WARNING: ALL DATA ON DISK {target_disk_num} ({model_name} {size_gb}) WILL BE WIPED!")
    print("!" * 70)
    confirm = prompt_input(f"Type 'YES' to confirm flashing to Disk {target_disk_num}")
    if confirm != "YES":
        print("Operation aborted. No changes made.")
        sys.exit(0)

    # 2. Configure Settings
    print("\n--- 2. Wireless Network Configuration ---")
    detected_wifi = get_current_wifi_ssid()
    ssid = prompt_input("Home WiFi Network Name (SSID)", default=detected_wifi if detected_wifi else None)
    wifi_pass = prompt_input("Home WiFi Password")

    print("\n--- 3. Archive / Backup Destination ---")
    print("Enter your Windows share / NAS path (e.g. \\\\192.168.1.50\\TeslaCam or smb://mynas/TeslaCam):")
    raw_share = prompt_input("Share Path", default="\\\\192.168.1.50\\TeslaCam")
    srv, shr = parse_network_share(raw_share)
    if srv and shr:
        server = srv
        share_name = shr
        print(f"   ✓ Auto-parsed: Server = {server} | Share = {share_name}")
    else:
        server = prompt_input("Archive Server IP or Hostname", default="192.168.1.50")
        share_name = prompt_input("Share Folder Name", default="TeslaCam")

    share_user = prompt_input("Share Username (leave blank if unauthenticated)", default="tesla")
    share_pass = prompt_input("Share Password") if share_user else ""

    cam_size = prompt_input("\nTeslaCam Drive Size [Dashcam & Sentry]", default="40G")

    # Build Configuration Content
    lines = [
        "#####################################################################",
        "# TESLAUSB CONFIGURATION FILE",
        "# Generated automatically by TeslaUSB 1-Click Flasher",
        "#####################################################################",
        "",
        "# === WiFi Settings ===",
        f"export SSID={bash_quote(ssid)}",
        f"export WIFIPASS={bash_quote(wifi_pass)}",
        "",
        "# === Drive Partition Sizes ===",
        f"export CAM_SIZE={cam_size}",
        "",
        "# === Archive Destination ===",
        "export ARCHIVE_SYSTEM=cifs",
        f"export ARCHIVE_SERVER={bash_quote(server)}",
        f"export SHARE_NAME={bash_quote(share_name)}",
        f"export SHARE_USER={bash_quote(share_user)}",
        f"export SHARE_PASSWORD={bash_quote(share_pass)}",
        ""
    ]
    config_content = "\n".join(lines)

    # 3. Execution
    print("\n" + "=" * 70)
    print(" 🚀  STARTING 1-STEP FLASH & CONFIGURE PROCESS")
    print("=" * 70)

    # Step A: Download image
    zip_path = download_image()

    # Step B: Flash raw image to disk
    flash_image_to_disk(zip_path, target_disk_num)

    # Step C: Mount and write config
    mount_and_write_config(target_disk_num, config_content)

    print("\n" + "=" * 70)
    print(" 🎉  COMPLETE! YOUR TESLAUSB DRIVE IS FULLY PREPARED!")
    print("=" * 70)
    print(" What's next:")
    print("   1. Safely unplug your MicroSD card / USB drive from this computer.")
    print("   2. Insert it into your Raspberry Pi.")
    print("   3. Plug the Pi into power or your Tesla.")
    print("   4. Setup runs automatically! Access dashboard at: http://teslausb.local")
    print("=" * 70)
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()


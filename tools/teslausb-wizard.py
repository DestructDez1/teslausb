#!/usr/bin/env python3
"""
TeslaUSB Interactive Setup Wizard & SD Card Configurator (CLI)
Cross-platform: Windows, macOS, Linux
Zero dependencies (standard Python 3)
"""

import argparse
import os
import platform
import re
import sys

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

def detect_sd_card_boot():
    """Detect potential SD card boot partition paths"""
    system = platform.system()
    candidates = []

    if system == "Windows":
        # Check standard removable drive letters
        import string
        for letter in string.ascii_uppercase:
            path = f"{letter}:\\"
            if os.path.exists(path):
                # Look for typical boot partition markers
                if any(os.path.exists(os.path.join(path, f)) for f in ["config.txt", "cmdline.txt", "issue.txt", "bootcode.bin"]):
                    candidates.append(path)
    elif system == "Darwin": # macOS
        vol_base = "/Volumes"
        if os.path.exists(vol_base):
            for d in os.listdir(vol_base):
                path = os.path.join(vol_base, d)
                if os.path.isdir(path) and ("boot" in d.lower() or os.path.exists(os.path.join(path, "config.txt"))):
                    candidates.append(path)
    else: # Linux
        for base in ["/media", "/run/media", "/mnt"]:
            if os.path.exists(base):
                for root, dirs, files in os.walk(base):
                    if "config.txt" in files:
                        candidates.append(root)
                        break

    return candidates

def prompt_input(prompt, default=None, validator=None):
    prompt_str = f"{prompt} [{default}]: " if default is not None else f"{prompt}: "
    while True:
        try:
            val = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(1)
        if not val and default is not None:
            return default
        if validator:
            valid, err = validator(val)
            if not valid:
                print(f"  ⚠️  Error: {err}")
                continue
        return val

def prompt_bool(prompt, default=True):
    choice = "Y/n" if default else "y/N"
    while True:
        try:
            val = input(f"{prompt} ({choice}): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nSetup cancelled.")
            sys.exit(1)
        if not val:
            return default
        if val in ["y", "yes"]:
            return True
        if val in ["n", "no"]:
            return False

def validate_existing(file_path):
    print(f"\n🔍 Validating configuration file: {file_path}")
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    issues = []
    vars_found = {}
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r'^export\s+([A-Za-z0-9_]+)=(.*)$', line)
        if not m:
            if line.startswith("export"):
                issues.append(f"Line {i}: Malformed export syntax: {line}")
            continue
        var, val = m.group(1), m.group(2).strip()
        vars_found[var] = val

        # Check unclosed quotes
        if (val.startswith("'") and not val.endswith("'")) or (val.startswith('"') and not val.endswith('"')):
            issues.append(f"Line {i}: Unclosed quotes in {var}")

    if "SSID" not in vars_found:
        issues.append("Warning: SSID is not defined.")
    if "WIFIPASS" not in vars_found:
        issues.append("Warning: WIFIPASS is not defined.")

    arch = vars_found.get("ARCHIVE_SYSTEM", "cifs")
    if arch == "cifs":
        if "ARCHIVE_SERVER" not in vars_found:
            issues.append("Error: ARCHIVE_SYSTEM is cifs but ARCHIVE_SERVER is missing.")
        if "SHARE_NAME" not in vars_found:
            issues.append("Error: SHARE_NAME is missing.")
        if vars_found.get("SHARE_NAME", "").startswith("\\"):
            issues.append("Error: SHARE_NAME should not begin with backslash (\\). Use standard share name.")

    if not issues:
        print("✅ Configuration is 100% syntactically valid!")
        return True
    else:
        print(f"⚠️ Found {len(issues)} issue(s):")
        for iss in issues:
            print(f"  - {iss}")
        return False

def main():
    parser = argparse.ArgumentParser(description="TeslaUSB Setup Wizard & Configurator")
    parser.add_argument("--validate", help="Validate an existing configuration file", metavar="FILE")
    parser.add_argument("--out", help="Output file path (default: teslausb_setup_variables.conf)")
    args = parser.parse_args()

    if args.validate:
        validate_existing(args.validate)
        sys.exit(0)

    print("=" * 65)
    print(" 🚗  TeslaUSB Setup Wizard (Interactive CLI Configurator)")
    print("=" * 65)

    # 1. Target output path
    sd_candidates = detect_sd_card_boot()
    default_out = "teslausb_setup_variables.conf"
    if sd_candidates:
        print(f"\nDetected possible SD card boot partition at: {sd_candidates[0]}")
        if prompt_bool("Write configuration directly to this SD card?", default=True):
            default_out = os.path.join(sd_candidates[0], "teslausb_setup_variables.conf")

    out_file = args.out or prompt_input("\nTarget output file path", default=default_out)

    # 2. Hardware
    print("\n--- 1. Hardware Selection ---")
    print("1) Raspberry Pi Zero 2 W")
    print("2) Raspberry Pi 4 Model B (Recommended)")
    print("3) Raspberry Pi 5")
    print("4) Other / Generic SBC")
    hw_choice = prompt_input("Select hardware", default="2")

    # 3. WiFi
    print("\n--- 2. Wireless Network Settings ---")
    ssid = prompt_input("Home WiFi SSID (Network Name)")
    wifi_pass = prompt_input("Home WiFi Password")
    hostname = prompt_input("TeslaUSB Hostname", default="teslausb")

    # 4. Storage Partitions
    print("\n--- 3. Storage Drive Allocation ---")
    cam_size = prompt_input("TeslaCam partition size (Dashcam & Sentry)", default="40G")
    include_music = prompt_bool("Include Music Drive partition?", default=False)
    music_size = prompt_input("Music partition size", default="16G") if include_music else None
    include_lightshow = prompt_bool("Include Custom LightShow partition?", default=False)
    lightshow_size = prompt_input("LightShow partition size", default="2G") if include_lightshow else None

    # 5. Archive
    print("\n--- 4. Archiving Destination ---")
    print("1) Windows Share / SMB / NAS (CIFS) [Recommended]")
    print("2) Cloud Storage (Rclone - Google Drive / OneDrive)")
    print("3) Linux / SSH Server (RSync)")
    print("4) Network File System (NFS)")
    print("5) Standalone / Web Only (No server)")
    arch_choice = prompt_input("Select storage target", default="1")

    arch_system = "cifs"
    cifs_server, cifs_share, cifs_user, cifs_pass = None, None, None, None
    rclone_drive, rclone_path = None, None
    rsync_server, rsync_user, rsync_path = None, None, None
    nfs_server, nfs_share = None, None

    if arch_choice == "1":
        arch_system = "cifs"
        cifs_server = prompt_input("CIFS Server IP or Hostname (e.g. 192.168.1.50)")
        cifs_share = prompt_input("CIFS Share Name (e.g. TeslaCam)")
        cifs_user = prompt_input("CIFS Username", default="tesla")
        cifs_pass = prompt_input("CIFS Password")
    elif arch_choice == "2":
        arch_system = "rclone"
        rclone_drive = prompt_input("Rclone remote name (e.g. gdrive)")
        rclone_path = prompt_input("Rclone folder path (e.g. TeslaCam)")
    elif arch_choice == "3":
        arch_system = "rsync"
        rsync_server = prompt_input("RSync Server Hostname/IP")
        rsync_user = prompt_input("RSync SSH Username", default="pi")
        rsync_path = prompt_input("RSync Server Path (e.g. /mnt/storage/TeslaCam)")
    elif arch_choice == "4":
        arch_system = "nfs"
        nfs_server = prompt_input("NFS Server IP")
        nfs_share = prompt_input("NFS Export Path (e.g. /volume1/TeslaCam)")
    else:
        arch_system = "none"

    # 6. Notifications
    print("\n--- 5. Notifications (Optional) ---")
    discord_webhook = None
    if prompt_bool("Enable Discord Webhook notifications?", default=False):
        discord_webhook = prompt_input("Discord Webhook URL")

    # Generate Config
    lines = [
        "#####################################################################",
        "# TESLAUSB CONFIGURATION FILE",
        "# Generated by TeslaUSB Setup Wizard CLI",
        "#####################################################################",
        "",
        "# === WiFi Settings ===",
        f"export SSID={bash_quote(ssid)}",
        f"export WIFIPASS={bash_quote(wifi_pass)}",
    ]

    if hostname != "teslausb":
        lines.append(f"export TESLAUSB_HOSTNAME={bash_quote(hostname)}")

    lines.extend([
        "",
        "# === Drive Partition Sizes ===",
        f"export CAM_SIZE={cam_size}",
    ])

    if music_size:
        lines.append(f"export MUSIC_SIZE={music_size}")
    if lightshow_size:
        lines.append(f"export LIGHTSHOW_SIZE={lightshow_size}")

    lines.extend([
        "",
        "# === Archive Destination ===",
        f"export ARCHIVE_SYSTEM={arch_system}",
    ])

    if arch_system == "cifs":
        lines.extend([
            f"export ARCHIVE_SERVER={bash_quote(cifs_server)}",
            f"export SHARE_NAME={bash_quote(cifs_share)}",
            f"export SHARE_USER={bash_quote(cifs_user)}",
            f"export SHARE_PASSWORD={bash_quote(cifs_pass)}",
        ])
    elif arch_system == "rclone":
        lines.extend([
            f"export RCLONE_DRIVE={bash_quote(rclone_drive)}",
            f"export RCLONE_PATH={bash_quote(rclone_path)}",
        ])
    elif arch_system == "rsync":
        lines.extend([
            f"export RSYNC_SERVER={bash_quote(rsync_server)}",
            f"export RSYNC_USER={bash_quote(rsync_user)}",
            f"export RSYNC_PATH={bash_quote(rsync_path)}",
        ])
    elif arch_system == "nfs":
        lines.extend([
            f"export ARCHIVE_SERVER={bash_quote(nfs_server)}",
            f"export SHARE_NAME={bash_quote(nfs_share)}",
        ])

    if discord_webhook:
        lines.extend([
            "",
            "# === Notifications ===",
            f"export DISCORD_WEBHOOK_URL={bash_quote(discord_webhook)}"
        ])

    lines.append("")

    # Write file with Unix (LF) line endings
    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(out_file)), exist_ok=True)
    with open(out_file, "w", newline="\n", encoding="utf-8") as f:
        f.write(content)

    print("\n" + "=" * 65)
    print(f"🎉 SUCCESS! Configuration file generated:")
    print(f"📁 {os.path.abspath(out_file)}")
    print("=" * 65)
    print("Next steps:")
    print("  1. Ensure the SD card is flashed with the latest TeslaUSB image.")
    print("  2. Place 'teslausb_setup_variables.conf' in the SD card's 'boot' directory.")
    print("  3. Insert into Raspberry Pi and boot!")
    print("=" * 65)

if __name__ == "__main__":
    main()


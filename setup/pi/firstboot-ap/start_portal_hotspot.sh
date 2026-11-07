#!/bin/bash
# Starts the TeslaUSB First-Boot Fallback Hotspot and Captive Portal

SETUP_LOGFILE=/teslausb/teslausb-headless-setup.log

function log_msg () {
  echo "$( date ) : [SETUP-HOTSPOT] $1" >> "$SETUP_LOGFILE" || true
  echo "[SETUP-HOTSPOT] $1"
}

log_msg "Starting TeslaUSB Setup Hotspot (SSID: TeslaUSB-Setup)..."

# Find wireless interface
WLAN_IFACE=$(nmcli -t -f DEVICE,TYPE device status | grep ":wifi" | head -n 1 | cut -d: -f1)
if [ -z "$WLAN_IFACE" ]; then
  WLAN_IFACE="wlan0"
fi

# Ensure wifi is unblocked
rfkill unblock wifi &> /dev/null || true

# If NetworkManager is running
if systemctl --quiet is-enabled NetworkManager.service || systemctl --quiet is-active NetworkManager.service; then
  log_msg "Configuring AP via NetworkManager on $WLAN_IFACE"
  nmcli con delete TESLAUSB_SETUP_AP &> /dev/null || true
  nmcli con add type wifi ifname "$WLAN_IFACE" mode ap con-name TESLAUSB_SETUP_AP ssid "TeslaUSB-Setup" &> /dev/null || true
  nmcli con modify TESLAUSB_SETUP_AP 802-11-wireless-security.key-mgmt none &> /dev/null || true
  nmcli con modify TESLAUSB_SETUP_AP ipv4.addr "192.168.4.1/24" &> /dev/null || true
  nmcli con modify TESLAUSB_SETUP_AP ipv4.method shared &> /dev/null || true
  nmcli con modify TESLAUSB_SETUP_AP ipv6.method disabled &> /dev/null || true
  nmcli con up TESLAUSB_SETUP_AP &> /dev/null || true
fi

# Start python captive portal web server
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log_msg "Launching Captive Portal Web Server on port 80..."
python3 "$SCRIPT_DIR/firstboot_ap.py"


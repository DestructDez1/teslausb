# ⚡ TeslaUSB Quickstart Guide

TeslaUSB turns your Raspberry Pi into a smart, self-archiving USB drive for your Tesla. When plugged into your vehicle, it records Dashcam, Sentry Mode, and Track Mode footage while also serving music or light shows. When you return home and park within WiFi range, it automatically offloads and archives all your footage to your NAS, server, or cloud drive!

---

## 🛠️ Step 1: Hardware Essentials

| Component | Recommendation | Notes |
| :--- | :--- | :--- |
| **SBC** | **Raspberry Pi 4 (2GB/4GB)** or **Pi Zero 2 W** | Pi 4 offers fastest WiFi (5 GHz) & transfers. Pi Zero 2 W is compact. |
| **Storage** | **128 GB+ Endurance MicroSD** or **USB 3.0 SSD** | High-endurance cards (e.g. SanDisk High/Max Endurance or Samsung PRO Endurance) handle frequent video writing best. |
| **Cabling** | **Data + Power USB Cable** | **Pi Zero 2 W:** Connect to inner micro-USB data port.<br>**Pi 4 / 5:** USB-A to USB-C cable to the Pi's USB-C port. |
| **Port in Car** | **Data-capable USB Port** | Model 3/Y (2021+): Glovebox USB-A port supports data. Center console ports are often power-only. |

---

## 🚀 Step 2: Flash the TeslaUSB Image

1. Download the [Latest TeslaUSB Prebuilt Image](https://github.com/marcone/teslausb/releases/latest).
2. Download and open [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
3. Under **Operating System**, scroll down and click **Use custom**, then select the downloaded `.zip` or `.img` file.
4. Under **Storage**, choose your MicroSD card.
5. Click **Write**.

---

## ⚙️ Step 3: Configure with TeslaUSB Setup Studio (Foolproof)

Rather than hand-editing complex bash files and risking quotation errors or hidden Windows `.txt` file extensions, use **TeslaUSB Setup Studio**:

### Option A: Setup Studio Web App (Recommended)
1. Open [`setup-studio/index.html`](setup-studio/index.html) in Chrome or Edge (runs locally in your browser, completely offline).
2. Follow the visual wizard:
   - **Hardware & Partitions:** Select your drive size (e.g. 128 GB) and allocate space for Dashcam, Music, and LightShow.
   - **WiFi:** Enter your network name and password (special characters are automatically escaped).
   - **Archiving Target:** Choose your NAS (Synology, TrueNAS, Windows Share/CIFS), Cloud (Google Drive, OneDrive), or Linux SSH (RSync).
   - **Notifications:** Optional Discord or Telegram alerts.
3. Click **💾 Select SD Card & Write Config**:
   - Select your SD card's `boot` drive.
   - Studio writes `teslausb_setup_variables.conf` directly with guaranteed valid permissions and syntax!

### Option B: Interactive CLI Wizard
Run the Python CLI configurator from any terminal:
```bash
python tools/teslausb-wizard.py
```
To validate an existing configuration:
```bash
python tools/teslausb-wizard.py --validate path/to/teslausb_setup_variables.conf
```

---

## 📶 Step 4: First Boot & Fallback Hotspot

1. Eject the MicroSD card from your computer and insert it into your Raspberry Pi.
2. Connect the Pi to a USB power supply or your car's USB port.
3. **Automated Setup:** The Pi will boot, format partitions, connect to your WiFi, and finalize setup in ~5–10 minutes.
4. **Smart Hotspot Fallback:**
   - If WiFi fails to connect or credentials were unset, the Pi automatically broadcasts a hotspot: **`TeslaUSB-Setup`**.
   - Connect on your smartphone or laptop. The captive onboarding portal will open automatically at `http://192.168.4.1`.
   - Scan for your home WiFi, enter credentials, and watch live setup progress on your screen!

---

## 🎬 Step 5: View & Manage Footage

Once setup is complete and your Pi is connected to your network:
- Open your browser to `http://teslausb.local`
- Access the **🎬 Multi-Cam Player** at `http://teslausb.local/player/player.html` to watch synchronized Front, Back, Left, and Right camera streams with 2x2 grid view, synchronized scrubbing, and variable speed playback!

---

## 🔍 Troubleshooting Checklist

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **Tesla says "USB drive too slow" or drive not recognized** | Using power-only port or charge-only cable | Ensure you are using the glovebox port (on newer Teslas) and a certified high-speed data cable. On Pi Zero, use the inner micro-USB data port. |
| **Pi LED flashing continuously (Error Strobe)** | WiFi failed to connect or config syntax error | Connect to the `TeslaUSB-Setup` fallback hotspot to inspect logs, or validate your config using `python tools/teslausb-wizard.py --validate`. |
| **Share fails to mount** | Incorrect share path formatting | Share names should NOT start with `\\` or `/`. For example, use `TeslaCam` or `share/folder`, not `\\server\TeslaCam`. |
| **Can't access `teslausb.local`** | mDNS / Bonjour not resolving | Use the Pi's local IP address (found via your router's DHCP client list), or use the In-Car AP. |

---

### 💖 Credits & Acknowledgements
- **Marcone (@marcone)** — Upstream creator and maintainer of [marcone/teslausb](https://github.com/marcone/teslausb) and [teslausb-webui](https://github.com/marcone/teslausb-webui).
- **Cimryan (@cimryan)** — Original creator of [cimryan/teslausb](https://github.com/cimryan/teslausb).
- **The Tesla & Reddit Open-Source Community** — For testing, guides, and ongoing support.


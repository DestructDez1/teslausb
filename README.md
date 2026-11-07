# teslausb — Modernized Setup Studio & All-in-One Flasher

> **Fork & Attribution Notice**: This project is a community modernization and fork of the groundbreaking [marcone/teslausb](https://github.com/marcone/teslausb) project, originally created by [cimryan](https://github.com/cimryan/teslausb) from the original Reddit concept. All core OTG emulation, snapshotting, CIFS/rclone archiving, and gadget infrastructure are the work of **Marcone** and the upstream TeslaUSB contributors. 
> 
> This fork modernizes the onboarding experience by adding **Setup Studio** (an all-in-one web flasher and visual configurator), **strict drive safety protection**, **automatic network share detection**, a **synchronized 4-camera video player**, and a 1-click startup workflow to eliminate command-line barriers.

## Intro

Raspberry Pi and other [SBCs](## "Single Board Computers") can emulate a USB drive, so can act as a drive for your Tesla to write dashcam footage to. Because the SBC has full access to the emulated drive, it can:

- automatically copy the recordings to an archive server when you get home
- hold both dashcam recordings and music files
- automatically repair filesystem corruption produced by the Tesla's current failure to properly dismount the USB drives before cutting power to the USB ports
- serve up a web UI to view or download the recordings
- retain more than one hour of RecentClips (assuming large enough storage)

This video (not mine) has a nice overview of teslausb and how to install it:

[![teslausb intro and installation](http://img.youtube.com/vi/ETs6r1vKTO8/0.jpg)](http://www.youtube.com/watch?v=ETs6r1vKTO8 "teslausb intro and installation")

If you are interested in having more detailed information about how TeslaUsb works, have a look into the [wiki](https://github.com/marcone/teslausb/wiki).

## What's New & Easier to Set Up

- **[TeslaUSB Setup Studio](setup-studio/index.html)**: Interactive, web-based visual configurator that calculates storage partitions, safely escapes bash syntax for passwords and SSIDs, and writes `teslausb_setup_variables.conf` **directly to your SD card** using the Web File System Access API — zero risk of `.txt` naming errors on Windows!
- **First-Boot Smart AP Onboarding**: If WiFi cannot be reached or configuration is missing, the Pi launches a setup hotspot (`TeslaUSB-Setup` at `192.168.4.1`) with a captive portal. You can scan networks and finish setup straight from your phone.
- **[🎬 Synchronized 4-Camera Video Player](teslausb-www/html/player/player.html)**: Integrated HTML5 player that synchronizes Front, Back, Left, and Right camera streams with 2x2 grid view, single-camera zoom, synchronized scrubbing, and variable playback speed.
- **Interactive CLI Configurator & Linter**: Run `python tools/teslausb-wizard.py` to configure from any terminal, or test an existing file with `--validate`.
- **[⚡ Quickstart Guide](QUICKSTART.md)**: A streamlined guide with hardware, cabling, and troubleshooting tables.

## Prerequisites

### Assumptions

- You park in range of your wireless network.
- Your wireless network is configured with WPA2 PSK access.

### Hardware

Required:

- [A Raspberry Pi or other SBC that supports USB OTG](https://github.com/marcone/teslausb/wiki/Hardware).
- A Micro SD card, at least 64 GB in size, and an adapter (if necessary) to connect the card to your computer.
- Cable(s) to connect the SBC to the Tesla (USB A/Micro B cable for the Pi Zero, USB A/C cable for the Pi 4 and 5, other SBCs vary)

Optional:

- A case and/or cooler for the SBC. For the Raspberry Pi 4 I like the ["armor case"](https://www.amazon.com/s?k=Raspberry+Pi+4+Armor+Case) (available with or without fans), which appears to do a good job of protecting the Pi while keeping it cool.
- USB Splitter if you don't want to lose a front USB port. [The Onvian Splitter](https://www.amazon.com/gp/product/B01KX4TKH6) has been reported working by multiple people on reddit. Some SBCs require separate power and data connection, so may require a splitter or a USB hub to connect to the car.

## Installing

To install teslausb on a Raspberry Pi, it is recommended to use the [prebuilt image](https://github.com/marcone/teslausb/releases) and [one step setup instructions](doc/OneStepSetup.md). For other SBCs, start [here](https://github.com/marcone/teslausb/wiki/Installation)

## Contributing

You're welcome to contribute to this repo by submitting pull requests and creating issues.
For pull requests, please split complex changes into multiple pull requests when feasible, and follow the existing code style.

## Credits & Acknowledgements

This modernized version builds directly upon the years of dedication and innovation by the original TeslaUSB creators and maintainers:

- **[Marcone (@marcone)](https://github.com/marcone)**: Lead architect and maintainer of [marcone/teslausb](https://github.com/marcone/teslausb) and [marcone/teslausb-webui](https://github.com/marcone/teslausb-webui). Marcone engineered the headless setup automation, the robust read-only root filesystem architecture, multi-protocol archiving (CIFS, rsync, rclone), and the web interface.
- **[Cimryan (@cimryan)](https://github.com/cimryan)**: The original creator who founded the [cimryan/teslausb](https://github.com/cimryan/teslausb) repository and organized the initial community scripts onto GitHub.
- **The Reddit Community**: The original creators and testers in the [r/teslamotors community thread](https://www.reddit.com/r/teslamotors/comments/9m9gyk/build_a_smart_usb_drive_for_your_tesla_dash_cam/) whose early proof-of-concept inspired the smart dashcam ecosystem.
- **Upstream Contributors**: All [contributors to marcone/teslausb](https://github.com/marcone/teslausb/graphs/contributors) whose code, testing, and bug reports make TeslaUSB possible.

## License

This project is licensed under the original GNU General Public License (GPL) / MIT License — see the [LICENSE](LICENSE) file for details.

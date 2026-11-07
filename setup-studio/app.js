/**
 * TeslaUSB Setup Studio
 * Interactive Configuration Generator, Validator, and SD Card Writer
 */

// Application State
const state = {
  currentStep: 1,
  totalSteps: 6,
  hardware: "pi4", // pizero2, pi4, pi5, other
  sdSizeGB: 128,
  osReserveGB: 6,
  camSizeGB: 40,
  musicSizeGB: 0,
  enableMusic: false,
  lightshowSizeGB: 0,
  enableLightshow: false,
  boomboxSizeGB: 0,
  enableBoombox: false,
  
  // WiFi
  ssid: "",
  wifiPass: "",
  enableSecondWifi: false,
  ssid2: "",
  wifiPass2: "",
  hostname: "teslausb",
  hiddenSsid: false,
  
  // Archive
  archiveSystem: "cifs", // cifs, rclone, rsync, nfs, none
  // CIFS
  cifsServer: "",
  cifsShare: "",
  cifsUser: "",
  cifsPass: "",
  cifsDomain: "",
  cifsVersion: "",
  // Rclone
  rcloneDrive: "",
  rclonePath: "",
  rcloneServer: "",
  // Rsync
  rsyncServer: "",
  rsyncUser: "",
  rsyncPath: "",
  // NFS
  nfsServer: "",
  nfsShare: "",
  
  // Archive filters & options
  archiveSentry: true,
  archiveSaved: true,
  archiveRecent: false,
  archiveTrackmode: true,
  snapshotInterval: 0, // 0 = default, or seconds
  
  // Notifications
  notifDiscord: false,
  discordWebhook: "",
  notifTelegram: false,
  telegramToken: "",
  telegramChatId: "",
  notifPushover: false,
  pushoverToken: "",
  pushoverUser: "",
  notifGotify: false,
  gotifyUrl: "",
  gotifyToken: "",
  notifWebhook: false,
  webhookUrl: "",
  
  // Tesla integration
  carStayAwake: false,
  stayAwakeMethod: "ble", // ble, fleet, legacy
  vin: "",
  
  // Web UI
  webAuth: false,
  webUser: "admin",
  webPass: "",
  enableAp: false,
  apSsid: "TeslaUSB-Car",
  apPass: "teslausb123"
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  updateStorageVisualizer();
  updateConfigPreview();
});

// Event Listeners
function initEventListeners() {
  // Navigation
  document.querySelectorAll(".step-indicator").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const step = parseInt(btn.dataset.step, 10);
      goToStep(step);
    });
  });

  // Next / Prev buttons
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  if (prevBtn) prevBtn.addEventListener("click", prevStep);
  if (nextBtn) nextBtn.addEventListener("click", nextStep);

  // Hardware selection
  document.querySelectorAll("[data-hardware]").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll("[data-hardware]").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      state.hardware = card.dataset.hardware;
      updateHardwareNotes();
      updateConfigPreview();
    });
  });

  // Storage card size
  const sdSizeSelect = document.getElementById("sdSizeSelect");
  if (sdSizeSelect) {
    sdSizeSelect.addEventListener("change", (e) => {
      state.sdSizeGB = parseInt(e.target.value, 10);
      recalculateStorageLimits();
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }

  // Cam slider
  const camSlider = document.getElementById("camSlider");
  if (camSlider) {
    camSlider.addEventListener("input", (e) => {
      state.camSizeGB = parseInt(e.target.value, 10);
      document.getElementById("camSliderVal").textContent = `${state.camSizeGB} GB`;
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }

  // Music toggle & slider
  const musicToggle = document.getElementById("musicToggle");
  const musicSlider = document.getElementById("musicSlider");
  if (musicToggle) {
    musicToggle.addEventListener("change", (e) => {
      state.enableMusic = e.target.checked;
      document.getElementById("musicSliderGroup").style.display = state.enableMusic ? "block" : "none";
      if (!state.enableMusic) state.musicSizeGB = 0;
      else if (state.musicSizeGB === 0) state.musicSizeGB = 16;
      if (musicSlider) musicSlider.value = state.musicSizeGB;
      document.getElementById("musicSliderVal").textContent = `${state.musicSizeGB} GB`;
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }
  if (musicSlider) {
    musicSlider.addEventListener("input", (e) => {
      state.musicSizeGB = parseInt(e.target.value, 10);
      document.getElementById("musicSliderVal").textContent = `${state.musicSizeGB} GB`;
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }

  // Lightshow toggle & slider
  const lightshowToggle = document.getElementById("lightshowToggle");
  const lightshowSlider = document.getElementById("lightshowSlider");
  if (lightshowToggle) {
    lightshowToggle.addEventListener("change", (e) => {
      state.enableLightshow = e.target.checked;
      document.getElementById("lightshowSliderGroup").style.display = state.enableLightshow ? "block" : "none";
      if (!state.enableLightshow) state.lightshowSizeGB = 0;
      else if (state.lightshowSizeGB === 0) state.lightshowSizeGB = 2;
      if (lightshowSlider) lightshowSlider.value = state.lightshowSizeGB;
      document.getElementById("lightshowSliderVal").textContent = `${state.lightshowSizeGB} GB`;
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }
  if (lightshowSlider) {
    lightshowSlider.addEventListener("input", (e) => {
      state.lightshowSizeGB = parseInt(e.target.value, 10);
      document.getElementById("lightshowSliderVal").textContent = `${state.lightshowSizeGB} GB`;
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }

  // Boombox toggle & slider
  const boomboxToggle = document.getElementById("boomboxToggle");
  const boomboxSlider = document.getElementById("boomboxSlider");
  if (boomboxToggle) {
    boomboxToggle.addEventListener("change", (e) => {
      state.enableBoombox = e.target.checked;
      document.getElementById("boomboxSliderGroup").style.display = state.enableBoombox ? "block" : "none";
      if (!state.enableBoombox) state.boomboxSizeGB = 0;
      else if (state.boomboxSizeGB === 0) state.boomboxSizeGB = 1;
      if (boomboxSlider) boomboxSlider.value = state.boomboxSizeGB;
      document.getElementById("boomboxSliderVal").textContent = `${state.boomboxSizeGB} GB`;
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }
  if (boomboxSlider) {
    boomboxSlider.addEventListener("input", (e) => {
      state.boomboxSizeGB = parseInt(e.target.value, 10);
      document.getElementById("boomboxSliderVal").textContent = `${state.boomboxSizeGB} GB`;
      updateStorageVisualizer();
      updateConfigPreview();
    });
  }

  // Form input bindings
  bindInput("ssidInput", "ssid");
  bindInput("wifiPassInput", "wifiPass");
  bindInput("hostnameInput", "hostname");
  bindCheckbox("hiddenSsidCheck", "hiddenSsid");

  // Secondary WiFi
  const secondWifiToggle = document.getElementById("secondWifiToggle");
  if (secondWifiToggle) {
    secondWifiToggle.addEventListener("change", (e) => {
      state.enableSecondWifi = e.target.checked;
      document.getElementById("secondWifiFields").style.display = state.enableSecondWifi ? "block" : "none";
      updateConfigPreview();
    });
  }
  bindInput("ssid2Input", "ssid2");
  bindInput("wifiPass2Input", "wifiPass2");

  // Archive Backend selection
  document.querySelectorAll("[data-archive]").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll("[data-archive]").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      state.archiveSystem = card.dataset.archive;
      showArchiveFields(state.archiveSystem);
      updateConfigPreview();
    });
  });

  // Archive fields
  bindInput("cifsServer", "cifsServer");
  bindInput("cifsShare", "cifsShare");
  bindInput("cifsUser", "cifsUser");
  bindInput("cifsPass", "cifsPass");
  bindInput("cifsDomain", "cifsDomain");
  bindInput("cifsVersion", "cifsVersion");

  // Folder Auto-Detector & Smart Path Parser
  const browseFolderBtn = document.getElementById("browseArchiveFolderBtn");
  if (browseFolderBtn) {
    browseFolderBtn.addEventListener("click", browseArchiveFolder);
  }

  const smartPathInput = document.getElementById("smartPathInput");
  const parsePathBtn = document.getElementById("parsePathBtn");
  if (parsePathBtn) {
    parsePathBtn.addEventListener("click", () => {
      parseAndApplyNetworkPath(smartPathInput.value, true);
    });
  }
  if (smartPathInput) {
    smartPathInput.addEventListener("input", (e) => {
      if (e.target.value.trim().length > 3) {
        parseAndApplyNetworkPath(e.target.value, false);
      }
    });
  }

  // Detected Network Shares on PC
  const applyShareBtn = document.getElementById("applyDetectedShareBtn");
  const shareSelect = document.getElementById("detectedSharesSelect");
  if (applyShareBtn && shareSelect) {
    applyShareBtn.addEventListener("click", () => {
      const idx = shareSelect.value;
      if (idx !== "" && detectedNetworkShares[idx]) {
        applyDetectedShare(detectedNetworkShares[idx]);
      }
    });
    shareSelect.addEventListener("change", (e) => {
      const idx = e.target.value;
      if (idx !== "" && detectedNetworkShares[idx]) {
        applyDetectedShare(detectedNetworkShares[idx]);
      }
    });
  }

  fetchDetectedShares();

  bindInput("rcloneDrive", "rcloneDrive");
  bindInput("rclonePath", "rclonePath");
  bindInput("rcloneServer", "rcloneServer");

  bindInput("rsyncServer", "rsyncServer");
  bindInput("rsyncUser", "rsyncUser");
  bindInput("rsyncPath", "rsyncPath");

  bindInput("nfsServer", "nfsServer");
  bindInput("nfsShare", "nfsShare");

  // Archive options
  bindCheckbox("archSentry", "archiveSentry");
  bindCheckbox("archSaved", "archiveSaved");
  bindCheckbox("archRecent", "archiveRecent");
  bindCheckbox("archTrack", "archiveTrackmode");

  // Notifications
  bindToggleSection("notifDiscordToggle", "discordFields", "notifDiscord");
  bindInput("discordWebhook", "discordWebhook");

  bindToggleSection("notifTelegramToggle", "telegramFields", "notifTelegram");
  bindInput("telegramToken", "telegramToken");
  bindInput("telegramChatId", "telegramChatId");

  bindToggleSection("notifPushoverToggle", "pushoverFields", "notifPushover");
  bindInput("pushoverToken", "pushoverToken");
  bindInput("pushoverUser", "pushoverUser");

  bindToggleSection("notifGotifyToggle", "gotifyFields", "notifGotify");
  bindInput("gotifyUrl", "gotifyUrl");
  bindInput("gotifyToken", "gotifyToken");

  // Car stay awake
  bindToggleSection("carStayAwakeToggle", "stayAwakeFields", "carStayAwake");
  bindInput("teslaVin", "vin");

  // In-Car AP
  bindToggleSection("enableApToggle", "apFields", "enableAp");
  bindInput("apSsid", "apSsid");
  bindInput("apPass", "apPass");

  // Password view toggles
  document.querySelectorAll(".pwd-toggle").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.dataset.target;
      const input = document.getElementById(targetId);
      if (input) {
        input.type = input.type === "password" ? "text" : "password";
        btn.textContent = input.type === "password" ? "👁️" : "🙈";
      }
    });
  });

  // Action buttons
  const copyBtn = document.getElementById("copyConfigBtn");
  if (copyBtn) copyBtn.addEventListener("click", copyConfigToClipboard);

  const downloadBtn = document.getElementById("downloadConfigBtn");
  if (downloadBtn) downloadBtn.addEventListener("click", downloadConfigFile);

  const writeSdBtn = document.getElementById("writeSdBtn");
  if (writeSdBtn) writeSdBtn.addEventListener("click", writeDirectToSdCard);

  const openLinterBtn = document.getElementById("openLinterBtn");
  if (openLinterBtn) openLinterBtn.addEventListener("click", openLinterModal);

  const closeLinterBtn = document.getElementById("closeLinterBtn");
  if (closeLinterBtn) closeLinterBtn.addEventListener("click", closeLinterModal);

  const runLinterBtn = document.getElementById("runLinterBtn");
  if (runLinterBtn) runLinterBtn.addEventListener("click", runConfigLinter);

  // In-Browser Flasher Controls
  const flasherRefreshBtn = document.getElementById("flasherRefreshBtn");
  if (flasherRefreshBtn) {
    flasherRefreshBtn.addEventListener("click", fetchConnectedDisks);
  }

  const flasherDiskSelect = document.getElementById("flasherDiskSelect");
  if (flasherDiskSelect) {
    flasherDiskSelect.addEventListener("change", (e) => {
      const warn = document.getElementById("flasherEraseWarning");
      if (warn) warn.style.display = e.target.value ? "block" : "none";
    });
  }

  const flasherStartBtn = document.getElementById("flasherStartBtn");
  if (flasherStartBtn) {
    flasherStartBtn.addEventListener("click", startBrowserFlashing);
  }

  // Attempt initial disk scan
  fetchConnectedDisks();
}

// Helpers for input binding
function bindInput(id, stateKey) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("input", (e) => {
    state[stateKey] = e.target.value;
    updateConfigPreview();
  });
}

function bindCheckbox(id, stateKey) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("change", (e) => {
    state[stateKey] = e.target.checked;
    updateConfigPreview();
  });
}

function bindToggleSection(toggleId, containerId, stateKey) {
  const toggle = document.getElementById(toggleId);
  const container = document.getElementById(containerId);
  if (!toggle || !container) return;
  toggle.addEventListener("change", (e) => {
    state[stateKey] = e.target.checked;
    container.style.display = state[stateKey] ? "block" : "none";
    updateConfigPreview();
  });
}

// Wizard Steps
function goToStep(step) {
  if (step < 1 || step > state.totalSteps) return;
  state.currentStep = step;
  
  // Update step indicators
  document.querySelectorAll(".step-indicator").forEach(ind => {
    const s = parseInt(ind.dataset.step, 10);
    ind.classList.remove("active");
    if (s === step) ind.classList.add("active");
    else if (s < step) ind.classList.add("completed");
    else ind.classList.remove("completed");
  });

  // Show active step content
  document.querySelectorAll(".step-content").forEach(content => {
    content.classList.remove("active");
  });
  const activeContent = document.getElementById(`step${step}`);
  if (activeContent) activeContent.classList.add("active");

  // Update navigation buttons
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");
  if (prevBtn) prevBtn.style.visibility = step === 1 ? "hidden" : "visible";
  if (nextBtn) {
    if (step === state.totalSteps) {
      nextBtn.style.display = "none";
    } else {
      nextBtn.style.display = "inline-flex";
      nextBtn.innerHTML = `<span>Next Step</span> →`;
    }
  }

  // Refresh drives when entering deploy step
  if (step === 6) {
    fetchConnectedDisks();
  }

  // Scroll to top
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function nextStep() {
  if (state.currentStep < state.totalSteps) {
    goToStep(state.currentStep + 1);
  }
}

function prevStep() {
  if (state.currentStep > 1) {
    goToStep(state.currentStep - 1);
  }
}

// Hardware & Storage logic
function updateHardwareNotes() {
  const noteEl = document.getElementById("hardwareNotes");
  if (!noteEl) return;
  
  if (state.hardware === "pizero2") {
    noteEl.innerHTML = `<strong>Raspberry Pi Zero 2 W:</strong> Connect the USB cable to the Pi's <em>inner</em> micro-USB port (labeled 'USB' / data port), NOT the 'PWR' port. Requires 2.4 GHz WiFi.`;
  } else if (state.hardware === "pi4") {
    noteEl.innerHTML = `<strong>Raspberry Pi 4:</strong> Connect using a USB-A to USB-C cable to the Pi's USB-C port. Some cars require a USB-A power+data splitter if the port doesn't provide enough current. Supports 2.4 & 5 GHz WiFi.`;
  } else if (state.hardware === "pi5") {
    noteEl.innerHTML = `<strong>Raspberry Pi 5:</strong> Supported! Ensure adequate cooling. Uses the USB-C port in peripheral/device mode. Supports 2.4 & 5 GHz WiFi.`;
  } else {
    noteEl.innerHTML = `<strong>Custom SBC:</strong> Ensure your board supports USB OTG gadget mode and UDC driver.`;
  }
}

function recalculateStorageLimits() {
  const maxAvailable = state.sdSizeGB - state.osReserveGB;
  const camSlider = document.getElementById("camSlider");
  if (camSlider) {
    camSlider.max = Math.max(32, maxAvailable - 10);
    if (state.camSizeGB > camSlider.max) {
      state.camSizeGB = parseInt(camSlider.max, 10);
      camSlider.value = state.camSizeGB;
      document.getElementById("camSliderVal").textContent = `${state.camSizeGB} GB`;
    }
  }
}

function updateStorageVisualizer() {
  const total = state.sdSizeGB;
  const os = state.osReserveGB;
  const cam = state.camSizeGB;
  const music = state.enableMusic ? state.musicSizeGB : 0;
  const lightshow = state.enableLightshow ? state.lightshowSizeGB : 0;
  const boombox = state.enableBoombox ? state.boomboxSizeGB : 0;
  
  const used = os + cam + music + lightshow + boombox;
  const free = Math.max(0, total - used);

  const osPct = (os / total) * 100;
  const camPct = (cam / total) * 100;
  const musicPct = (music / total) * 100;
  const lightshowPct = (lightshow / total) * 100;
  const boomboxPct = (boombox / total) * 100;
  const freePct = (free / total) * 100;

  setBarSeg("segOs", osPct, `OS (${os}G)`);
  setBarSeg("segCam", camPct, `Cam (${cam}G)`);
  setBarSeg("segMusic", musicPct, music > 0 ? `Music (${music}G)` : "");
  setBarSeg("segLightshow", lightshowPct, lightshow > 0 ? `LightShow (${lightshow}G)` : "");
  setBarSeg("segBoombox", boomboxPct, boombox > 0 ? `Boombox (${boombox}G)` : "");
  setBarSeg("segFree", freePct, free > 0 ? `Free (${free}G)` : "");
}

function setBarSeg(id, pct, label) {
  const el = document.getElementById(id);
  if (!el) return;
  el.style.width = `${pct}%`;
  el.textContent = pct > 6 ? label : "";
  el.style.display = pct > 0 ? "flex" : "none";
}

function showArchiveFields(type) {
  const fields = ["cifsFields", "rcloneFields", "rsyncFields", "nfsFields", "noneFields"];
  fields.forEach(f => {
    const el = document.getElementById(f);
    if (el) el.style.display = "none";
  });
  const activeEl = document.getElementById(`${type}Fields`);
  if (activeEl) activeEl.style.display = "block";
}

/**
 * Robust Bash-Safe Quoting Engine
 * Generates safely escaped export strings according to bash quoting rules
 */
function bashQuote(val) {
  if (val === undefined || val === null) return "''";
  const str = String(val);
  
  // If string contains only safe alphanumeric and simple punctuation:
  if (/^[a-zA-Z0-9_\-\.\/]+$/.test(str)) {
    return str;
  }
  
  // If string does NOT contain single quotes:
  if (!str.includes("'")) {
    return `'${str}'`;
  }
  
  // If it has single quotes, use $'...' syntax escaping single quotes and backslashes
  const escaped = str.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  return `$'${escaped}'`;
}

/**
 * Generate Complete teslausb_setup_variables.conf Content
 */
function generateConfigFile() {
  const lines = [
    "#####################################################################",
    "# TESLAUSB CONFIGURATION FILE",
    `# Generated by TeslaUSB Setup Studio on ${new Date().toISOString()}`,
    "#####################################################################",
    ""
  ];

  // WiFi Setup
  lines.push("# === WiFi Configuration ===");
  if (state.ssid) {
    lines.push(`export SSID=${bashQuote(state.ssid)}`);
    lines.push(`export WIFIPASS=${bashQuote(state.wifiPass)}`);
  } else {
    lines.push("# export SSID='your_ssid'");
    lines.push("# export WIFIPASS='your_password'");
  }

  if (state.enableSecondWifi && state.ssid2) {
    lines.push(`export SSID2=${bashQuote(state.ssid2)}`);
    lines.push(`export WIFIPASS2=${bashQuote(state.wifiPass2)}`);
  }

  if (state.hostname && state.hostname !== "teslausb") {
    lines.push(`export TESLAUSB_HOSTNAME=${bashQuote(state.hostname)}`);
  }
  lines.push("");

  // Partition sizes
  lines.push("# === Drive Partition Sizes ===");
  lines.push(`export CAM_SIZE=${state.camSizeGB}G`);
  if (state.enableMusic && state.musicSizeGB > 0) {
    lines.push(`export MUSIC_SIZE=${state.musicSizeGB}G`);
  }
  if (state.enableLightshow && state.lightshowSizeGB > 0) {
    lines.push(`export LIGHTSHOW_SIZE=${state.lightshowSizeGB}G`);
  }
  if (state.enableBoombox && state.boomboxSizeGB > 0) {
    lines.push(`export BOOMBOX_SIZE=${state.boomboxSizeGB}G`);
  }
  lines.push("");

  // Archive Backend
  lines.push("# === Archive Storage Backend ===");
  lines.push(`export ARCHIVE_SYSTEM=${state.archiveSystem}`);

  if (state.archiveSystem === "cifs") {
    lines.push(`export ARCHIVE_SERVER=${bashQuote(state.cifsServer || "192.168.1.100")}`);
    lines.push(`export SHARE_NAME=${bashQuote(state.cifsShare || "TeslaCam")}`);
    lines.push(`export SHARE_USER=${bashQuote(state.cifsUser || "username")}`);
    lines.push(`export SHARE_PASSWORD=${bashQuote(state.cifsPass || "password")}`);
    if (state.cifsDomain) lines.push(`export SHARE_DOMAIN=${bashQuote(state.cifsDomain)}`);
    if (state.cifsVersion) lines.push(`export CIFS_VERSION=${bashQuote(state.cifsVersion)}`);
  } else if (state.archiveSystem === "rclone") {
    if (state.rcloneServer) lines.push(`export ARCHIVE_SERVER=${bashQuote(state.rcloneServer)}`);
    lines.push(`export RCLONE_DRIVE=${bashQuote(state.rcloneDrive || "gdrive")}`);
    lines.push(`export RCLONE_PATH=${bashQuote(state.rclonePath || "TeslaCam")}`);
  } else if (state.archiveSystem === "rsync") {
    lines.push(`export RSYNC_SERVER=${bashQuote(state.rsyncServer || "hostname_or_ip")}`);
    lines.push(`export RSYNC_USER=${bashQuote(state.rsyncUser || "username")}`);
    lines.push(`export RSYNC_PATH=${bashQuote(state.rsyncPath || "/path/to/TeslaCam")}`);
  } else if (state.archiveSystem === "nfs") {
    lines.push(`export ARCHIVE_SERVER=${bashQuote(state.nfsServer || "hostname_or_ip")}`);
    lines.push(`export SHARE_NAME=${bashQuote(state.nfsShare || "/volume1/TeslaCam")}`);
  }
  lines.push("");

  // Clip Selection Filters
  lines.push("# === Footage Archiving Options ===");
  if (!state.archiveSentry) lines.push("export ARCHIVE_SENTRYCLIPS=false");
  if (!state.archiveSaved) lines.push("export ARCHIVE_SAVEDCLIPS=false");
  if (state.archiveRecent) lines.push("export ARCHIVE_RECENTCLIPS=true");
  if (!state.archiveTrackmode) lines.push("export ARCHIVE_TRACKMODECLIPS=false");
  lines.push("");

  // Notifications
  const hasNotifs = state.notifDiscord || state.notifTelegram || state.notifPushover || state.notifGotify;
  if (hasNotifs) {
    lines.push("# === Push Notifications ===");
    if (state.notifDiscord && state.discordWebhook) {
      lines.push(`export DISCORD_WEBHOOK_URL=${bashQuote(state.discordWebhook)}`);
    }
    if (state.notifTelegram && state.telegramToken) {
      lines.push(`export TELEGRAM_BOT_TOKEN=${bashQuote(state.telegramToken)}`);
      lines.push(`export TELEGRAM_CHAT_ID=${bashQuote(state.telegramChatId)}`);
    }
    if (state.notifPushover && state.pushoverToken) {
      lines.push(`export PUSHOVER_APP_TOKEN=${bashQuote(state.pushoverToken)}`);
      lines.push(`export PUSHOVER_USER_KEY=${bashQuote(state.pushoverUser)}`);
    }
    if (state.notifGotify && state.gotifyUrl) {
      lines.push(`export GOTIFY_URL=${bashQuote(state.gotifyUrl)}`);
      lines.push(`export GOTIFY_APP_TOKEN=${bashQuote(state.gotifyToken)}`);
    }
    lines.push("");
  }

  // Tesla Integration
  if (state.carStayAwake && state.vin) {
    lines.push("# === Tesla Vehicle Integration ===");
    lines.push(`export TESLA_VIN=${bashQuote(state.vin)}`);
    lines.push("");
  }

  // In-Car AP
  if (state.enableAp && state.apSsid && state.apPass) {
    lines.push("# === In-Car WiFi Access Point ===");
    lines.push(`export AP_SSID=${bashQuote(state.apSsid)}`);
    lines.push(`export AP_PASS=${bashQuote(state.apPass)}`);
    lines.push("");
  }

  return lines.join("\n");
}

function updateConfigPreview() {
  const previewEl = document.getElementById("configCodePreview");
  if (previewEl) {
    previewEl.textContent = generateConfigFile();
  }
}

// Copy to Clipboard
function copyConfigToClipboard() {
  const content = generateConfigFile();
  navigator.clipboard.writeText(content).then(() => {
    const btn = document.getElementById("copyConfigBtn");
    const origText = btn.textContent;
    btn.textContent = "Copied! ✓";
    setTimeout(() => { btn.textContent = origText; }, 2000);
  });
}

// Download .conf File
function downloadConfigFile() {
  const content = generateConfigFile();
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "teslausb_setup_variables.conf";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Direct SD Card Write using Web File System Access API
async function writeDirectToSdCard() {
  const statusEl = document.getElementById("writeStatus");
  if (!window.showDirectoryPicker) {
    alert("Direct SD card writing requires Chrome, Edge, or Opera. Please use the 'Download' button instead.");
    return;
  }

  try {
    statusEl.innerHTML = `<span style="color:var(--accent-blue)">Please select your MicroSD card 'boot' or root folder...</span>`;
    
    // Prompt user to pick directory
    const dirHandle = await window.showDirectoryPicker({
      id: "teslausb_sd",
      mode: "readwrite"
    });

    statusEl.innerHTML = `<span style="color:var(--accent-amber)">Writing teslausb_setup_variables.conf...</span>`;

    // Create file
    const fileHandle = await dirHandle.getFileHandle("teslausb_setup_variables.conf", { create: true });
    const writable = await fileHandle.createWritable();
    const content = generateConfigFile();
    await writable.write(content);
    await writable.close();

    statusEl.innerHTML = `<span style="color:var(--accent-green);font-weight:600;">✓ Success! Configuration written to SD card. You can safely eject and boot the Pi!</span>`;
  } catch (err) {
    if (err.name !== "AbortError") {
      statusEl.innerHTML = `<span style="color:var(--tesla-red)">Error: ${err.message}</span>`;
    } else {
      statusEl.innerHTML = "";
    }
  }
}

// Config Linter / Validator Modal
function openLinterModal() {
  const modal = document.getElementById("linterModal");
  if (modal) modal.classList.add("active");
}

function closeLinterModal() {
  const modal = document.getElementById("linterModal");
  if (modal) modal.classList.remove("active");
}

function runConfigLinter() {
  const raw = document.getElementById("linterInput").value;
  const resultsEl = document.getElementById("linterResults");
  resultsEl.innerHTML = "";

  if (!raw.trim()) {
    resultsEl.innerHTML = `<div class="validation-item warning">Please paste a configuration file to validate.</div>`;
    return;
  }

  const issues = [];
  const lines = raw.split("\n");
  const parsedVars = {};

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) return;

    const match = trimmed.match(/^export\s+([A-Za-z0-9_]+)=(.*)$/);
    if (!match) {
      if (trimmed.startsWith("export")) {
        issues.push({ type: "error", msg: `Line ${idx + 1}: Malformed export syntax: '${trimmed}'` });
      }
      return;
    }

    const key = match[1];
    let val = match[2].trim();
    parsedVars[key] = val;

    // Check for bad quotation
    if (val.startsWith("'") && !val.endsWith("'")) {
      issues.push({ type: "error", msg: `Line ${idx + 1}: Unclosed single quote in ${key}` });
    } else if (val.startsWith('"') && !val.endsWith('"')) {
      issues.push({ type: "error", msg: `Line ${idx + 1}: Unclosed double quote in ${key}` });
    }

    // Check for unquoted special characters in bash
    if (!val.startsWith("'") && !val.startsWith('"') && !val.startsWith("$'")) {
      if (/[\s&|;$`()\\!]/.test(val)) {
        issues.push({ type: "warning", msg: `Line ${idx + 1}: Value for ${key} contains special bash characters without quotes. Consider quoting it.` });
      }
    }
  });

  // Verify Required Keys
  if (!parsedVars["SSID"] && !parsedVars["WIFIPASS"]) {
    issues.push({ type: "warning", msg: "Missing SSID or WIFIPASS: The Pi will not be able to connect to WiFi on first boot." });
  }

  const archiveSys = parsedVars["ARCHIVE_SYSTEM"];
  if (archiveSys === "cifs" || !archiveSys) {
    if (!parsedVars["ARCHIVE_SERVER"]) issues.push({ type: "error", msg: "CIFS enabled but ARCHIVE_SERVER is missing." });
    if (!parsedVars["SHARE_NAME"]) issues.push({ type: "error", msg: "CIFS enabled but SHARE_NAME is missing." });
    if (!parsedVars["SHARE_USER"]) issues.push({ type: "warning", msg: "SHARE_USER is empty. Most SMB servers require credentials." });
    
    // Check if user accidentally entered Windows path syntax
    if (parsedVars["SHARE_NAME"] && parsedVars["SHARE_NAME"].includes("\\")) {
      issues.push({ type: "error", msg: `SHARE_NAME contains backslashes ('\\'). CIFS shares should not have leading backslashes or Windows drive paths.` });
    }
  }

  if (parsedVars["CAM_SIZE"]) {
    const num = parseInt(parsedVars["CAM_SIZE"], 10);
    if (isNaN(num) || num < 20) {
      issues.push({ type: "warning", msg: `CAM_SIZE (${parsedVars["CAM_SIZE"]}) is small. A minimum of 32G or 40G is strongly recommended for Sentry and Dashcam footage.` });
    }
  }

  if (issues.length === 0) {
    resultsEl.innerHTML = `<div class="validation-item success">✓ Great news! Configuration is valid and adheres to all TeslaUSB bash rules.</div>`;
  } else {
    issues.forEach(iss => {
      const div = document.createElement("div");
      div.className = `validation-item ${iss.type}`;
      div.textContent = `${iss.type.toUpperCase()}: ${iss.msg}`;
      resultsEl.appendChild(div);
    });
  }
}

/**
 * Smart Folder Picker & Network Address Parser
 */
async function browseArchiveFolder() {
  const feedback = document.getElementById("smartPathFeedback");
  if (!window.showDirectoryPicker) {
    // Fallback for browsers without showDirectoryPicker
    const input = document.createElement("input");
    input.type = "file";
    input.webkitdirectory = true;
    input.onchange = (e) => {
      if (e.target.files.length > 0) {
        const fullPath = e.target.files[0].webkitRelativePath || "";
        const folderName = fullPath.split("/")[0] || e.target.files[0].name;
        applySelectedFolder(folderName);
      }
    };
    input.click();
    return;
  }

  try {
    feedback.className = "path-feedback info";
    feedback.textContent = "Please select your archive destination folder...";
    feedback.style.display = "block";

    const dirHandle = await window.showDirectoryPicker({
      id: "teslausb_archive_dest",
      mode: "read"
    });

    applySelectedFolder(dirHandle.name);
  } catch (err) {
    if (err.name !== "AbortError") {
      feedback.className = "path-feedback warning";
      feedback.textContent = `Could not access folder: ${err.message}`;
      feedback.style.display = "block";
    } else {
      feedback.style.display = "none";
    }
  }
}

let detectedNetworkShares = [];

async function fetchDetectedShares() {
  const container = document.getElementById("detectedSharesContainer");
  const select = document.getElementById("detectedSharesSelect");
  if (!select) return;

  try {
    const res = await fetch("/api/network_shares");
    if (!res.ok) return;
    const data = await res.json();
    detectedNetworkShares = data.shares || [];

    if (detectedNetworkShares.length > 0) {
      select.innerHTML = '<option value="">-- Click to select detected network share --</option>';
      let bestMatchIdx = -1;

      detectedNetworkShares.forEach((s, idx) => {
        const opt = document.createElement("option");
        opt.value = idx;
        const isTesla = s.share.toLowerCase().includes("teslacam");
        opt.textContent = `${s.display}${isTesla ? " ★ [Detected TeslaCam Drive]" : ""}`;
        select.appendChild(opt);
        if (isTesla && bestMatchIdx === -1) bestMatchIdx = idx;
      });

      if (container) container.style.display = "block";

      // If a TeslaCam share was found on PC (like Y:\TeslaCam), auto-fill it!
      if (bestMatchIdx >= 0 && !state.cifsServer) {
        select.value = bestMatchIdx;
        applyDetectedShare(detectedNetworkShares[bestMatchIdx]);
      }
    }
  } catch (e) {
    // server not running or network shares unavailable
  }
}

function applyDetectedShare(s) {
  if (!s) return;
  state.cifsServer = s.server;
  state.cifsShare = s.share;

  const srvEl = document.getElementById("cifsServer");
  const shrEl = document.getElementById("cifsShare");
  if (srvEl) srvEl.value = s.server;
  if (shrEl) shrEl.value = s.share;

  updateConfigPreview();

  const feedback = document.getElementById("smartPathFeedback");
  if (feedback) {
    feedback.className = "path-feedback success";
    feedback.innerHTML = `✓ Auto-filled from mapped drive <strong>${escapeHtml(s.letter)}</strong>!<br><strong>Server IP/Host:</strong> <code>${escapeHtml(s.server)}</code> &nbsp;|&nbsp; <strong>Share Name:</strong> <code>${escapeHtml(s.share)}</code>`;
    feedback.style.display = "block";
  }
}

function applySelectedFolder(folderName) {
  const feedback = document.getElementById("smartPathFeedback");
  state.cifsShare = folderName;
  const shareInput = document.getElementById("cifsShare");
  if (shareInput) shareInput.value = folderName;

  // Check if this folder matches any detected mapped network shares on this PC!
  const matched = detectedNetworkShares.find(s => 
    s.share.toLowerCase() === folderName.toLowerCase() || 
    s.remote.toLowerCase().includes(folderName.toLowerCase())
  );

  if (matched) {
    state.cifsServer = matched.server;
    const srvInput = document.getElementById("cifsServer");
    if (srvInput) srvInput.value = matched.server;
    updateConfigPreview();

    feedback.className = "path-feedback success";
    feedback.innerHTML = `✓ Selected folder <strong>${escapeHtml(folderName)}</strong> matched to mapped drive <strong>${escapeHtml(matched.letter)}</strong> (<code>${escapeHtml(matched.remote)}</code>)!<br><strong>Server IP/Host:</strong> <code>${escapeHtml(matched.server)}</code> &nbsp;|&nbsp; <strong>Share Name:</strong> <code>${escapeHtml(matched.share)}</code>`;
    feedback.style.display = "block";
    return;
  }

  updateConfigPreview();

  if (!state.cifsServer) {
    feedback.className = "path-feedback success";
    feedback.innerHTML = `✓ Selected folder <strong>${escapeHtml(folderName)}</strong>! Share Name set to <code>${escapeHtml(folderName)}</code>.<br>Please enter your Server IP or hostname above.`;
  } else {
    feedback.className = "path-feedback success";
    feedback.innerHTML = `✓ Set Share Name to <code>${escapeHtml(folderName)}</code> on server <strong>${escapeHtml(state.cifsServer)}</strong>!`;
  }
  feedback.style.display = "block";
}

function parseAndApplyNetworkPath(rawPath, explicit = true) {
  const feedback = document.getElementById("smartPathFeedback");
  if (!rawPath || !rawPath.trim()) {
    if (explicit) {
      feedback.className = "path-feedback warning";
      feedback.textContent = "Please enter or paste a network path to parse.";
      feedback.style.display = "block";
    }
    return;
  }

  const p = rawPath.trim();

  // Pattern 1: Windows UNC path (e.g. \\192.168.1.50\TeslaCam or \\NAS\video\TeslaCam or //server/share)
  const uncMatch = p.match(/^[\\\/]{2}([^\/\\:]+)[\/\\]+([^\\\/].*)$/);
  if (uncMatch) {
    const server = uncMatch[1];
    const share = uncMatch[2].replace(/\\/g, "/").replace(/\/+$/, "");

    state.cifsServer = server;
    state.cifsShare = share;

    const srvEl = document.getElementById("cifsServer");
    const shrEl = document.getElementById("cifsShare");
    if (srvEl) srvEl.value = server;
    if (shrEl) shrEl.value = share;

    updateConfigPreview();

    feedback.className = "path-feedback success";
    feedback.innerHTML = `✓ Successfully parsed Windows UNC path!<br><strong>Server IP/Host:</strong> <code>${escapeHtml(server)}</code> &nbsp;|&nbsp; <strong>Share Name:</strong> <code>${escapeHtml(share)}</code>`;
    feedback.style.display = "block";
    return;
  }

  // Pattern 2: smb:// or cifs:// URL (e.g. smb://user:pass@192.168.1.50/TeslaCam or smb://mynas/share/path)
  const smbMatch = p.match(/^(?:smb|cifs):\/\/(?:([^:@]+)(?::([^@]+))?@)?([^\/:]+)(?::\d+)?\/(.+)$/i);
  if (smbMatch) {
    const user = smbMatch[1] || "";
    const pass = smbMatch[2] || "";
    const server = smbMatch[3];
    const share = smbMatch[4].replace(/\/+$/, "");

    state.cifsServer = server;
    state.cifsShare = share;
    const srvEl = document.getElementById("cifsServer");
    const shrEl = document.getElementById("cifsShare");
    if (srvEl) srvEl.value = server;
    if (shrEl) shrEl.value = share;

    if (user) {
      state.cifsUser = user;
      const userEl = document.getElementById("cifsUser");
      if (userEl) userEl.value = user;
    }
    if (pass) {
      state.cifsPass = pass;
      const passEl = document.getElementById("cifsPass");
      if (passEl) passEl.value = pass;
    }

    updateConfigPreview();

    feedback.className = "path-feedback success";
    feedback.innerHTML = `✓ Successfully parsed SMB URL!<br><strong>Server:</strong> <code>${escapeHtml(server)}</code> &nbsp;|&nbsp; <strong>Share:</strong> <code>${escapeHtml(share)}</code>` +
      (user ? ` &nbsp;|&nbsp; <strong>User:</strong> <code>${escapeHtml(user)}</code>` : "");
    feedback.style.display = "block";
    return;
  }

  // Pattern 3: Windows mapped drive letter (e.g. Z:\TeslaCam or Y:\video\TeslaCam)
  const driveMatch = p.match(/^([A-Za-z]):\\([^\\]+.*)$/);
  if (driveMatch) {
    const driveLetter = driveMatch[1].toUpperCase();
    const folderPath = driveMatch[2].replace(/\\/g, "/").replace(/\/+$/, "");

    state.cifsShare = folderPath;
    const shrEl = document.getElementById("cifsShare");
    if (shrEl) shrEl.value = folderPath;
    updateConfigPreview();

    feedback.className = "path-feedback info";
    feedback.innerHTML = `✓ Detected mapped network drive <strong>${driveLetter}:\\</strong>. Set Share Name to <code>${escapeHtml(folderPath)}</code>.<br>Please enter your Server IP or hostname above.`;
    feedback.style.display = "block";
    return;
  }

  // Pattern 4: NFS export (e.g. 192.168.1.50:/volume1/TeslaCam)
  const nfsMatch = p.match(/^([^\/\\:]+):(\/[^\/].*)$/);
  if (nfsMatch) {
    const server = nfsMatch[1];
    const share = nfsMatch[2];
    state.nfsServer = server;
    state.nfsShare = share;
    const nfsSrv = document.getElementById("nfsServer");
    const nfsShr = document.getElementById("nfsShare");
    if (nfsSrv) nfsSrv.value = server;
    if (nfsShr) nfsShr.value = share;

    updateConfigPreview();

    feedback.className = "path-feedback success";
    feedback.innerHTML = `✓ Parsed NFS export path!<br><strong>Server:</strong> <code>${escapeHtml(server)}</code> &nbsp;|&nbsp; <strong>Export Path:</strong> <code>${escapeHtml(share)}</code>`;
    feedback.style.display = "block";
    return;
  }

  if (explicit) {
    feedback.className = "path-feedback warning";
    feedback.innerHTML = `Could not recognize network format. Examples of recognized paths:<br><code>\\\\192.168.1.50\\TeslaCam</code><br><code>\\\\MYNAS\\video\\TeslaCam</code><br><code>smb://192.168.1.50/TeslaCam</code>`;
    feedback.style.display = "block";
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/**
 * In-Browser 1-Click Flasher Client Logic
 */
let flashPollTimer = null;

async function fetchConnectedDisks() {
  const select = document.getElementById("flasherDiskSelect");
  if (!select) return;
  select.innerHTML = '<option value="">🔍 Scanning connected drives...</option>';

  try {
    const res = await fetch("/api/disks");
    if (!res.ok) throw new Error("Local server not responding");
    const data = await res.json();
    const disks = data.disks || [];

    select.innerHTML = "";
    if (disks.length === 0) {
      select.innerHTML = '<option value="">No drives detected. Plug in your USB drive/SD card and click Refresh.</option>';
      return;
    }

    const defaultOpt = document.createElement("option");
    defaultOpt.value = "";
    defaultOpt.textContent = "-- Select your USB / SD Card drive --";
    select.appendChild(defaultOpt);

    disks.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.index;
      opt.textContent = `${d.display || `Disk ${d.index}: ${d.model}`}${d.is_usb ? " (Recommended)" : ""}`;
      select.appendChild(opt);
    });

    // Auto-select if only one USB disk is present
    const usbOnly = disks.filter(d => d.is_usb);
    if (usbOnly.length === 1) {
      select.value = usbOnly[0].index;
      const warn = document.getElementById("flasherEraseWarning");
      if (warn) warn.style.display = "block";
    }
  } catch (err) {
    select.innerHTML = '<option value="">Local server offline. Open via launch-setup-studio.bat for direct flashing.</option>';
  }
}

async function startBrowserFlashing() {
  const select = document.getElementById("flasherDiskSelect");
  const diskIndex = select ? select.value : "";
  if (!diskIndex) {
    alert("Please select your target USB / MicroSD drive from the dropdown first.");
    return;
  }

  const conf = generateConfigFile();
  const selectedText = select.options[select.selectedIndex].text;
  const confirmed = confirm(`Are you sure you want to format and flash:\n\n${selectedText}\n\nWARNING: All existing files on this drive will be erased!`);
  if (!confirmed) return;

  const controls = document.getElementById("flasherControls");
  const progressBox = document.getElementById("flasherProgressContainer");
  const successBox = document.getElementById("flasherSuccessContainer");
  const errorBox = document.getElementById("flasherErrorContainer");

  if (controls) controls.style.display = "none";
  if (successBox) successBox.style.display = "none";
  if (errorBox) errorBox.style.display = "none";
  if (progressBox) progressBox.style.display = "block";

  try {
    const res = await fetch("/api/flash", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        diskIndex: parseInt(diskIndex, 10),
        config: conf
      })
    });

    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || "Failed to initiate flashing.");
    }

    pollFlashStatus();
  } catch (err) {
    if (progressBox) progressBox.style.display = "none";
    if (controls) controls.style.display = "block";
    if (errorBox) {
      errorBox.style.display = "block";
      document.getElementById("flasherErrorMsg").textContent = err.message;
    }
  }
}

function pollFlashStatus() {
  if (flashPollTimer) clearInterval(flashPollTimer);

  const bar = document.getElementById("flasherProgressBar");
  const percentEl = document.getElementById("flasherPercent");
  const stageEl = document.getElementById("flasherStageMsg");
  const speedEl = document.getElementById("flasherSpeed");
  const subStatusEl = document.getElementById("flasherSubStatus");
  const controls = document.getElementById("flasherControls");
  const progressBox = document.getElementById("flasherProgressContainer");
  const successBox = document.getElementById("flasherSuccessContainer");
  const errorBox = document.getElementById("flasherErrorContainer");

  flashPollTimer = setInterval(async () => {
    try {
      const res = await fetch("/api/flash_status");
      const status = await res.json();

      if (bar) bar.style.width = `${status.progress}%`;
      if (percentEl) percentEl.textContent = `${status.progress}%`;
      if (stageEl) stageEl.textContent = status.message || "Processing...";
      if (speedEl) speedEl.textContent = status.speed || "";
      if (subStatusEl) subStatusEl.textContent = `Status: ${status.status}`;

      if (status.status === "complete") {
        clearInterval(flashPollTimer);
        if (progressBox) progressBox.style.display = "none";
        if (successBox) successBox.style.display = "block";
      } else if (status.status === "error") {
        clearInterval(flashPollTimer);
        if (progressBox) progressBox.style.display = "none";
        if (controls) controls.style.display = "block";
        if (errorBox) {
          errorBox.style.display = "block";
          document.getElementById("flasherErrorMsg").textContent = status.error || status.message;
        }
      }
    } catch (e) {
      // transient network glitch
    }
  }, 600);
}


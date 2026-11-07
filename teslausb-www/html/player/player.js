/**
 * TeslaUSB Synchronized 4-Camera Video Player
 * Synchronizes Front, Back, Left Repeater, and Right Repeater camera streams
 */

class TeslaPlayer {
  constructor() {
    this.videos = {
      front: document.getElementById("videoFront"),
      back: document.getElementById("videoBack"),
      left: document.getElementById("videoLeft"),
      right: document.getElementById("videoRight")
    };

    this.isPlaying = false;
    this.currentClipGroup = null;
    this.clipGroups = [];
    this.currentCategory = "SentryClips"; // SentryClips, SavedClips, RecentClips
    this.isSingleMode = false;
    this.expandedSlot = null;

    this.initUI();
    this.bindEvents();
    this.loadClips();
  }

  initUI() {
    this.playBtn = document.getElementById("playBtn");
    this.scrubber = document.getElementById("scrubber");
    this.currentTimeEl = document.getElementById("currentTime");
    this.totalTimeEl = document.getElementById("totalTime");
    this.speedSelect = document.getElementById("speedSelect");
    this.clipListEl = document.getElementById("clipList");
    this.gridEl = document.getElementById("videoGrid");
  }

  bindEvents() {
    // Play / Pause toggle
    this.playBtn.addEventListener("click", () => this.togglePlay());

    // Scrubber seeking
    this.scrubber.addEventListener("input", (e) => {
      const seekTime = parseFloat(e.target.value);
      this.seek(seekTime);
    });

    // Speed change
    this.speedSelect.addEventListener("change", (e) => {
      const rate = parseFloat(e.target.value);
      this.setPlaybackRate(rate);
    });

    // Time update (monitor primary video: front)
    this.videos.front.addEventListener("timeupdate", () => {
      if (!this.scrubberIsDragging) {
        const cur = this.videos.front.currentTime;
        const dur = this.videos.front.duration || 60;
        this.scrubber.value = cur;
        this.scrubber.max = dur;
        this.currentTimeEl.textContent = this.formatTime(cur);
        this.totalTimeEl.textContent = this.formatTime(dur);
      }
      this.resyncCheck();
    });

    // When primary clip ends, automatically advance
    this.videos.front.addEventListener("ended", () => {
      this.advanceNextClip();
    });

    // Click slot to zoom
    document.querySelectorAll(".video-slot").forEach(slot => {
      slot.addEventListener("click", () => {
        const cam = slot.dataset.cam;
        this.toggleSlotZoom(slot);
      });
    });

    // Filter tabs
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.currentCategory = btn.dataset.folder;
        this.loadClips();
      });
    });

    // Keyboard shortcuts
    window.addEventListener("keydown", (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
      if (e.code === "Space") {
        e.preventDefault();
        this.togglePlay();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        this.seekRelative(-5);
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        this.seekRelative(5);
      } else if (e.code === "KeyG") {
        this.toggleGridMode();
      }
    });
  }

  async loadClips() {
    this.clipListEl.innerHTML = '<li style="padding:1rem;color:var(--text-secondary);text-align:center;">Loading clips...</li>';

    try {
      // Fetch clips from server
      const res = await fetch(`/TeslaCam/${this.currentCategory}/`);
      if (!res.ok) throw new Error("Could not fetch clip directory");

      const html = await res.text();
      this.clipGroups = this.parseTeslaCamHtml(html, this.currentCategory);
      this.renderClipList();

      if (this.clipGroups.length > 0) {
        this.selectClip(this.clipGroups[0]);
      } else {
        this.clipListEl.innerHTML = '<li style="padding:1rem;color:var(--text-secondary);text-align:center;">No recordings found in this folder.</li>';
      }
    } catch (err) {
      // Fallback for demonstration / local testing
      this.clipGroups = this.getSampleClips();
      this.renderClipList();
      if (this.clipGroups.length > 0) {
        this.selectClip(this.clipGroups[0]);
      }
    }
  }

  parseTeslaCamHtml(html, folder) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const links = Array.from(doc.querySelectorAll("a"));
    const files = links.map(a => a.getAttribute("href")).filter(Boolean);

    // Group files by timestamp
    const groups = {};
    files.forEach(href => {
      const match = href.match(/(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})-(front|back|left_repeater|right_repeater)\.mp4$/);
      if (match) {
        const [_, timestamp, angle] = match;
        if (!groups[timestamp]) {
          groups[timestamp] = {
            id: timestamp,
            timestamp: timestamp.replace("_", " "),
            category: folder,
            cams: {}
          };
        }
        groups[timestamp].cams[angle] = `/TeslaCam/${folder}/${href}`;
      }
    });

    return Object.values(groups).sort((a, b) => b.id.localeCompare(a.id));
  }

  getSampleClips() {
    return [
      {
        id: "2026-11-07_12-30-00",
        timestamp: "2026-11-07 12:30:00",
        category: this.currentCategory,
        cams: {
          front: "",
          back: "",
          left_repeater: "",
          right_repeater: ""
        }
      }
    ];
  }

  renderClipList() {
    this.clipListEl.innerHTML = "";
    this.clipGroups.forEach(grp => {
      const li = document.createElement("li");
      li.className = "clip-item";
      li.dataset.id = grp.id;
      
      const camCount = Object.keys(grp.cams).length;
      li.innerHTML = `
        <div class="clip-date">📅 ${grp.timestamp}</div>
        <div class="clip-meta">
          <span>${grp.category}</span>
          <span>${camCount} Angles</span>
        </div>
      `;

      li.addEventListener("click", () => {
        document.querySelectorAll(".clip-item").forEach(item => item.classList.remove("active"));
        li.classList.add("active");
        this.selectClip(grp);
      });

      this.clipListEl.appendChild(li);
    });
  }

  selectClip(group) {
    this.currentClipGroup = group;
    const { cams } = group;

    // Load video sources
    this.setVideoSource(this.videos.front, cams.front);
    this.setVideoSource(this.videos.back, cams.back);
    this.setVideoSource(this.videos.left, cams.left_repeater);
    this.setVideoSource(this.videos.right, cams.right_repeater);

    // Reset playback
    this.pause();
    this.seek(0);
  }

  setVideoSource(videoEl, src) {
    if (src) {
      videoEl.src = src;
      videoEl.load();
      videoEl.style.display = "block";
    } else {
      videoEl.removeAttribute("src");
      videoEl.style.display = "none";
    }
  }

  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  }

  play() {
    const playPromises = Object.values(this.videos).map(v => {
      if (v.src) return v.play().catch(() => {});
      return Promise.resolve();
    });

    Promise.all(playPromises).then(() => {
      this.isPlaying = true;
      this.playBtn.innerHTML = "⏸ Pause";
      this.playBtn.classList.remove("play-btn");
    });
  }

  pause() {
    Object.values(this.videos).forEach(v => {
      if (v.src) v.pause();
    });
    this.isPlaying = false;
    this.playBtn.innerHTML = "▶ Play";
    this.playBtn.classList.add("play-btn");
  }

  seek(seconds) {
    Object.values(this.videos).forEach(v => {
      if (v.src) v.currentTime = seconds;
    });
  }

  seekRelative(delta) {
    const newTime = Math.max(0, (this.videos.front.currentTime || 0) + delta);
    this.seek(newTime);
  }

  setPlaybackRate(rate) {
    Object.values(this.videos).forEach(v => {
      v.playbackRate = rate;
    });
  }

  resyncCheck() {
    const master = this.videos.front.currentTime;
    [this.videos.back, this.videos.left, this.videos.right].forEach(slave => {
      if (slave.src && Math.abs(slave.currentTime - master) > 0.25) {
        slave.currentTime = master;
      }
    });
  }

  toggleSlotZoom(slot) {
    if (this.isSingleMode && this.expandedSlot === slot) {
      // Return to 2x2 grid
      this.gridEl.classList.remove("single-mode");
      slot.classList.remove("expanded");
      this.isSingleMode = false;
      this.expandedSlot = null;
    } else {
      // Zoom this camera slot
      if (this.expandedSlot) this.expandedSlot.classList.remove("expanded");
      this.gridEl.classList.add("single-mode");
      slot.classList.add("expanded");
      this.isSingleMode = true;
      this.expandedSlot = slot;
    }
  }

  toggleGridMode() {
    if (this.isSingleMode) {
      this.gridEl.classList.remove("single-mode");
      if (this.expandedSlot) this.expandedSlot.classList.remove("expanded");
      this.isSingleMode = false;
    }
  }

  advanceNextClip() {
    if (!this.currentClipGroup) return;
    const currentIndex = this.clipGroups.findIndex(g => g.id === this.currentClipGroup.id);
    if (currentIndex >= 0 && currentIndex < this.clipGroups.length - 1) {
      const nextGroup = this.clipGroups[currentIndex + 1];
      this.selectClip(nextGroup);
      this.play();
    }
  }

  formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  window.teslaPlayer = new TeslaPlayer();
});


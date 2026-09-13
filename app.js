const API = "/api/v1";
const RISK_COLOR = {
  "Low": "#10b981",
  "Medium": "#f59e0b",
  "High": "#f97316",
  "Very High": "#ef4444"
};

let map;
let markers = {};
let safeZoneMarkers = {};
let reportMarkers = [];
let routeLine = null;
let selectedLocId = null;
let pendingReportCoords = null;
let META = null;

// ---------------------------------------------------------------------------
// Toast Notification
// ---------------------------------------------------------------------------
function showToast(message, type = "success") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✅" : "⚠️"}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ---------------------------------------------------------------------------
// Audio Voice Alert Playback via Web Speech API
// ---------------------------------------------------------------------------
function playVoiceAlert(text, langCode = "en") {
  if (!("speechSynthesis" in window)) {
    showToast("Speech synthesis is not supported in this browser.", "error");
    return;
  }
  window.speechSynthesis.cancel(); // Stop any previous speech
  const utterance = new SpeechSynthesisUtterance(text);
  
  const langMap = {
    "en": "en-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "as": "as-IN"
  };
  utterance.lang = langMap[langCode] || "en-IN";
  utterance.rate = 0.95; // Slightly slower for emergency broadcast clarity
  utterance.pitch = 1.0;
  
  utterance.onstart = () => {
    showToast(`Playing audio alert (${langCode.toUpperCase()})...`, "success");
  };
  utterance.onerror = (e) => {
    console.warn("TTS error:", e);
    // fallback to English voice if regional language voice is absent
    if (utterance.lang !== "en-US") {
      utterance.lang = "en-US";
      window.speechSynthesis.speak(utterance);
    }
  };
  
  window.speechSynthesis.speak(utterance);
}

// ---------------------------------------------------------------------------
// Leaflet Map Initialization
// ---------------------------------------------------------------------------
function initMap() {
  map = L.map("map", { zoomControl: true }).setView([25.8, 92.8], 7);

  // Free, open-source OpenStreetMap tiles (No API key required)
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; <a href='https://www.openstreetmap.org/copyright'>OpenStreetMap</a> contributors",
    maxZoom: 16
  }).addTo(map);

  // Map Click Handler for Citizen Reports
  map.on("click", (e) => {
    pendingReportCoords = e.latlng;
    document.getElementById("reportCoords").value =
      `${e.latlng.lat.toFixed(4)}° N, ${e.latlng.lng.toFixed(4)}° E`;
    document.getElementById("reportModal").classList.remove("hidden");
  });
}

async function fetchJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// ---------------------------------------------------------------------------
// Load System Metadata & Markers
// ---------------------------------------------------------------------------
async function loadMeta() {
  try {
    META = await fetchJSON(`${API}/meta`);
    
    // Update topbar system summary
    document.getElementById("topbarStats").innerHTML =
      `<b>${META.locations.length} Monitored Sectors</b> · ML Backtest Accuracy: <span style="color:var(--orange-dark); font-weight:800;">${(META.model_backtest_accuracy * 100).toFixed(0)}%</span>`;

    // Populate modal select dropdowns
    const reportSelect = document.getElementById("reportLocationSelect");
    const subSelect = document.getElementById("subLocationSelect");
    
    if (reportSelect && subSelect) {
      const options = META.locations.map(l => `<option value="${l.id}">${l.name} (${l.state})</option>`).join("");
      reportSelect.innerHTML = options;
      subSelect.innerHTML = options;
    }

    // Add village hazard markers
    META.locations.forEach(loc => {
      const marker = L.circleMarker([loc.lat, loc.lng], {
        radius: 12,
        weight: 3,
        color: "#000000",
        fillColor: "#10b981",
        fillOpacity: 0.95
      }).addTo(map);

      marker.bindTooltip(`<b>${loc.name}</b><br><span style="font-size:11px">${loc.state}</span>`, {
        permanent: false,
        direction: "top",
        className: "custom-leaflet-tooltip"
      });

      marker.on("click", (e) => {
        L.DomEvent.stopPropagation(e);
        selectLocation(loc.id);
      });

      markers[loc.id] = marker;
    });

    // Add safe zone markers (Emergency Hospitals / Shelters) - Compact Brutalist Pin
    Object.entries(META.safe_zones).forEach(([id, z]) => {
      const szMarker = L.marker([z.lat, z.lng], {
        icon: L.divIcon({
          className: "",
          html: `<div style="background:#ffffff; border:2px solid #000; border-radius:50%; width:26px; height:26px; display:flex; align-items:center; justify-content:center; font-size:13px; box-shadow:2px 2px 0 #000; cursor:pointer;" title="${z.name}">🏥</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13]
        })
      }).addTo(map).bindTooltip(`<b>🏥 Emergency Safe Zone:</b><br>${z.name}`, {
        direction: "top"
      });
      safeZoneMarkers[id] = szMarker;
    });

  } catch (err) {
    console.error("Failed to load metadata:", err);
  }
}

// ---------------------------------------------------------------------------
// Polling & Refresh Data Feeds
// ---------------------------------------------------------------------------
async function refreshLocations() {
  try {
    const locs = await fetchJSON(`${API}/locations`);
    const rankingEl = document.getElementById("riskRanking");
    const sorted = [...locs].sort((a, b) => b.risk_score - a.risk_score);

    rankingEl.innerHTML = sorted.map(l => `
      <div class="risk-row ${l.id === selectedLocId ? 'active' : ''}" onclick="selectLocation('${l.id}')">
        <div>
          <div class="loc-name">${l.name}</div>
          <div class="loc-sub">${l.state} · Score: ${(l.risk_score * 100).toFixed(0)}%</div>
        </div>
        <span class="badge ${l.risk_level.replace(' ', '-')}">${l.risk_level}</span>
      </div>
    `).join("");

    locs.forEach(l => {
      const m = markers[l.id];
      if (m) {
        m.setStyle({
          fillColor: RISK_COLOR[l.risk_level] || "#10b981",
          color: l.id === selectedLocId ? "#ff6b00" : "#000000",
          weight: l.id === selectedLocId ? 4 : 2.5
        });
        const r = 9 + l.risk_score * 11;
        m.setRadius(r);
      }
    });
  } catch (err) {
    console.error("Failed to refresh locations:", err);
  }
}

async function refreshAlerts() {
  try {
    const alerts = await fetchJSON(`${API}/alerts`);
    const el = document.getElementById("alertsList");
    const countBadge = document.getElementById("alertCountBadge");
    
    if (countBadge) {
      countBadge.textContent = `${alerts.length} LIVE`;
      countBadge.style.background = alerts.length > 0 ? "var(--orange)" : "#000";
    }

    if (!alerts.length) {
      el.innerHTML = `
        <div class="risk-row" style="cursor:default;">
          <span style="font-size:0.8rem; color:var(--text-muted); font-weight:700;">
            🌱 No emergency high-risk alerts currently active across monitored hills.
          </span>
        </div>`;
      return;
    }

    el.innerHTML = alerts.slice(0, 15).map(a => {
      const loc = META ? META.locations.find(l => l.id === a.location_id) : null;
      const t = new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return `
        <div class="risk-row" onclick="selectLocation('${a.location_id}')">
          <div>
            <div class="loc-name">🚨 ${loc ? loc.name : a.location_id}</div>
            <div class="loc-sub">Dispatched: ${t} · Push/SMS</div>
          </div>
          <span class="badge ${a.risk_level.replace(' ', '-')}">${a.risk_level}</span>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to refresh alerts:", err);
  }
}

async function refreshResilience() {
  try {
    const list = await fetchJSON(`${API}/resilience`);
    const el = document.getElementById("resilienceList");
    el.innerHTML = list.map(r => `
      <div class="risk-row" onclick="selectLocation('${r.location_id}')">
        <div>
          <div class="loc-name">${r.name}</div>
          <div class="loc-sub">${r.state}</div>
        </div>
        <div class="resilience-bar-wrap">
          <div class="resilience-bar">
            <div class="resilience-fill" style="width:${r.resilience_score}%;"></div>
          </div>
          <span>${r.resilience_score}</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to refresh resilience:", err);
  }
}

// ---------------------------------------------------------------------------
// Select Location & Render Comprehensive Telemetry
// ---------------------------------------------------------------------------
async function selectLocation(locId) {
  selectedLocId = locId;
  
  // Highlight active row in ranking
  document.querySelectorAll(".risk-row").forEach(r => r.classList.remove("active"));
  
  const detail = document.getElementById("detailPanel");
  detail.innerHTML = `
    <div class="brutal-card">
      <div class="brutal-card-header">
        <span class="brutal-card-title">📡 Processing Sensor Streams...</span>
      </div>
      <p style="font-size:0.8rem; color:var(--text-muted); font-weight:700;">Evaluating slope stability and neural network weights...</p>
    </div>`;

  try {
    const r = await fetchJSON(`${API}/predict/${locId}`);
    renderDetail(r);
    drawEvacuationRoute(locId);
    map.panTo([r.location.lat, r.location.lng], { animate: true, duration: 0.8 });
    refreshLocations();
  } catch (err) {
    console.error("Failed to fetch location prediction:", err);
  }
}

function renderDetail(r) {
  const detail = document.getElementById("detailPanel");
  const ml = r.ml_prediction;
  const s = r.sensor_state;

  // Build Voice Alert Cards with Speech Buttons
  const voiceEntries = Object.entries(r.voice_alert || {});
  let voiceHTML = `<p style="font-size:0.75rem; color:var(--text-muted); font-weight:700;">No voice broadcast triggered at Low risk level.</p>`;
  
  if (voiceEntries.length > 0) {
    voiceHTML = voiceEntries.map(([lang, text]) => `
      <div class="voice-card">
        <div>
          <span class="lang-tag">${lang.toUpperCase()}</span>
          <span class="text">${text}</span>
        </div>
        <button class="voice-play-btn" onclick="playVoiceAlert('${text.replace(/'/g, "\\'")}', '${lang}')" title="Play Broadcast">
          🔊 Hear
        </button>
      </div>
    `).join("");
  }

  detail.innerHTML = `
    <!-- Location Title Card -->
    <div class="brutal-card">
      <div class="detail-header">
        <div class="detail-header-top">
          <div>
            <div class="detail-loc-title">${r.location.name}</div>
            <div style="font-size:0.75rem; color:var(--text-muted); font-family:'JetBrains Mono'; font-weight:700;">
              ${r.location.state} · Slope: ${s.slope_deg.toFixed(1)}°
            </div>
          </div>
          <span class="badge ${ml.risk_level.replace(' ', '-')}">${ml.risk_level}</span>
        </div>
      </div>

      <!-- Live Sensor Telemetry Grid -->
      <span class="section-label">📊 Telemetry Feed (Live Stream)</span>
      <div class="telemetry-grid">
        <div class="telemetry-cell">
          <div class="lbl">Rainfall (24h)</div>
          <div class="val">${s.rainfall_24h.toFixed(1)} mm</div>
        </div>
        <div class="telemetry-cell">
          <div class="lbl">Rainfall (3-Day)</div>
          <div class="val">${s.rainfall_3day.toFixed(1)} mm</div>
        </div>
        <div class="telemetry-cell">
          <div class="lbl">Soil Moisture</div>
          <div class="val">${s.soil_moisture.toFixed(1)} %</div>
        </div>
        <div class="telemetry-cell">
          <div class="lbl">Vegetation Index</div>
          <div class="val">${s.vegetation_index.toFixed(2)}</div>
        </div>
      </div>

      <!-- AI Risk Decomposition -->
      <span class="section-label">🧠 AI Risk Prediction</span>
      <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:0.8rem; font-weight:800;">
        <span>Hazard Probability: <b>${(ml.risk_score * 100).toFixed(1)}%</b></span>
        <span>Confidence: <b>${(ml.confidence * 100).toFixed(0)}%</b></span>
      </div>

      <div style="margin-bottom:10px;">
        ${ml.top_factors.map(f => `
          <div class="factor-item">
            <div class="factor-header">
              <span>${f[0]}</span>
              <span class="font-mono">${(f[1] * 100).toFixed(0)}%</span>
            </div>
            <div class="factor-track">
              <div class="factor-fill" style="width:${Math.min(100, Math.max(5, f[1] * 350))}%;"></div>
            </div>
          </div>
        `).join("")}
      </div>

      <!-- Recommendation & Offline Fallback -->
      <span class="section-label">🛡️ Tactical Response Directives</span>
      <div class="callout-box">
        <b>Direct Action:</b> ${r.recommendation}
      </div>
      <div class="callout-box green-accent">
        <b>Offline Rule Engine:</b> ${r.offline_rule_engine.risk_level} — ${r.offline_rule_engine.reasons.join("; ")}
      </div>

      <!-- Voice Broadcast Preview Deck -->
      <span class="section-label">📢 Multi-Lingual Voice Alerts</span>
      <div class="voice-deck">
        ${voiceHTML}
      </div>
    </div>

    <!-- What-If Simulation Deck -->
    <div class="brutal-card">
      <div class="brutal-card-header">
        <span class="brutal-card-title">🧪 What-If Scenario Simulator</span>
        <span class="brutal-card-badge">F10 ENGINE</span>
      </div>
      
      <div class="slider-group">
        <div class="slider-row">
          <label>Rainfall Δ</label>
          <input type="range" id="simRain" min="-50" max="150" value="0" oninput="simUpdateLabel()">
          <span class="slider-val" id="simRainVal">+0mm</span>
        </div>
        <div class="slider-row">
          <label>Soil Moist. Δ</label>
          <input type="range" id="simSoil" min="-40" max="40" value="0" oninput="simUpdateLabel()">
          <span class="slider-val" id="simSoilVal">+0%</span>
        </div>
        <div class="slider-row">
          <label>Vegetation Δ</label>
          <input type="range" id="simVeg" min="-50" max="50" value="0" oninput="simUpdateLabel()">
          <span class="slider-val" id="simVegVal">+0%</span>
        </div>
      </div>

      <button class="brutal-btn brutal-btn-orange" style="width:100%; justify-content:center;" onclick="runSimulation()">
        ⚡ Run Stress Test Simulation
      </button>
      <div id="simResult"></div>
    </div>

    <!-- Evacuation Route Card -->
    <div class="brutal-card">
      <div class="brutal-card-header">
        <span class="brutal-card-title">🚑 Evacuation Routing</span>
        <span class="brutal-card-badge">DIJKSTRA F8</span>
      </div>
      <div id="evacInfo" style="font-size:0.8rem; line-height:1.4; color:var(--text-muted); font-weight:700;">
        Computing safest corridor bypassing hazard segments...
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// What-If Simulation Handlers
// ---------------------------------------------------------------------------
function simUpdateLabel() {
  const rain = document.getElementById("simRain").value;
  const soil = document.getElementById("simSoil").value;
  const veg = document.getElementById("simVeg").value;
  
  document.getElementById("simRainVal").textContent = `${rain >= 0 ? '+' : ''}${rain}mm`;
  document.getElementById("simSoilVal").textContent = `${soil >= 0 ? '+' : ''}${soil}%`;
  document.getElementById("simVegVal").textContent = `${veg >= 0 ? '+' : ''}${veg}%`;
}

async function runSimulation() {
  if (!selectedLocId) return;
  const rainfall_delta = parseFloat(document.getElementById("simRain").value);
  const soil_delta = parseFloat(document.getElementById("simSoil").value);
  const veg_delta = parseFloat(document.getElementById("simVeg").value) / 100;
  
  try {
    const r = await fetchJSON(`${API}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location_id: selectedLocId, rainfall_delta, soil_delta, veg_delta })
    });
    const ml = r.ml_prediction;
    document.getElementById("simResult").innerHTML = `
      <div class="sim-result-box">
        <b>Projected Risk:</b> <span class="badge ${ml.risk_level.replace(' ', '-')}">${ml.risk_level}</span>
        <b>Score: ${(ml.risk_score * 100).toFixed(1)}%</b>
      </div>
    `;
    showToast(`Simulation Complete: ${ml.risk_level} Risk (${(ml.risk_score * 100).toFixed(0)}%)`, "success");
  } catch (err) {
    showToast("Simulation failed to execute.", "error");
  }
}

// ---------------------------------------------------------------------------
// Dynamic Evacuation Route Drawing
// ---------------------------------------------------------------------------
async function drawEvacuationRoute(locId) {
  try {
    const route = await fetchJSON(`${API}/evacuate?location_id=${locId}`);
    if (routeLine) map.removeLayer(routeLine);

    const latlngs = route.route_coords.map(c => [c.lat, c.lng]);
    routeLine = L.polyline(latlngs, {
      color: "#ef7618",
      weight: 5,
      dashArray: "8 8",
      lineCap: "round",
      opacity: 0.95
    }).addTo(map);

    const info = document.getElementById("evacInfo");
    if (info) {
      info.innerHTML = `
        <div style="background:#f0fdf4; border:1.5px solid #000; border-radius:6px; padding:8px; box-shadow:1px 1px 0 #000;">
          <div style="font-weight:900; color:#000; margin-bottom:4px;">🏥 Nearest Safe Zone: ${route.to_safe_zone.name}</div>
          <div>📏 Distance: <b>${route.estimated_distance_km} km</b> · ⏱️ Terrain ETA: <b>${route.estimated_time_min} mins</b></div>
          <div style="font-size:0.72rem; color:var(--green-dark); font-weight:800; margin-top:4px;">✓ ${route.risk_avoided}</div>
        </div>
      `;
    }
  } catch (e) {
    console.warn("No route found:", e);
    const info = document.getElementById("evacInfo");
    if (info) info.innerHTML = `<span>No reachable safe zone within current graph.</span>`;
  }
}

// ---------------------------------------------------------------------------
// Incident Report Modal Logic
// ---------------------------------------------------------------------------
function openReportModalDirect() {
  if (selectedLocId && META) {
    const loc = META.locations.find(l => l.id === selectedLocId);
    if (loc) {
      pendingReportCoords = { lat: loc.lat, lng: loc.lng };
      document.getElementById("reportCoords").value = `${loc.lat.toFixed(4)}° N, ${loc.lng.toFixed(4)}° E`;
      document.getElementById("reportLocationSelect").value = selectedLocId;
    }
  } else {
    pendingReportCoords = { lat: 25.8, lng: 92.8 };
    document.getElementById("reportCoords").value = "25.8000° N, 92.8000° E";
  }
  document.getElementById("reportModal").classList.remove("hidden");
}

function closeReportModal() {
  document.getElementById("reportModal").classList.add("hidden");
}

async function submitReport() {
  if (!pendingReportCoords) return;
  const desc = document.getElementById("reportDesc").value.trim();
  if (!desc) {
    showToast("Please provide a short incident description.", "error");
    return;
  }
  const body = {
    location_id: document.getElementById("reportLocationSelect").value || selectedLocId || "L01",
    lat: pendingReportCoords.lat,
    lng: pendingReportCoords.lng,
    description: desc,
    reported_severity: document.getElementById("reportSeverity").value,
    media_url: document.getElementById("reportMedia").value.trim()
  };

  try {
    const res = await fetchJSON(`${API}/reports`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    const marker = L.marker([body.lat, body.lng], {
      icon: L.divIcon({
        className: "",
        html: `<div style="background:#f97316; border:2px solid #000; border-radius:50%; width:26px; height:26px; display:flex; align-items:center; justify-content:center; box-shadow:2px 2px 0 #000; font-size:14px;">📍</div>`,
        iconSize: [26, 26],
        iconAnchor: [13, 13]
      })
    }).addTo(map).bindPopup(`
      <div style="font-family:'Plus Jakarta Sans'; font-size:12px;">
        <b style="color:#c2410c;">📸 CITIZEN INCIDENT REPORT</b><br>
        <b>Severity:</b> ${body.reported_severity}<br>
        <b>Details:</b> ${body.description}
        ${res.auto_verified ? "<br><b style='color:#15803d;'>✓ Auto-Verified by Command Center</b>" : ""}
      </div>
    `);

    reportMarkers.push(marker);
    closeReportModal();
    document.getElementById("reportDesc").value = "";
    document.getElementById("reportMedia").value = "";
    showToast("Incident report logged & geotagged successfully!", "success");
  } catch (err) {
    showToast("Failed to submit report. Try again.", "error");
  }
}

// ---------------------------------------------------------------------------
// Emergency Alerts Subscription Modal Logic
// ---------------------------------------------------------------------------
function openSubscribeModal() {
  if (selectedLocId) {
    document.getElementById("subLocationSelect").value = selectedLocId;
  }
  document.getElementById("subscribeModal").classList.remove("hidden");
}

function closeSubscribeModal() {
  document.getElementById("subscribeModal").classList.add("hidden");
}

async function submitSubscription() {
  const phone = document.getElementById("subPhone").value.trim();
  if (phone.length < 8) {
    showToast("Please enter a valid mobile number.", "error");
    return;
  }
  const body = {
    phone: phone,
    location_id: document.getElementById("subLocationSelect").value,
    language: document.getElementById("subLanguage").value,
    voice_enabled: document.getElementById("subVoiceEnabled").checked
  };

  try {
    await fetchJSON(`${API}/subscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    closeSubscribeModal();
    showToast(`Subscribed ${phone} for emergency broadcasts!`, "success");
  } catch (err) {
    showToast("Failed to subscribe phone number.", "error");
  }
}

// ---------------------------------------------------------------------------
// Specialized NER Disaster AI Chatbot (Pahar-Mitra) Logic & Drag Handlers
// ---------------------------------------------------------------------------
let isDragging = false;
let dragStartX = 0;
let launcherStartX = 0;
let currentChatDock = "left"; // "left", "center", "right"

function handleLauncherClick(e) {
  if (isDragging) return;
  toggleChatDrawer();
}

function cycleChatDockPosition(e) {
  if (e) e.stopPropagation();
  const launcher = document.getElementById("chatLauncher");
  const drawer = document.getElementById("chatDrawer");
  
  if (currentChatDock === "left") {
    currentChatDock = "center";
    const centerPos = Math.max(20, (window.innerWidth / 2) - 200);
    launcher.style.left = `${centerPos}px`;
    launcher.style.right = "auto";
    drawer.style.left = `${centerPos}px`;
    drawer.style.right = "auto";
    showToast("Chatbot position: Center", "success");
  } else if (currentChatDock === "center") {
    currentChatDock = "right";
    const rightPos = Math.max(20, window.innerWidth - 440);
    launcher.style.left = `${rightPos}px`;
    launcher.style.right = "auto";
    drawer.style.left = `${rightPos}px`;
    drawer.style.right = "auto";
    showToast("Chatbot position: Right", "success");
  } else {
    currentChatDock = "left";
    launcher.style.left = "340px";
    launcher.style.right = "auto";
    drawer.style.left = "340px";
    drawer.style.right = "auto";
    showToast("Chatbot position: Left (Evacuation route clear)", "success");
  }
}

function initChatDraggables() {
  const launcher = document.getElementById("chatLauncher");
  const dragHeader = document.getElementById("chatDragHeader");
  const drawer = document.getElementById("chatDrawer");

  if (!launcher || !dragHeader) return;

  // Make Launcher Horizontally Draggable
  let launcherMoved = false;
  launcher.addEventListener("pointerdown", (e) => {
    isDragging = false;
    launcherMoved = false;
    dragStartX = e.clientX;
    launcherStartX = launcher.offsetLeft;
    
    function onPointerMove(ev) {
      const dx = ev.clientX - dragStartX;
      if (Math.abs(dx) > 4) {
        isDragging = true;
        launcherMoved = true;
        const newLeft = Math.max(10, Math.min(window.innerWidth - launcher.offsetWidth - 10, launcherStartX + dx));
        launcher.style.left = `${newLeft}px`;
        launcher.style.right = "auto";
        if (drawer) {
          drawer.style.left = `${Math.max(10, Math.min(window.innerWidth - drawer.offsetWidth - 10, newLeft))}px`;
          drawer.style.right = "auto";
        }
      }
    }

    function onPointerUp() {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      setTimeout(() => { isDragging = false; }, 50);
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  });

  // Make Drawer Header Horizontally Draggable
  dragHeader.addEventListener("pointerdown", (e) => {
    if (e.target.tagName === "BUTTON") return;
    const drawerStartX = drawer.offsetLeft;
    const startX = e.clientX;

    function onHeaderMove(ev) {
      const dx = ev.clientX - startX;
      const newLeft = Math.max(10, Math.min(window.innerWidth - drawer.offsetWidth - 10, drawerStartX + dx));
      drawer.style.left = `${newLeft}px`;
      drawer.style.right = "auto";
      if (launcher) {
        launcher.style.left = `${newLeft}px`;
        launcher.style.right = "auto";
      }
    }

    function onHeaderUp() {
      window.removeEventListener("pointermove", onHeaderMove);
      window.removeEventListener("pointerup", onHeaderUp);
    }

    window.addEventListener("pointermove", onHeaderMove);
    window.addEventListener("pointerup", onHeaderUp);
  });
}

function toggleChatDrawer() {
  const drawer = document.getElementById("chatDrawer");
  drawer.classList.toggle("hidden");
  if (!drawer.classList.contains("hidden")) {
    updateChatLocationContext();
    document.getElementById("chatInput").focus();
  }
}

function updateChatLocationContext() {
  const locEl = document.getElementById("chatActiveLoc");
  if (selectedLocId && META) {
    const loc = META.locations.find(l => l.id === selectedLocId);
    if (loc) {
      locEl.textContent = `${loc.name} (${loc.state})`;
      return;
    }
  }
  locEl.textContent = "North-East Region (General)";
}

function sendQuickPrompt(promptText) {
  document.getElementById("chatInput").value = promptText;
  sendChatMessage();
}

function formatMarkdownReply(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.*?)\*/g, '<i>$1</i>')
    .replace(/•\s/g, '• ')
    .replace(/\n/g, '<br>');
}

async function sendChatMessage() {
  const input = document.getElementById("chatInput");
  const msgText = input.value.trim();
  if (!msgText) return;

  const msgsContainer = document.getElementById("chatMessages");

  // Append user message
  const userWrapper = document.createElement("div");
  userWrapper.className = "msg-wrapper user";
  userWrapper.innerHTML = `<div class="msg-bubble">${msgText}</div>`;
  msgsContainer.appendChild(userWrapper);
  input.value = "";
  msgsContainer.scrollTop = msgsContainer.scrollHeight;

  // Append typing indicator
  const botWrapper = document.createElement("div");
  botWrapper.className = "msg-wrapper bot";
  const typingId = "typing_" + Date.now();
  botWrapper.innerHTML = `<div class="msg-bubble" id="${typingId}"><i>Consulting NER Geological & Disaster Protocols...</i></div>`;
  msgsContainer.appendChild(botWrapper);
  msgsContainer.scrollTop = msgsContainer.scrollHeight;

  try {
    const res = await fetchJSON(`${API}/chatbot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: msgText,
        location_id: selectedLocId,
        language: "en"
      })
    });

    const replyEl = document.getElementById(typingId);
    if (replyEl) {
      replyEl.innerHTML = formatMarkdownReply(res.reply);
      
      // Clean speech text for TTS
      const cleanSpeech = res.reply
        .replace(/[*#•_]/g, '')
        .replace(/🚨|⚠️|🛑|🚗|🎒|🛡️|🌧️|📍|✓/g, '')
        .slice(0, 260); // Read first crucial sentences

      const ttsBtn = document.createElement("button");
      ttsBtn.className = "msg-tts-btn";
      ttsBtn.textContent = "🔊 Listen";
      ttsBtn.onclick = () => playVoiceAlert(cleanSpeech, 'en');
      botWrapper.appendChild(ttsBtn);
    }
  } catch (err) {
    const replyEl = document.getElementById(typingId);
    if (replyEl) {
      replyEl.innerHTML = `⚠️ <b>Offline Emergency Advisory:</b> For immediate landslide assistance in North-East India, contact NDRF at <b>1078</b> or Emergency Services at <b>112</b>.`;
    }
  }
  msgsContainer.scrollTop = msgsContainer.scrollHeight;
}

// ---------------------------------------------------------------------------
// Neo-Brutalist Custom Cursor & Interactive Click Particle System
// ---------------------------------------------------------------------------
function initCustomCursor() {
  const dot = document.getElementById("cursorDot");
  const ring = document.getElementById("cursorRing");
  if (!dot || !ring || window.matchMedia("(hover: none)").matches) return;

  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;
  let ringX = mouseX;
  let ringY = mouseY;

  window.addEventListener("pointermove", (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    dot.style.transform = `translate(${mouseX}px, ${mouseY}px) translate(-50%, -50%)`;
  });

  // Smooth Ring Follower Animation Loop
  function renderCursor() {
    ringX += (mouseX - ringX) * 0.22;
    ringY += (mouseY - ringY) * 0.22;
    ring.style.transform = `translate(${ringX}px, ${ringY}px) translate(-50%, -50%)`;
    requestAnimationFrame(renderCursor);
  }
  requestAnimationFrame(renderCursor);

  // Hover Effect on Clickable Elements
  document.addEventListener("mouseover", (e) => {
    const target = e.target.closest("button, a, input, select, textarea, .risk-row, .chip-btn, .brand-badge, .voice-play-btn, [onclick], .leaflet-interactive");
    if (target) {
      ring.classList.add("hovered");
    } else {
      ring.classList.remove("hovered");
    }
  });

  // Down/Up Press Squish
  window.addEventListener("pointerdown", () => {
    ring.classList.add("active");
  });
  window.addEventListener("pointerup", () => {
    ring.classList.remove("active");
  });

  // Comic Neo-Brutalist Click Burst Effect
  const CLICK_WORDS = ["💥 POP!", "⚡ CLICK", "🎯 TARGET", "🚨 SOS", "✓ LOGGED", "📡 SYNC", "🏔️ NER"];
  window.addEventListener("click", (e) => {
    const burst = document.createElement("div");
    const isGreen = Math.random() > 0.5;
    burst.className = `click-burst ${isGreen ? 'green-burst' : ''}`;
    const word = CLICK_WORDS[Math.floor(Math.random() * CLICK_WORDS.length)];
    burst.textContent = word;
    burst.style.left = `${e.clientX}px`;
    burst.style.top = `${e.clientY}px`;
    document.body.appendChild(burst);

    setTimeout(() => {
      burst.remove();
    }, 400);
  });
}

// ---------------------------------------------------------------------------
// Top-Left Theme Switcher & Refresh Mode Animation
// ---------------------------------------------------------------------------
function triggerThemeRefresh() {
  const overlay = document.getElementById('themeRefreshOverlay');
  const btn = document.getElementById('themeToggleBtn');
  const popupTitle = document.getElementById('refreshTitleText');
  const popupSub = document.getElementById('refreshSubText');

  if (btn) btn.classList.add('refreshing');

  const isDarkCurrently = document.documentElement.classList.contains('theme-bluish-dark');
  const targetThemeName = isDarkCurrently ? "Classic Orange & Green" : "Classy Dark Bluish";

  if (popupTitle) popupTitle.textContent = `REFRESHING THEME...`;
  if (popupSub) popupSub.textContent = `Morphing UI to ${targetThemeName}`;

  if (overlay) overlay.classList.add('active');

  setTimeout(() => {
    if (isDarkCurrently) {
      document.documentElement.classList.remove('theme-bluish-dark');
      if (document.body) document.body.classList.remove('theme-bluish-dark');
      localStorage.setItem('ner_vision_theme', 'light-orange-green');
    } else {
      document.documentElement.classList.add('theme-bluish-dark');
      if (document.body) document.body.classList.add('theme-bluish-dark');
      localStorage.setItem('ner_vision_theme', 'bluish-dark');
    }

    updateThemeToggleUI();

    const layout = document.querySelector('main') || document.body;
    layout.classList.add('theme-refresh-wave');
    setTimeout(() => layout.classList.remove('theme-refresh-wave'), 650);

  }, 350);

  setTimeout(() => {
    if (overlay) overlay.classList.remove('active');
    if (btn) btn.classList.remove('refreshing');
    
    if (typeof showToast === 'function') {
      showToast(`Theme Refreshed to ${targetThemeName} 🚀`, "success");
    }
  }, 750);
}

function updateThemeToggleUI() {
  const isDark = document.documentElement.classList.contains('theme-bluish-dark');
  const btns = document.querySelectorAll('.top-left-theme-btn');
  btns.forEach(btn => {
    const label = btn.querySelector('.btn-text');
    const icon = btn.querySelector('.refresh-icon-spin');
    if (label) label.textContent = isDark ? "Classic Mode" : "Dark Blue Mode";
    if (icon) icon.textContent = isDark ? "☀️" : "🌌";
  });
}

function initTheme() {
  const savedTheme = localStorage.getItem('ner_vision_theme');
  if (savedTheme === 'bluish-dark') {
    document.documentElement.classList.add('theme-bluish-dark');
    if (document.body) document.body.classList.add('theme-bluish-dark');
  } else {
    document.documentElement.classList.remove('theme-bluish-dark');
    if (document.body) document.body.classList.remove('theme-bluish-dark');
  }
  updateThemeToggleUI();
}

(function prebootTheme() {
  const savedTheme = localStorage.getItem('ner_vision_theme');
  if (savedTheme === 'bluish-dark') {
    document.documentElement.classList.add('theme-bluish-dark');
  }
})();

// ---------------------------------------------------------------------------
// Periodic Polling & App Bootstrap
// ---------------------------------------------------------------------------
async function poll() {
  await Promise.all([refreshLocations(), refreshAlerts(), refreshResilience()]);
}

(async function boot() {
  initTheme();
  initMap();
  await loadMeta();
  await poll();
  initChatDraggables();
  initCustomCursor();
  if (META && META.locations.length) {
    selectLocation(META.locations[0].id);
  }
  setInterval(poll, 6000); // 6s reactive refresh
})();



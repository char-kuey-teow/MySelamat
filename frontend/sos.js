/* ======== CONFIG ======== */
const FRI_SOURCE = "./mocks/fri.latest.json";       // disaster polygons (optional gate)
const USE_ZONE_GATE = false;                         // set true if you want zone check now
// ---- MOCK LOCATION (toggle for demo) ----
const USE_FAKE_LOCATION = true; // set false to use real GPS
const FAKE_COORDS = { lat: 6.1248, lng: 102.2542 }; // Kampung Badang

/* ======== STATE ======== */
let isHolding = false;
let holdTimer = null;
let selectedIncident = null;
let lastFix = null;
let lastAddress = null;
let disasterPolygons = []; // [{level, coords:[[lng,lat]...]}]
let geocoder;

/* ======== INIT ======== */
// Will be called by the Google Maps script when it’s fully loaded
function onGoogleMapsReady() {
  // you now have google.maps.* available
  geocoder = new google.maps.Geocoder();
  wireSOSHold();
  wireIncidentButtons();
  if (USE_ZONE_GATE) loadDisasterPolygons(); // no await needed here
}
// expose it globally for the callback=onGoogleMapsReady
window.onGoogleMapsReady = onGoogleMapsReady;


/* ======== HOLD LOGIC ======== */
function wireSOSHold() {
  const sosBtn = document.querySelector(".sos-button");
  const statusEl = byId("sos-status");
  const errorEl  = byId("sos-error");
  const options  = byId("incident-options");

  const startHold = () => {
    if (isHolding) return;
    isHolding = true;
    errorEl.style.display = "none";
    statusEl.style.display = "block";
    statusEl.textContent  = "Holding… keep pressing to confirm";

    holdTimer = setTimeout(() => {
      // reveal incident choices after 3s
      statusEl.textContent = "Choose your incident type";
      options.style.display = "block";
    }, 3000);
  };

  const cancelHold = () => {
    if (!isHolding) return;
    isHolding = false;
    clearTimeout(holdTimer);
    // keep status hidden if user didn’t reach 3s
    if (options.style.display !== "block") statusEl.style.display = "none";
  };

  sosBtn.addEventListener("pointerdown", startHold);
  sosBtn.addEventListener("pointerup", cancelHold);
  sosBtn.addEventListener("pointerleave", cancelHold);
  sosBtn.addEventListener("pointercancel", cancelHold);
}

/* ======== INCIDENT BUTTONS ======== */
function wireIncidentButtons() {
  const options = byId("incident-options");
  const statusEl = byId("sos-status");

  options.querySelectorAll(".action-button").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (btn.classList.contains("push-to-talk")) {
        flashStatus("🎤 Voice note not implemented in this demo");
        return;
      }
      selectedIncident = btn.textContent.trim();
      flashStatus(`Selected: ${selectedIncident}`);
      // proceed to collect location + address and show summary
      try {
        lastFix = await getLocationFix();
        lastAddress = await reverseGeocode(lastFix.lat, lastFix.lng);

        if (USE_ZONE_GATE) {
          const inZone = await checkInZone([lastFix.lng, lastFix.lat]);
          if (!inZone) {
            showError("Outside verified disaster zone. SOS disabled.");
            return;
          }
        }

        showBottomRightSummary({
          incident: selectedIncident,
          location: {
            lat: lastFix.lat,
            lng: lastFix.lng,
            address: lastAddress
          },
          timestamp: new Date().toISOString()
        });

        statusEl.textContent = "✅ SOS prepared (demo). Ready to send to authority.";
      } catch (e) {
        console.error(e);
        showError("Failed to get your location. Please try again.");
      }
    });
  });
}

/* ======== GEO ======== */
async function getLocationFix() {
  // Use mock instantly if enabled
  if (typeof USE_FAKE_LOCATION !== "undefined" && USE_FAKE_LOCATION) {
    return { lat: FAKE_COORDS.lat, lng: FAKE_COORDS.lng, accuracy: 15 };
  }

  // Try real GPS
  const pos = await new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("Geolocation not supported"));
    navigator.geolocation.getCurrentPosition(
      resolve,
      err => reject(new Error(`Geolocation failed: ${err.code} ${err.message}`)),
      { enableHighAccuracy: true, timeout: 8000, maximumAge: 1000 }
    );
  }).catch(err => {
    console.warn("[GPS] primary failed -> falling back to fake coords", err);
    if (typeof FAKE_COORDS !== "undefined") {
      return { coords: { latitude: FAKE_COORDS.lat, longitude: FAKE_COORDS.lng, accuracy: 15 } };
    }
    throw err;
  });

  // Normalize
  if ("coords" in pos) {
    return {
      lat: pos.coords.latitude,
      lng: pos.coords.longitude,
      accuracy: pos.coords.accuracy
    };
  }
  return pos; // already the normalized fake object
}


function reverseGeocode(lat, lng) {
  return new Promise((resolve) => {
    geocoder.geocode({ location: { lat, lng } }, (results, status) => {
      if (status === "OK" && results && results[0]) resolve(results[0].formatted_address);
      else resolve("(address unavailable)");
    });
  });
}

/* ======== OPTIONAL: ZONE GATE ======== */
async function loadDisasterPolygons() {
  try {
    const res = await fetch(FRI_SOURCE);
    const arr = await res.json(); // [{polygon:[[[lng,lat]...]]}]
    disasterPolygons = arr.map(x => ({ level: x.level, coords: x.polygon[0] }));
  } catch (e) {
    console.warn("FRI load failed; zone gate disabled", e);
    disasterPolygons = [];
  }
}
async function checkInZone([lng, lat]) {
  if (!disasterPolygons.length) return true; // allow if no data
  return disasterPolygons.some(p => pointInPolygon([lng, lat], p.coords));
}
function pointInPolygon([x, y], vs) {
  let inside = false;
  for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
    const [xi, yi] = vs[i];
    const [xj, yj] = vs[j];
    const intersect = ((yi > y) !== (yj > y)) && (x < ((xj - xi) * (y - yi)) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

/* ======== UI HELPERS ======== */
function byId(id){ return document.getElementById(id); }
function flashStatus(msg){ const el=byId("sos-status"); el.textContent=msg; el.style.display="block"; byId("sos-error").style.display="none"; }
function showError(msg){ const el=byId("sos-error"); el.textContent=msg; el.style.display="block"; byId("sos-status").style.display="none"; }

/* ======== SUMMARY BOX ======== */
function showBottomRightSummary(payload) {
  const box = byId("sos-result");
  box.innerHTML = `
    <b>🚨 SOS</b><br/>
    Incident: ${payload.incident}<br/>
    Lat: ${payload.location.lat.toFixed(4)}, Lng: ${payload.location.lng.toFixed(4)}<br/>
    ${payload.location.address}<br/>
    Time: ${new Date(payload.timestamp).toLocaleString()}
  `;
  box.style.display = "block";
}

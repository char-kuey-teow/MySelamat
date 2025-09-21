/* ================== CONFIG ================== */
const FIRE_STATION_NAME = "Balai Bomba & Penyelamat Kota Bharu (Jln Long Yunus)";
const DEFAULT_CENTER = { lat: 6.126562, lng: 102.257086 };
// Put near the top with your CONFIG:
const API_BASE = "http://localhost:3000"; // Express API base when using Live Server

const SOURCES = {
  fri: "./mocks/fri.latest.json"        // [{districtId, level, polygon:[[[lng,lat]...]]}]
};

const MOCKS = {
  incidents: "./mocks/sos-list.json",   // [{id, incident, location:{lat,lng}, address, ts}]
  hazards:   "./mocks/hazards.geojson"  // GeoJSON Polygon features
};

/* ================== STATE ================== */
let map, dirSvc, dirRenderer, geocoder;
let hazardPolys = [];      // <- IMPORTANT: keep all risk polygons here (FRI + hazards)
let incidentData = [];
let fireStation = null;

/* ================== INIT ================== */
window.initMap = async function initMap(){
  map = new google.maps.Map(document.getElementById("map"), {
    center: DEFAULT_CENTER,
    zoom: 12,
    mapTypeControl: false,
  });

  geocoder = new google.maps.Geocoder();
  dirSvc = new google.maps.DirectionsService();
  dirRenderer = new google.maps.DirectionsRenderer({
    map, suppressMarkers: false, polylineOptions: { strokeWeight: 5 }
  });

  // reset polygons ONCE, then load both sources
  hazardPolys = [];
  await Promise.all([
    ensureFireStation(),
    loadFRI(),
    loadHazards(),
    loadIncidents()
  ]);

  renderLegend();
  wireUI();

  if (fireStation) {
    map.setCenter({lat: fireStation.lat, lng: fireStation.lng});
    new google.maps.Marker({
      map,
      position: {lat: fireStation.lat, lng: fireStation.lng},
      title: fireStation.name,
      icon: {
        path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
        scale: 5, fillColor:"#d32f2f", fillOpacity:1, strokeColor:"#7f0000"
      }
    });
  }
};

/* ================== LOADERS ================== */
async function ensureFireStation(){
  fireStation = null;
  try {
    const res = await geocodeAddress(FIRE_STATION_NAME);
    if (res) fireStation = { name: FIRE_STATION_NAME, lat: res.lat, lng: res.lng };
    else toast("Could not geocode fire station – using fallback center.");
  } catch(e) { console.warn("Geocode failed", e); }
}

async function loadFRI(){
  try {
    const arr = await fetch(SOURCES.fri).then(r=>r.json());
    (arr || []).forEach(d=>{
      if (!d.polygon || !Array.isArray(d.polygon) || !Array.isArray(d.polygon[0])) {
        console.warn("Skipping invalid FRI polygon", d);
        return;
      }
      const path = d.polygon[0].map(([lng,lat])=>({lat,lng}));
      if (!path.length) return;
      const poly = new google.maps.Polygon({
        map,
        paths: path,
        strokeOpacity:.9,
        strokeWeight:1,
        strokeColor: strokeForLevel(d.level),
        fillColor:   fillForLevel(d.level),
        fillOpacity: .20
      });
      poly._level = d.level || "GREEN";
      hazardPolys.push(poly);
    });
  } catch(e){
    console.warn("FRI load failed", e);
  }
}

async function loadHazards(){
  try {
    const gj = await fetch(MOCKS.hazards).then(r=>r.json());
    (gj.features || []).forEach(f=>{
      if(f.geometry?.type !== "Polygon") return;
      const path = f.geometry.coordinates[0].map(([lng,lat])=>({lat,lng}));
      const poly = new google.maps.Polygon({
        map, paths: path,
        strokeColor:"#0D47A1", strokeOpacity:.9, strokeWeight:1,
        fillColor:"#1565C0", fillOpacity:.22
      });
      poly._level = f.properties?.level || "FLOOD";
      hazardPolys.push(poly); // append (do NOT reset)
    });
  } catch(e) {
    console.warn("hazards.geojson not found", e);
  }
}

async function loadIncidents(){
  try {
    incidentData = await fetch(MOCKS.incidents).then(r=>r.json());
    renderIncidents();
  } catch(e) {
    incidentData = [];
  }
}

/* ================== UI ================== */
function wireUI(){
  const reload = document.getElementById("reloadIncidents");
  if (reload) reload.onclick = loadIncidents;

  const filter = document.getElementById("filter");
  if (filter) filter.addEventListener("input", ()=> renderIncidents(filter.value.trim().toLowerCase()));

  // NEW: SOS button
  const sosBtn = document.getElementById("sosBtn");
  if (sosBtn) {
    sosBtn.addEventListener("click", sendSOS);
  }
}

function renderLegend(){
  const el = document.getElementById("legend");
  if (!el) return;
  el.innerHTML = `
    <div class="row"><span class="dot" style="background:#1565C0"></span>Flood polygon</div>
    <div class="row"><span class="dot" style="background:#43a047"></span>Selected route (safest)</div>
    <div class="row"><span class="dot" style="background:#d32f2f"></span>Fire Station</div>
  `;
}

function renderIncidents(q=""){
  const box = document.getElementById("incidents");
  if (!box) return;
  box.innerHTML = "";
  incidentData
    .filter(i => !q || (i.incident?.toLowerCase().includes(q) || i.address?.toLowerCase().includes(q)))
    .forEach(i=>{
      const el = document.createElement("div");
      el.className = "card";
      el.innerHTML = `
        <h4>${i.incident || "Incident"}</h4>
        <div class="small">${i.address || (i.location?.lat.toFixed(4)+", "+i.location?.lng.toFixed(4))}</div>
        <div class="row" style="margin-top:8px;">
          <button class="btn" data-id="${i.id}">Route from Fire Station</button>
        </div>
      `;
      el.querySelector("button").onclick = ()=> onRouteFromStation(i);
      box.appendChild(el);
    });
  if(!box.children.length) box.innerHTML = `<div class="muted small">No incidents</div>`;
}

/* ================== CORE: ROUTE (robust) ================== */
async function onRouteFromStation(incident){
  if (!fireStation) { toast("Fire station not set."); return; }
  if (!incident?.location?.lat || !incident?.location?.lng) {
    toast("Incident has no coordinates."); return;
  }

  const origin = new google.maps.LatLng(fireStation.lat, fireStation.lng);
  const dest   = new google.maps.LatLng(incident.location.lat, incident.location.lng);

  const req = {
    origin,
    destination: dest,
    travelMode: google.maps.TravelMode.DRIVING,
    provideRouteAlternatives: true,
    drivingOptions: { departureTime: new Date(), trafficModel: "bestguess" }
  };

  dirSvc.route(req, (res, status) => {
    if (status !== "OK" || !res?.routes?.length) {
      toast("Routing failed: " + status);
      return;
    }

    // Safely decode each route to a list of LatLngs, then score
    const scored = res.routes.map(r => {
      const pts = decodeRouteToPath(r);
      const hitCount = countHazardHits(pts);
      return { route: r, hits: hitCount, pts };
    }).sort((a,b) => a.hits - b.hits);

    const best = scored[0];
    if (!best?.pts?.length) {
      toast("No polyline available for this route.");
      return;
    }

    // Render only the best route
    const resultForRenderer = { ...res, routes: [best.route] };
    dirRenderer.setDirections(resultForRenderer);

    const leg = best.route.legs?.[0];
    const info = document.getElementById("routeInfo");
    if (info && leg) {
      info.classList.remove("muted");
      info.innerHTML = `
        <div><b>From:</b> ${fireStation.name}</div>
        <div><b>To:</b> ${incident.incident ?? ""} ${incident.address ? "– " + incident.address : ""}</div>
        <div><b>ETA:</b> ${leg.duration?.text ?? "?"} &nbsp; <b>Distance:</b> ${leg.distance?.text ?? "?"}</div>
        <div class="small ${best.hits>0?'':'muted'}">
          ${best.hits>0 ? `⚠️ Flood proximity detected at ${best.hits} sampled points. Chosen least-risk route.` : `✅ No flood overlap detected in samples.`}
        </div>
      `;
    }

    // Fit map to route bounds
    const b = new google.maps.LatLngBounds();
    best.pts.forEach(p => b.extend(p));
    map.fitBounds(b, 60);
  });
}

/* Decode a route to a LatLng[] safely */
function decodeRouteToPath(route){
  try {
    if (route?.overview_polyline?.points) {
      return google.maps.geometry.encoding.decodePath(route.overview_polyline.points);
    }
    const steps = route?.legs?.[0]?.steps || [];
    const out = [];
    steps.forEach(s => {
      if (s.polyline?.points) {
        const seg = google.maps.geometry.encoding.decodePath(s.polyline.points);
        out.push(...seg);
      }
    });
    return out;
  } catch (e) {
    console.warn("decodeRouteToPath failed", e);
    return [];
  }
}

/* ================== HAZARD CHECKING ================== */
function countHazardHits(pathPoints){
  if(!hazardPolys.length || !pathPoints?.length) return 0;
  const step = Math.max(1, Math.floor(pathPoints.length / 100)); // up to 100 checks
  let hits = 0;
  for(let i=0; i<pathPoints.length; i+=step){
    const pt = pathPoints[i];
    if(pointInAnyPolygon(pt)) hits++;
  }
  return hits;
}
function pointInAnyPolygon(latlng){
  return hazardPolys.some(poly => google.maps.geometry.poly.containsLocation(latlng, poly));
}

/* ================== SOS (NEW) ================== */
async function sendSOS() {
  // (Optional) keep these hardcoded or wire to inputs later
  const payload = {
    userId: "pak-abu-001",
    location: "Kuala Terengganu",
    context: "Flooded roads and rising water"
  };

  try {
    // If you’re using Live Server, set API_BASE = "http://localhost:3000" near the top of the file
    const res = await fetch((typeof API_BASE !== "undefined" ? `${API_BASE}` : "") + "/sos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    // If backend doesn’t respond 2xx, quietly bail
    if (!res.ok) return;

    // Success → update the UI (keep this if you still want success output)
    const data = await res.json();
    const out = document.getElementById("sosOut");
    if (out) {
      out.classList.remove("muted");
      out.style.whiteSpace = "pre-wrap";
      out.textContent = [
        `Agency: ${data.agency}  •  Priority: ${data.priority}`,
        `Alert: ${data.alert}`,
        `Route: ${data.route?.from} → ${data.route?.to} (${(data.route?.steps||[]).join(" → ")})`
      ].join("\n");
    }
    // If you also want silence on success, remove the block above.
  } catch (_) {
    // Network/CORS/timeout errors → do nothing (silent)
    return;
  }
}


/* ================== UTILS ================== */
function toast(msg){
  const t = document.getElementById("toast");
  if (!t) return;
  t.textContent = msg; t.style.display = "block";
  setTimeout(()=> t.style.display="none", 2500);
}

function geocodeAddress(query){
  return new Promise((resolve) => {
    geocoder.geocode({ address: query }, (results, status) => {
      if (status === "OK" && results && results[0]) {
        const loc = results[0].geometry.location;
        resolve({ lat: loc.lat(), lng: loc.lng() });
      } else resolve(null);
    });
  });
}

/* ====== Color helpers for FRI levels ====== */
function fillForLevel(l){
  if (l==='RED') return '#d32f2f';
  if (l==='ORANGE') return '#f57c00';
  if (l==='YELLOW') return '#fbc02d';
  return '#43a047';
}
function strokeForLevel(l){
  if (l==='RED') return '#b71c1c';
  if (l==='ORANGE') return '#e65100';
  if (l==='YELLOW') return '#f9a825';
  return '#2e7d32';
}

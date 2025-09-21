  const USE_MOCKS = true;  // set false when backend is ready
  const API_BASE  = "http://localhost:3001"; // for later when you have a backend
  const MOCK_PATH = "../mocks"; 
  const DEFAULT_CENTER = { lat: 6.129, lng: 102.243 }; //Kota Bharu
  const USE_FAKE_USER_LOC = true;
  const FAKE_USER_LOC = { lat: 6.191, lng: 102.273 };

  // --- Google Routes API ---
  const GOOGLE_API_KEY = "AIzaSyAupowXVdjw9VQESNxsqBeWskKjXvfeTZE"; // same key you use in the <script> tag
  const ROUTES_BASE    = "https://routes.googleapis.com";
  let map, routePolyline, currentLevel="GREEN";


    async function safeFetch(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`${url} -> ${res.status}`);
    return res.json();
  }
// Initilize map

  async function initMap(){
    map = new google.maps.Map(document.getElementById('map'), {
      center: DEFAULT_CENTER, zoom: 12
    });

    
      // --- Default view: 5 km around the user's location ---
    // Note: Geolocation requires HTTPS on the web (localhost is OK).
    const user = await getUserLocation();                 // returns DEFAULT_CENTER if blocked/failed
    map.setCenter(user);
    const fiveKmCircle = new google.maps.Circle({
      center: user,
      radius: 3000 // meters
    });
    const circleBounds = fiveKmCircle.getBounds();
    if (circleBounds) map.fitBounds(circleBounds);

    // Load mocks
    const fri  = await safeFetch(`${MOCK_PATH}/fri.latest.json`);
    const haz  = await safeFetch(`${MOCK_PATH}/hazards.geojson`);
    const safe = await safeFetch(`${MOCK_PATH}/safe-zones.json`);

    // Draw layers
    drawFRI(fri);
    map.data.addGeoJson(haz);
    map.data.setStyle({ fillColor:'#1565C0', fillOpacity:.35, strokeColor:'#0D47A1', strokeWeight:1 });
    drawSafeZones(safe);

    // Initialize panel with highest severity item
    const top = fri.reduce((a,b)=> severity(b.level) > severity(a.level) ? b : a, fri[0]);
    setAdviceFor(top.level || "GREEN", top.reasons || [], nameFromDistrictId(top.districtId));
    setUpdatedNow();

    

    // Legend
    document.querySelector('.legend').innerHTML = legendHtml();
  }

  

  function drawFRI(fri){
    fri.forEach(d=>{
      const path = d.polygon[0].map(([lng,lat]) => ({ lat, lng }));
      const poly = new google.maps.Polygon({
        map,
        paths: path,
        strokeOpacity: .4,
        strokeColor: '#000',
        strokeWeight: 1,
        fillOpacity: d.level === 'GREEN' ? .15 : .25,
        fillColor: colorForLevel(d.level)
      });

      poly.addListener('click', () => {
        currentLevel = d.level || "GREEN";
        setAdviceFor(currentLevel, d.reasons || [], nameFromDistrictId(d.districtId)); // NEW
        const infoPos = d.center ? d.center : path[0]; // fallback if center not present
        new google.maps.InfoWindow({
          content: `<b>${d.districtId}</b><br/>Level: ${d.level || "N/A"}`
        }).open({ map, position: infoPos });
      });
    });
  }

  function drawSafeZones(safe){
    safe.forEach(s=>{
      const marker=new google.maps.Marker({map,position:{lat:s.lat,lng:s.lng},title:s.name});
      marker.addListener('click',async()=>{
        const origin=await getUserLocation();
        const gmaps=`https://www.google.com/maps/dir/?api=1&origin=${origin.lat},${origin.lng}&destination=${s.lat},${s.lng}&travelmode=driving`;
        const html=`
          <b>${s.name}</b><br/>
          <div class="row">
            <a class="btn" target="_blank" href="${gmaps}">Google Maps</a>
            <button id="safeRouteBtn" class="btn">Safe Route</button>
          </div>
          <div id="etaRow" class="row muted"></div>`;
        const iw=new google.maps.InfoWindow({content:html}); iw.open({map,anchor:marker});
        google.maps.event.addListenerOnce(iw,'domready',()=>{
          document.getElementById('safeRouteBtn').onclick=()=>{ 
            getSafeRoute(origin, {lat:s.lat, lng:s.lng, name:s.name});
          };
        });
      });
    });
  }

  // --- Call Google Routes API (Directions v2: computeRoutes) ---
  async function getSafeRoute(origin, destination) {
    try {
      const body = {
        origin:      { location: { latLng: { latitude: origin.lat,      longitude: origin.lng } } },
        destination: { location: { latLng: { latitude: destination.lat, longitude: destination.lng } } },
        travelMode: "DRIVE",
        routingPreference: "TRAFFIC_AWARE",
        polylineQuality: "HIGH_QUALITY",
        polylineEncoding: "GEO_JSON_LINESTRING" // ask for GeoJSON first
      };

      const url = `${ROUTES_BASE}/directions/v2:computeRoutes?key=${encodeURIComponent(GOOGLE_API_KEY)}`;

      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // request only what we need (faster/cheaper)
          "X-Goog-FieldMask":
            "routes.distanceMeters,routes.duration,routes.polyline.geoJsonLinestring,routes.polyline.encodedPolyline"
        },
        body: JSON.stringify(body)
      });

      // Parse JSON or fallback to raw text for error display
      let payloadText = await res.text();
      let data;
      try { data = JSON.parse(payloadText); } catch { data = null; }

      if (!res.ok || !data?.routes?.length) {
        const msg = data?.error?.message || payloadText || `HTTP ${res.status}`;
        console.error("ComputeRoutes error:", res.status, msg);
        setEtaSummaryError(`Route error: ${msg}`);
        return;
      }

      const route = data.routes[0];

      // Prefer GeoJSON line; fallback to encoded polyline (needs geometry library)
      if (route.polyline?.geoJsonLinestring?.coordinates?.length) {
        drawGeoJsonPolyline(route.polyline.geoJsonLinestring);
        fitToGeoJsonLineString(route.polyline.geoJsonLinestring);
      } else if (route.polyline?.encodedPolyline && google.maps.geometry?.encoding) {
        const decoded = google.maps.geometry.encoding.decodePath(route.polyline.encodedPolyline);
        if (routePolyline) routePolyline.setMap(null);
        routePolyline = new google.maps.Polyline({ map, path: decoded, strokeColor: "#FF0000", strokeWeight: 4 });
        const b = new google.maps.LatLngBounds();
        decoded.forEach(p => b.extend(p));
        map.fitBounds(b);
      } else {
        setEtaSummaryError("Route error: No polyline returned.");
        return;
      }

      // Update ETA box
      const km  = (route.distanceMeters / 1000);
      const sec = Number(String(route.duration).replace("s",""));
      const min = Math.round(sec / 60);
      updateEtaSummary(min, km, origin, destination);

      // Optional panel update
      setAdviceFor("GREEN", ["Route calculated"], "Routing",
        { user: origin, zone: { lat: destination.lat, lng: destination.lng } });

    } catch (err) {
      console.error("Routes API fetch failed:", err);
      setEtaSummaryError("Route error: request failed.");
    }
  }




      
// --- Helpers ---
  
  async function getUserLocation(){
  // If you want to force Kota Bharu as the user's location
  if (USE_FAKE_USER_LOC) {
    return { ...FAKE_USER_LOC, isMock: true };
  }

  // Otherwise use real geolocation (falls back to DEFAULT_CENTER)
  return new Promise(res=>{
    if(!navigator.geolocation) return res({ ...DEFAULT_CENTER, isMock: true });
    navigator.geolocation.getCurrentPosition(
      p=>res({ lat:p.coords.latitude, lng:p.coords.longitude, isMock:false }),
      ()=>res({ ...DEFAULT_CENTER, isMock:true }),
      { enableHighAccuracy:true, timeout:5000 }
    );
  });
}

  function drawGeoJsonPolyline(lineString) {
  const path = (lineString.coordinates || []).map(([lng, lat]) => ({ lat, lng }));
  if (routePolyline) routePolyline.setMap(null);
  routePolyline = new google.maps.Polyline({
    map,
    path,
    strokeColor: "#FF0000",
    strokeWeight: 4
  });
}

function fitToGeoJsonLineString(lineString) {
  const bounds = new google.maps.LatLngBounds();
  (lineString.coordinates || []).forEach(([lng, lat]) => bounds.extend({ lat, lng }));
  if (!bounds.isEmpty()) map.fitBounds(bounds);
}

function fmt(n){ return Number(n).toFixed(6); }
function coordsLine(label, p){
  if(!p) return "";
  return `<div class="muted">${label}: ${fmt(p.lat)}, ${fmt(p.lng)}</div>`;
}

function updateEtaSummary(min, km, origin, destination){
  const el = document.getElementById('etaSummary');
  if(!el) return;
  const toLabel = destination?.name
    ? destination.name
    : `${fmt(destination.lat)}, ${fmt(destination.lng)}`;
  const fromStr = origin ? `${fmt(origin.lat)}, ${fmt(origin.lng)}` : '—';
  el.innerHTML = `ETA: ~${min} min • Distance: ${km.toFixed(1)} km
    <br><span class="muted">From: ${fromStr} &nbsp;|&nbsp; To: ${toLabel}</span>`;
}
function setEtaSummaryError(msg){
  const el = document.getElementById('etaSummary');
  if (el) el.textContent = msg;
}
function fmt(n){ return Number(n).toFixed(6); }


  // NEW: severity rank
  function severity(l){ return l==='RED'?3 : l==='ORANGE'?2 : l==='YELLOW'?1 : 0; }

  // NEW: show readable name from districtId like "KELANTAN:KOTA_BHARU:Mukim Pengkalan Chepa"
  function nameFromDistrictId(id){
    if(!id) return "Unknown area";
    const parts = id.split(":");
    return parts[parts.length - 1].replace(/_/g, " ");
  }

  // NEW: colored badge HTML
  function badgeForLevel(level){
    const l = level || "GREEN";
    return `<span class="badge" style="background:${colorForLevel(l)}">${l}</span>`;
  }

  // NEW: upgraded advice writer with title + badge
  function setAdviceFor(level, reasons = [], title = "", extra = {}){
    const msg = adviceForLevel(level);
    const header = `<div><strong>${title || "Risk"}</strong> ${badgeForLevel(level)}</div>`;
    const userLine = extra.user ? coordsLine("User", extra.user) : "";
    const zoneLine = extra.zone ? coordsLine("Zone", extra.zone) : "";
    const reasonsHtml = reasons.length ? `<div class="muted">(${reasons.join(", ")})</div>` : "";
    document.getElementById('advice').innerHTML =
      `${header}${userLine}${zoneLine}<div>${msg}</div>${reasonsHtml}`;
  }

  function setUpdatedNow(){document.getElementById('updated').textContent="Last updated: "+new Date().toLocaleString();}
  function adviceForLevel(l){
    if(l==='RED')return"🔴 Severe risk. Evacuate if instructed. Avoid rivers/underpasses.";
    if(l==='ORANGE')return"🟠 High risk in 24h. Move valuables. Plan evacuation.";
    if(l==='YELLOW')return"🟡 Heavy rain possible. Prepare go-bag. Avoid low areas.";
    return"🟢 Low risk. Stay alert for updates.";
  }

  function colorForLevel(l){return l==='RED'?'#d32f2f':l==='ORANGE'?'#f57c00':l==='YELLOW'?'#fbc02d':'#43a047';}
  function legendHtml(){
    return`
      <div class="row"><span class="dot" style="background:#43a047"></span> Green</div>
      <div class="row"><span class="dot" style="background:#fbc02d"></span> Yellow</div>
      <div class="row"><span class="dot" style="background:#f57c00"></span> Orange</div>
      <div class="row"><span class="dot" style="background:#d32f2f"></span> Red</div>
      <div class="row muted">Tap district for details</div>`;
  }

  // NEW: fit to all polygons once
  function fitToAll(items){
    const bounds = new google.maps.LatLngBounds();
    items.forEach(d=>{
      (d.polygon?.[0] || []).forEach(([lng,lat])=>{
        bounds.extend(new google.maps.LatLng(lat,lng));
      });
    });
    if (!bounds.isEmpty()) map.fitBounds(bounds);
  }

  window.initMap = initMap;



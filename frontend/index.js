// index.js
import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const app = express();
app.use(express.json()); // parse JSON

// --- CORS for Live Server (5500) -> Express (3000)
app.use((req, res, next) => {
  const origin = req.headers.origin;
  const allowed = ["http://127.0.0.1:5500", "http://localhost:5500"];
  if (allowed.includes(origin)) {
    res.header("Access-Control-Allow-Origin", origin);
    res.header("Vary", "Origin");
  }
  res.header("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.header("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.sendStatus(204); // preflight
  next();
});

// __dirname in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---- API FIRST (so /sos isn't treated as a static file)
app.post("/sos", (req, res) => {
  console.log("SOS hit:", req.body);
  const { userId, location, context } = req.body || {};
  res.json({
    userId,
    location,
    context,
    agency: "Civil Defence",
    priority: "high",
    alert: `Demo alert for ${location}: ${context}`,
    route: {
      from: "Rescue HQ Kuala Terengganu",
      to: "Pak Abu’s House",
      steps: ["Head north", "Turn left onto Jalan Besar", "Arrive in ~10 mins"]
    }
  });
});

// ---- Static files (authority.html, authority.js, css/, mocks/)
app.use(express.static(__dirname));

// Optional: root -> authority.html
app.get("/", (_req, res) => {
  res.sendFile(path.join(__dirname, "authority.html"));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});



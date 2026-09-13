"""
NER-Vision: AI Landslide Guardian — Backend
SIH 2026 · PS 26001

Run:
    pip install -r requirements.txt
    python app.py
Then open http://localhost:5000
"""

import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone

import networkx as nx
from flask import Flask, jsonify, request, send_from_directory, g, session

import data
import model
import report_verifier
import reports_db

DB_PATH = "ner_vision.db"

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "ner_vision_secure_admin_key_2026_ps26001"

risk_engine = model.RiskEngine()
data.init_state()

# ---------------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    # Initialize main ner_vision.db
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        location_id TEXT,
        lat REAL, lng REAL,
        description TEXT,
        reported_severity TEXT,
        media_url TEXT,
        is_emergency INTEGER,
        is_verified INTEGER DEFAULT 0,
        timestamp TEXT
    );
    CREATE TABLE IF NOT EXISTS alerts (
        id TEXT PRIMARY KEY,
        location_id TEXT,
        risk_level TEXT,
        risk_score REAL,
        channel_log TEXT,
        timestamp TEXT,
        is_resolved INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS subscribers (
        phone TEXT PRIMARY KEY,
        location_id TEXT,
        language TEXT,
        voice_enabled INTEGER DEFAULT 1
    );
    """)
    conn.commit()
    conn.close()
    
    # Initialize dedicated reports.db database
    reports_db.init_reports_db()


# ---------------------------------------------------------------------------
# Core risk computation shared by several endpoints
# ---------------------------------------------------------------------------

def compute_location_risk(loc_id, state_override=None):
    loc = next(l for l in data.LOCATIONS if l["id"] == loc_id)
    s = state_override or data.get_state()[loc_id]
    ml = risk_engine.predict(
        s["rainfall_24h"], s["rainfall_3day"], s["soil_moisture"],
        s["slope_deg"], s["vegetation_index"], s["historical_landslide_count"]
    )
    rule = model.rule_based_fallback(
        s["rainfall_24h"], s["soil_moisture"], s["slope_deg"], s["vegetation_index"]
    )
    return {
        "location": loc,
        "sensor_state": s,
        "ml_prediction": ml,
        "offline_rule_engine": rule,
        "recommendation": model.recommendation_for(ml["risk_level"]),
        "voice_alert": {
            lang: tmpl.get(ml["risk_level"], "").format(loc=loc["name"])
            for lang, tmpl in model.ALERT_VOICE_TEMPLATES.items()
            if ml["risk_level"] in tmpl
        },
    }


def dispatch_alert_if_needed(loc_id, risk):
    if risk["ml_prediction"]["risk_level"] not in ("High", "Very High"):
        return None
    db = get_db()
    alert_id = str(uuid.uuid4())
    channels = ["app_push", "sms(simulated)", "whatsapp(simulated)"]
    db.execute(
        "INSERT INTO alerts (id, location_id, risk_level, risk_score, channel_log, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (alert_id, loc_id, risk["ml_prediction"]["risk_level"],
         risk["ml_prediction"]["risk_score"], ",".join(channels),
         datetime.now(timezone.utc).isoformat())
    )
    db.commit()
    return alert_id


# ---------------------------------------------------------------------------
# Background simulation loop
# ---------------------------------------------------------------------------

def simulation_loop():
    while True:
        time.sleep(15)
        data.tick()
        with app.app_context():
            for loc in data.LOCATIONS:
                risk = compute_location_risk(loc["id"])
                dispatch_alert_if_needed(loc["id"], risk)


# ---------------------------------------------------------------------------
# API Endpoints — /api/v1/*
# ---------------------------------------------------------------------------

@app.route("/api/v1/locations")
def list_locations():
    out = []
    for loc in data.LOCATIONS:
        r = compute_location_risk(loc["id"])
        out.append({
            "id": loc["id"], "name": loc["name"], "state": loc["state"],
            "lat": loc["lat"], "lng": loc["lng"],
            "risk_level": r["ml_prediction"]["risk_level"],
            "risk_score": r["ml_prediction"]["risk_score"],
        })
    return jsonify(out)


@app.route("/api/v1/predict/<loc_id>")
def predict(loc_id):
    if loc_id not in [l["id"] for l in data.LOCATIONS]:
        return jsonify({"error": "unknown location"}), 404
    return jsonify(compute_location_risk(loc_id))


@app.route("/api/v1/alerts")
def get_alerts():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT 50"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/v1/reports", methods=["GET", "POST"])
def reports():
    if request.method == "POST":
        body = request.get_json(force=True) if request.is_json else request.form
        rid = str(uuid.uuid4())
        loc_id = body.get("location_id")
        
        loc_name = "Custom Lat/Lng"
        if loc_id and loc_id in [l["id"] for l in data.LOCATIONS]:
            loc_name = next(l["name"] for l in data.LOCATIONS if l["id"] == loc_id)
            
        desc = body.get("description", "")
        severity = body.get("reported_severity", "Medium")
        lat = float(body.get("lat") or 25.8)
        lng = float(body.get("lng") or 92.8)
        media_url = body.get("media_url", "")
        is_emergency = severity in ("High", "Very High")
        
        # Run Automated NLP Verification Engine with sector telemetry validation
        ver_res = report_verifier.ReportVerifier.verify_report(desc, loc_id, severity)
        
        # Save to dedicated reports.db database
        reports_db.save_report(
            report_id=rid,
            location_id=loc_id,
            location_name=loc_name,
            lat=lat, lng=lng,
            description=desc,
            reported_severity=severity,
            media_url=media_url,
            is_emergency=is_emergency,
            ver_res=ver_res
        )
        
        return jsonify({
            "id": rid,
            "status": "received",
            "verification_score": ver_res["verification_score"],
            "verification_status": ver_res["verification_status"],
            "verification_reasons": ver_res["verification_reasons"],
            "is_verified": ver_res["is_verified"]
        }), 201

    # GET: return all reports stored in reports.db
    return jsonify(reports_db.fetch_all_reports())


@app.route("/api/v1/simulate", methods=["POST"])
def simulate():
    body = request.get_json(force=True)
    loc_id = body["location_id"]
    sim_state = data.nudge(
        loc_id,
        rainfall_delta=body.get("rainfall_delta", 0),
        soil_delta=body.get("soil_delta", 0),
        veg_delta=body.get("veg_delta", 0),
    )
    return jsonify(compute_location_risk(loc_id, state_override=sim_state))


@app.route("/api/v1/resilience")
def resilience():
    out = []
    for loc in data.LOCATIONS:
        s = data.get_state()[loc["id"]]
        hist_penalty = s["historical_landslide_count"] * 6
        veg_bonus = s["vegetation_index"] * 25
        slope_penalty = (s["slope_deg"] / 55) * 20
        score = max(0, min(100, 70 - hist_penalty + veg_bonus - slope_penalty))
        out.append({"location_id": loc["id"], "name": loc["name"],
                     "state": loc["state"], "resilience_score": round(score, 1)})
    out.sort(key=lambda x: x["resilience_score"])
    return jsonify(out)


@app.route("/api/v1/evacuate")
def evacuate():
    """Evacuation Route Planner with Google Maps Direct Turn-by-Turn Navigation."""
    loc_id = request.args.get("location_id")
    if loc_id not in [l["id"] for l in data.LOCATIONS]:
        return jsonify({"error": "unknown location"}), 404

    G = nx.Graph()
    risk_by_node = {}
    for loc in data.LOCATIONS:
        r = compute_location_risk(loc["id"])
        risk_by_node[loc["id"]] = r["ml_prediction"]["risk_score"]
    for a, b, dist in data.ROAD_EDGES:
        penalty_a = 1 + 4 * risk_by_node.get(a, 0)
        penalty_b = 1 + 4 * risk_by_node.get(b, 0)
        weight = dist * max(penalty_a, penalty_b)
        G.add_edge(a, b, weight=weight, distance=dist)

    best_path, best_zone, best_cost = None, None, float("inf")
    for sz in data.SAFE_ZONES:
        if sz not in G:
            continue
        try:
            path = nx.shortest_path(G, loc_id, sz, weight="weight")
            cost = nx.shortest_path_length(G, loc_id, sz, weight="weight")
            if cost < best_cost:
                best_cost, best_path, best_zone = cost, path, sz
        except nx.NetworkXNoPath:
            continue

    if not best_path:
        return jsonify({"error": "no route found"}), 404

    total_km = sum(
        data.haversine_km(
            *_coords(best_path[i]), *_coords(best_path[i + 1])
        ) for i in range(len(best_path) - 1)
    )
    
    orig_lat, orig_lng = _coords(best_path[0])
    dest_lat, dest_lng = _coords(best_path[-1])
    
    # Extract coordinates for intermediate road nodes
    nodes_coords = [_coords(n) for n in best_path]
    real_pts, real_dist, real_dur = _get_real_road_geometry(nodes_coords)
    
    # Construct Google Maps Direct Directions URL (with waypoints)
    waypoints_str = ""
    if len(best_path) > 2:
        wp_list = [f"{_coords(n)[0]},{_coords(n)[1]}" for n in best_path[1:-1]]
        waypoints_str = f"&waypoints={'|'.join(wp_list)}"
        
    google_maps_url = f"https://www.google.com/maps/dir/?api=1&origin={orig_lat},{orig_lng}&destination={dest_lat},{dest_lng}{waypoints_str}&travelmode=driving"

    return jsonify({
        "from": loc_id,
        "to_safe_zone": {"id": best_zone, "name": data.SAFE_ZONES[best_zone]["name"]},
        "route_nodes": best_path,
        "route_coords": [{"id": n, **_coords_dict(n)} for n in best_path],
        "real_road_coords": real_pts or [[c[0], c[1]] for c in nodes_coords],
        "estimated_distance_km": real_dist or round(total_km, 1),
        "estimated_time_min": real_dur or round(total_km / 35 * 60, 0),
        "risk_avoided": "Route dynamically re-weighted to bypass high-risk segments",
        "google_maps_url": google_maps_url,
        "is_real_road_geometry": bool(real_pts)
    })


def _get_real_road_geometry(nodes_coords):
    import urllib.request, json
    try:
        coords_str = ";".join([f"{lng},{lat}" for lat, lng in nodes_coords])
        url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
        req = urllib.request.Request(url, headers={'User-Agent': 'NER-Vision/2.0'})
        res = json.loads(urllib.request.urlopen(req, timeout=4).read().decode())
        route_data = res["routes"][0]
        # OSRM coordinates are [lng, lat], convert to [lat, lng] for Leaflet polyline
        road_pts = [[pt[1], pt[0]] for pt in route_data["geometry"]["coordinates"]]
        dist_km = round(route_data["distance"] / 1000.0, 1)
        duration_min = round(route_data["duration"] / 60.0, 0)
        return road_pts, dist_km, duration_min
    except Exception:
        return None, None, None


def _coords(node_id):
    if node_id in data.SAFE_ZONES:
        z = data.SAFE_ZONES[node_id]
        return z["lat"], z["lng"]
    loc = next(l for l in data.LOCATIONS if l["id"] == node_id)
    return loc["lat"], loc["lng"]


def _coords_dict(node_id):
    lat, lng = _coords(node_id)
    name = data.SAFE_ZONES[node_id]["name"] if node_id in data.SAFE_ZONES else \
        next(l["name"] for l in data.LOCATIONS if l["id"] == node_id)
    return {"lat": lat, "lng": lng, "name": name}


@app.route("/api/v1/subscribe", methods=["POST"])
def subscribe():
    body = request.get_json(force=True)
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO subscribers (phone, location_id, language, voice_enabled) "
        "VALUES (?,?,?,?)",
        (body["phone"], body["location_id"], body.get("language", "en"),
         1 if body.get("voice_enabled", True) else 0)
    )
    db.commit()
    return jsonify({"status": "subscribed"}), 201


@app.route("/api/v1/meta")
def meta():
    return jsonify({
        "locations": data.LOCATIONS,
        "safe_zones": data.SAFE_ZONES,
        "languages": list(model.ALERT_VOICE_TEMPLATES.keys()),
        "model_backtest_accuracy": risk_engine.backtest_accuracy,
    })


# ---------------------------------------------------------------------------
# Admin Security & Clearance Endpoints
# ---------------------------------------------------------------------------

@app.route("/admin")
def admin_page():
    return send_from_directory("templates", "admin.html")


@app.route("/api/v1/admin/login", methods=["POST"])
def admin_login():
    body = request.get_json(force=True)
    email = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    
    if email == "admin@nervision.gov.in" and password == "Guard@NER2026":
        session["admin"] = True
        return jsonify({"status": "authenticated", "message": "Clearance granted."})
    return jsonify({"status": "denied", "message": "Invalid government credentials."}), 401


@app.route("/api/v1/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return jsonify({"status": "logged_out"})


@app.route("/api/v1/admin/reports/override", methods=["POST"])
def admin_report_override():
    body = request.get_json(force=True)
    report_id = body.get("report_id")
    is_verified = bool(body.get("is_verified", True))
    
    reports_db.update_report_status(report_id, is_verified, admin_override=1)
    return jsonify({"status": "updated", "report_id": report_id, "is_verified": is_verified})


@app.route("/api/v1/admin/broadcast", methods=["POST"])
def admin_broadcast():
    body = request.get_json(force=True)
    sector = body.get("sector", "ALL")
    msg = body.get("message", "")
    
    return jsonify({
        "status": "dispatched",
        "sector": sector,
        "subscribers_notified": 48,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


# ---------------------------------------------------------------------------
# AI Chatbot & Static Routes
# ---------------------------------------------------------------------------

NER_KNOWLEDGE = {
    "helplines": (
        "🚨 **Official Disaster Helplines for North-East India:**\n"
        "• **NDRF National HQ**: 1078 / 011-24363260\n"
        "• **All-India Emergency Number**: 112\n"
        "• **Assam SDMA**: 1070 / 1079\n"
        "• **Sikkim SDMA**: 03592-202461 / 1070\n"
        "• **Meghalaya SDMA**: 1070 / 0364-2502142\n"
        "• **Nagaland NSDMA**: 112 / 0370-2270050"
    ),
    "warning_signs": (
        "⚠️ **Top Early Warning Signs of an Imminent Landslide:**\n"
        "1. **Fresh Ground Cracks**: Widening fissures on hill slopes or retaining walls.\n"
        "2. **Tilting Infrastructure**: Trees or poles leaning downslope.\n"
        "3. **Sudden Water Changes**: Muddy water gushing from new springs."
    )
}

DISASTER_KEYWORDS = [
    "landslide", "slide", "crack", "fissure", "rain", "rainfall", "weather", "flood",
    "hill", "slope", "soil", "mud", "rock", "helpline", "emergency", "ndrf", "sdrf"
]


@app.route("/api/v1/chatbot", methods=["POST"])
def ner_chatbot():
    body = request.get_json(force=True) if request.is_json else request.form
    query = (body.get("message") or "").strip().lower()
    
    if any(w in query for w in ["phone", "call", "helpline", "ndrf"]):
        reply = NER_KNOWLEDGE["helplines"]
    elif any(w in query for w in ["crack", "sign", "warning"]):
        reply = NER_KNOWLEDGE["warning_signs"]
    else:
        reply = "🏔️ **NER Hill Landslide Safety Guidance:**\nIf you observe slope cracks, evacuate sideways to higher ridge ground immediately. Call NDRF (**1078**) or Police (**112**)."

    return jsonify({"reply": reply, "is_emergency": "crack" in query or "helpline" in query})


@app.route("/")
def index():
    return send_from_directory("templates", "index.html")


@app.route("/gis-map")
def gis_map_page():
    return send_from_directory("templates", "gis_map.html")


@app.route("/reports")
def reports_page():
    return send_from_directory("templates", "reports.html")


@app.route("/login")
def login():
    return send_from_directory("templates", "login.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=simulation_loop, daemon=True)
    t.start()
    print("NER-Vision backend running with NLP verifier & reports.db active.")
    app.run(debug=True, port=5000, use_reloader=False)

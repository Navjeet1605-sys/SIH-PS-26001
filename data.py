"""
data.py
NER-Vision AI Landslide Guardian — Real & Comprehensive Data Layer.

Contains authoritative North-Eastern Region (NER) India landslide hazard
data compiled from:
  - Geological Survey of India (GSI) National Landslide Susceptibility Mapping (NLSM) & Bhukosh
  - National Disaster Management Authority (NDMA) Landslide Hazard Zonation Guidelines
  - Indian Meteorological Department (IMD) Heavy Rainfall Threshold Models
  - ISRO Bhuvan Landslide Geoportal & Sentinel-2 Vegetation Indices (NDVI)
  - Historical Incident Registries (2015-2026 NER Landslide Database)

Covers all 8 North-Eastern States:
Assam, Meghalaya, Sikkim, Mizoram, Manipur, Nagaland, Arunachal Pradesh, Tripura.
"""

import random
import math
import time

random.seed(42)

# Real at-risk village/town locations across all 8 NER states with exact coordinates,
# GSI susceptibility zone, primary lithology, critical rainfall threshold, and primary language.
LOCATIONS = [
    # --- ASSAM ---
    {
        "id": "L01",
        "name": "Haflong Hill & Jatinga Corridor",
        "district": "Dima Hasao",
        "state": "Assam",
        "lat": 25.1764,
        "lng": 93.0185,
        "base_slope": 44,
        "lang": "as",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Soft Tertiary Sandstone & Shale (Highly Weathered)",
        "critical_rain_24h": 65.0,
        "historical_events": 8,
        "elevation_m": 960,
    },
    {
        "id": "L02",
        "name": "Sonapur Hills Cut (NH-37)",
        "district": "Kamrup Metropolitan",
        "state": "Assam",
        "lat": 26.0206,
        "lng": 92.0246,
        "base_slope": 32,
        "lang": "as",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Precambrian Gneissic Complex with Soil Overburden",
        "critical_rain_24h": 75.0,
        "historical_events": 4,
        "elevation_m": 180,
    },
    {
        "id": "L03",
        "name": "Kamakhya & Sarania Slopes",
        "district": "Guwahati Urban",
        "state": "Assam",
        "lat": 26.1664,
        "lng": 91.7062,
        "base_slope": 35,
        "lang": "as",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Granitic Gneiss & Loose Colluvial Soil",
        "critical_rain_24h": 70.0,
        "historical_events": 5,
        "elevation_m": 240,
    },
    {
        "id": "L04",
        "name": "Lakhipur Slope Cut",
        "district": "Cachar",
        "state": "Assam",
        "lat": 24.7946,
        "lng": 93.0135,
        "base_slope": 28,
        "lang": "as",
        "gsi_zone": "Moderate Risk (Zone-3)",
        "lithology": "Surma Group Siltstone & Claystone",
        "critical_rain_24h": 85.0,
        "historical_events": 3,
        "elevation_m": 120,
    },

    # --- MEGHALAYA ---
    {
        "id": "L05",
        "name": "Cherrapunji (Sohra Rim) Escarpment",
        "district": "East Khasi Hills",
        "state": "Meghalaya",
        "lat": 25.2702,
        "lng": 91.7323,
        "base_slope": 52,
        "lang": "kha",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Khasi Group Sandstone & Limestone Gorges",
        "critical_rain_24h": 120.0,
        "historical_events": 12,
        "elevation_m": 1430,
    },
    {
        "id": "L06",
        "name": "Mawsynram South Ridge",
        "district": "East Khasi Hills",
        "state": "Meghalaya",
        "lat": 25.2971,
        "lng": 91.5822,
        "base_slope": 48,
        "lang": "kha",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Highly Fractured Sandstone & Thick Clay Layer",
        "critical_rain_24h": 115.0,
        "historical_events": 10,
        "elevation_m": 1400,
    },
    {
        "id": "L07",
        "name": "Shillong Peak & Laitlum Canyon",
        "district": "East Khasi Hills",
        "state": "Meghalaya",
        "lat": 25.5788,
        "lng": 91.8933,
        "base_slope": 42,
        "lang": "kha",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Shillong Group Quartzite & Schist",
        "critical_rain_24h": 80.0,
        "historical_events": 6,
        "elevation_m": 1965,
    },
    {
        "id": "L08",
        "name": "Jowai Pass (NH-6 Highway)",
        "district": "West Jaintia Hills",
        "state": "Meghalaya",
        "lat": 25.4484,
        "lng": 92.2036,
        "base_slope": 38,
        "lang": "kha",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Coal-Bearing Sandstone & Shale Intercalations",
        "critical_rain_24h": 75.0,
        "historical_events": 7,
        "elevation_m": 1380,
    },
    {
        "id": "L09",
        "name": "Nongpoh Cutting (GS Road Corridor)",
        "district": "Ri-Bhoi",
        "state": "Meghalaya",
        "lat": 25.9056,
        "lng": 91.8812,
        "base_slope": 36,
        "lang": "kha",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Porphyritic Granite & Weathered Residual Soil",
        "critical_rain_24h": 70.0,
        "historical_events": 5,
        "elevation_m": 485,
    },

    # --- SIKKIM ---
    {
        "id": "L10",
        "name": "Gangtok East Bypass & 9th Mile",
        "district": "East Sikkim",
        "state": "Sikkim",
        "lat": 27.3389,
        "lng": 88.6065,
        "base_slope": 49,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Daling Group Biotite Schist & Phyllite",
        "critical_rain_24h": 60.0,
        "historical_events": 11,
        "elevation_m": 1650,
    },
    {
        "id": "L11",
        "name": "Mangan-Chungthang Teesta Gorge",
        "district": "North Sikkim",
        "state": "Sikkim",
        "lat": 27.5133,
        "lng": 88.5326,
        "base_slope": 56,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "High-Grade Gneiss & Glacial Debris Deposits",
        "critical_rain_24h": 55.0,
        "historical_events": 14,
        "elevation_m": 1260,
    },
    {
        "id": "L12",
        "name": "NH-10 Sevoke to Teesta Bazaar Corridor",
        "district": "Kalimpong / Sikkim Border",
        "state": "Sikkim",
        "lat": 26.8912,
        "lng": 88.4712,
        "base_slope": 54,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Sheared Phyllite & Active Slope Shear Zones",
        "critical_rain_24h": 50.0,
        "historical_events": 15,
        "elevation_m": 220,
    },
    {
        "id": "L13",
        "name": "Pelling-Geyzing Ridge Road",
        "district": "West Sikkim",
        "state": "Sikkim",
        "lat": 27.3168,
        "lng": 88.2372,
        "base_slope": 43,
        "lang": "hi",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Garnetiferous Mica Schist",
        "critical_rain_24h": 65.0,
        "historical_events": 6,
        "elevation_m": 2150,
    },

    # --- MIZORAM ---
    {
        "id": "L14",
        "name": "Aizawl Laipuitlang & Ridge Highway",
        "district": "Aizawl Urban",
        "state": "Mizoram",
        "lat": 23.7271,
        "lng": 92.7176,
        "base_slope": 44,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Bhuban Formation Interbedded Sandstone & Mudstone",
        "critical_rain_24h": 60.0,
        "historical_events": 9,
        "elevation_m": 1132,
    },
    {
        "id": "L15",
        "name": "Serkawn Slope Zone",
        "district": "Lunglei",
        "state": "Mizoram",
        "lat": 22.8871,
        "lng": 92.7354,
        "base_slope": 39,
        "lang": "hi",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Weak Siltstone with Dip Slope Slippage",
        "critical_rain_24h": 70.0,
        "historical_events": 5,
        "elevation_m": 720,
    },
    {
        "id": "L16",
        "name": "Champhai Zokhawthar Border Cut",
        "district": "Champhai",
        "state": "Mizoram",
        "lat": 23.4560,
        "lng": 93.3273,
        "base_slope": 35,
        "lang": "hi",
        "gsi_zone": "Moderate Risk (Zone-3)",
        "lithology": "Sandstone-Shale Sequence",
        "critical_rain_24h": 80.0,
        "historical_events": 4,
        "elevation_m": 1678,
    },

    # --- MANIPUR ---
    {
        "id": "L17",
        "name": "Tupul Yard & Railway Construction Corridor",
        "district": "Noney",
        "state": "Manipur",
        "lat": 24.8142,
        "lng": 93.6301,
        "base_slope": 46,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Disang Group Shale & Siltstone (Highly Unstable Debris)",
        "critical_rain_24h": 55.0,
        "historical_events": 10,
        "elevation_m": 620,
    },
    {
        "id": "L18",
        "name": "Senapati Mao Gate Corridor (NH-39)",
        "district": "Senapati",
        "state": "Manipur",
        "lat": 25.5034,
        "lng": 94.1352,
        "base_slope": 38,
        "lang": "hi",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Disang Flysch Sediments & Clay Collapsible Soil",
        "critical_rain_24h": 65.0,
        "historical_events": 7,
        "elevation_m": 1780,
    },
    {
        "id": "L19",
        "name": "Ukhrul Shirui Peak Base",
        "district": "Ukhrul",
        "state": "Manipur",
        "lat": 25.0466,
        "lng": 94.3629,
        "base_slope": 41,
        "lang": "hi",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Ophiolite Belt & Serpentinized Rock",
        "critical_rain_24h": 70.0,
        "historical_events": 5,
        "elevation_m": 2020,
    },

    # --- NAGALAND ---
    {
        "id": "L20",
        "name": "Kohima Paglapahar & Ridge Pass",
        "district": "Kohima",
        "state": "Nagaland",
        "lat": 25.6751,
        "lng": 94.1086,
        "base_slope": 43,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Disang Series Weathered Black Shale",
        "critical_rain_24h": 60.0,
        "historical_events": 9,
        "elevation_m": 1444,
    },
    {
        "id": "L21",
        "name": "Chumukedima Rockfall Corridor (NH-29)",
        "district": "Chumukedima / Dimapur",
        "state": "Nagaland",
        "lat": 25.7921,
        "lng": 93.7712,
        "base_slope": 47,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "Overhanging Sandstone Strata & Sheared Fault Zone",
        "critical_rain_24h": 58.0,
        "historical_events": 8,
        "elevation_m": 310,
    },
    {
        "id": "L22",
        "name": "Mokokchung Ungma Slope",
        "district": "Mokokchung",
        "state": "Nagaland",
        "lat": 26.3260,
        "lng": 94.5153,
        "base_slope": 35,
        "lang": "hi",
        "gsi_zone": "Moderate Risk (Zone-3)",
        "lithology": "Barail Group Sandstone & Thin Shale Layers",
        "critical_rain_24h": 75.0,
        "historical_events": 4,
        "elevation_m": 1325,
    },

    # --- ARUNACHAL PRADESH ---
    {
        "id": "L23",
        "name": "Itanagar Chimpu Hill Road Cut",
        "district": "Papum Pare",
        "state": "Arunachal Pradesh",
        "lat": 27.0844,
        "lng": 93.6053,
        "base_slope": 39,
        "lang": "hi",
        "gsi_zone": "High Risk (Zone-2)",
        "lithology": "Siwalik Soft Sandstone & Unconsolidated Pebble Beds",
        "critical_rain_24h": 65.0,
        "historical_events": 6,
        "elevation_m": 440,
    },
    {
        "id": "L24",
        "name": "Tawang Highway Sela Pass Approach",
        "district": "West Kameng",
        "state": "Arunachal Pradesh",
        "lat": 27.5021,
        "lng": 92.1245,
        "base_slope": 51,
        "lang": "hi",
        "gsi_zone": "Very High Risk (Zone-1)",
        "lithology": "High Altitude Gneissic Rockfall & Moraine Slopes",
        "critical_rain_24h": 50.0,
        "historical_events": 9,
        "elevation_m": 3400,
    },
    {
        "id": "L25",
        "name": "Ziro Valley Rim Slopes",
        "district": "Lower Subansiri",
        "state": "Arunachal Pradesh",
        "lat": 27.5486,
        "lng": 93.8258,
        "base_slope": 32,
        "lang": "hi",
        "gsi_zone": "Moderate Risk (Zone-3)",
        "lithology": "Schistose Rock & Lake Sediment Clay",
        "critical_rain_24h": 80.0,
        "historical_events": 3,
        "elevation_m": 1560,
    },

    # --- TRIPURA ---
    {
        "id": "L26",
        "name": "Longtharai Valley Ridge (NH-8)",
        "district": "Dhalai",
        "state": "Tripura",
        "lat": 23.8315,
        "lng": 91.9005,
        "base_slope": 24,
        "lang": "bn",
        "gsi_zone": "Moderate Risk (Zone-3)",
        "lithology": "Dupitila Formation Unconsolidated Sands & Clay",
        "critical_rain_24h": 85.0,
        "historical_events": 3,
        "elevation_m": 240,
    },
    {
        "id": "L27",
        "name": "Jampui Hills Slope Cut",
        "district": "North Tripura",
        "state": "Tripura",
        "lat": 23.9512,
        "lng": 92.2741,
        "base_slope": 29,
        "lang": "bn",
        "gsi_zone": "Moderate Risk (Zone-3)",
        "lithology": "Surma Group Sandstone",
        "critical_rain_24h": 80.0,
        "historical_events": 4,
        "elevation_m": 620,
    },
]

LANG_NAMES = {"en": "English", "hi": "Hindi", "as": "Assamese", "kha": "Khasi", "bn": "Bengali"}

# Designated Safe Zones / Emergency Relief HQ Centers mapped across all 8 NER States
SAFE_ZONES = {
    "SZ01": {"name": "Guwahati State Relief HQ & Medical Depot", "state": "Assam", "lat": 26.1445, "lng": 91.7362, "capacity": 5000},
    "SZ02": {"name": "Shillong DC Office & Civil Defense Shelter", "state": "Meghalaya", "lat": 25.5760, "lng": 91.8825, "capacity": 3000},
    "SZ03": {"name": "Gangtok Army & State Relief Center (Tashi View)", "state": "Sikkim", "lat": 27.3314, "lng": 88.6138, "capacity": 2500},
    "SZ04": {"name": "Aizawl Emergency Relief Camp (Tuirial)", "state": "Mizoram", "lat": 23.7307, "lng": 92.7173, "capacity": 2000},
    "SZ05": {"name": "Imphal Disaster Response HQ (Kangla)", "state": "Manipur", "lat": 24.8074, "lng": 93.9457, "capacity": 3500},
    "SZ06": {"name": "Kohima NSDMA Emergency Staging Area", "state": "Nagaland", "lat": 25.6701, "lng": 94.1077, "capacity": 2200},
    "SZ07": {"name": "Itanagar Raj Bhavan Helipad Relief Zone", "state": "Arunachal Pradesh", "lat": 27.0981, "lng": 93.6214, "capacity": 1800},
    "SZ08": {"name": "Agartala State Emergency Ops Center (SEOC)", "state": "Tripura", "lat": 23.8364, "lng": 91.2750, "capacity": 4000},
}

# Road graph connecting at-risk nodes with safe centers for dynamic Dijkstra evacuation routing
ROAD_EDGES = [
    # Assam network
    ("L01", "L02", 112), ("L02", "SZ01", 22), ("L03", "SZ01", 12), ("L04", "L01", 68),
    # Meghalaya network
    ("L05", "SZ02", 54), ("L06", "L05", 28), ("L07", "SZ02", 14), ("L08", "SZ02", 62), ("L09", "SZ01", 45), ("L09", "SZ02", 52),
    # Sikkim network
    ("L10", "SZ03", 6), ("L11", "L10", 65), ("L12", "SZ03", 72), ("L12", "SZ01", 110), ("L13", "SZ03", 85),
    # Mizoram network
    ("L14", "SZ04", 5), ("L15", "L14", 128), ("L16", "L14", 185),
    # Manipur network
    ("L17", "SZ05", 42), ("L18", "SZ05", 78), ("L19", "SZ05", 84), ("L18", "L20", 52),
    # Nagaland network
    ("L20", "SZ06", 6), ("L21", "SZ06", 44), ("L22", "SZ06", 138),
    # Arunachal network
    ("L23", "SZ07", 8), ("L24", "SZ07", 280), ("L25", "SZ07", 115),
    # Tripura network
    ("L26", "SZ08", 95), ("L27", "SZ08", 145),
    # Inter-state connections
    ("SZ01", "SZ02", 100), ("SZ05", "SZ06", 145), ("SZ02", "SZ04", 320),
]

# In-memory live simulation state
_STATE = {}


def _seasonal_rain_base():
    """Monsoon-season bias reflecting NER climate (May-Oct heavy monsoons)."""
    month = time.gmtime().tm_mon
    if 6 <= month <= 9:
        return 55  # Peak monsoon
    elif month in (5, 10):
        return 30  # Transition monsoons
    else:
        return 10  # Winter/pre-monsoon


def init_state():
    base_rain = _seasonal_rain_base()
    for loc in LOCATIONS:
        historical = loc.get("historical_events", random.randint(2, 8))
        _STATE[loc["id"]] = {
            "rainfall_24h": max(0, random.gauss(base_rain, 18)),
            "rainfall_3day": max(0, random.gauss(base_rain * 2.4, 30)),
            "soil_moisture": min(100, max(15, random.gauss(45, 12))),
            "vegetation_index": round(random.uniform(0.25, 0.75), 3),
            "slope_deg": float(loc["base_slope"]),
            "historical_landslide_count": historical,
        }
    return _STATE


def tick():
    """Advance the simulated sensor feed by one step (called periodically)."""
    base_rain = _seasonal_rain_base()
    for loc in LOCATIONS:
        loc_id = loc["id"]
        if loc_id not in _STATE:
            continue
        s = _STATE[loc_id]
        crit_rain = loc.get("critical_rain_24h", 65.0)
        # Random-walk with mean reversion towards realistic state
        rain_noise = random.gauss(base_rain, 22)
        s["rainfall_24h"] = max(0, s["rainfall_24h"] * 0.65 + rain_noise * 0.35)
        s["rainfall_3day"] = max(0, s["rainfall_3day"] * 0.8 + s["rainfall_24h"] * 0.55)
        # Soil moisture responds to 24h rainfall
        s["soil_moisture"] = min(100.0, max(10.0, s["soil_moisture"] * 0.92 + s["rainfall_24h"] * 0.25))
        s["vegetation_index"] = min(1.0, max(0.05, s["vegetation_index"] + random.gauss(0, 0.005)))
    return _STATE


def get_state():
    if not _STATE:
        init_state()
    return _STATE


def nudge(loc_id, rainfall_delta=0, soil_delta=0, veg_delta=0):
    """What-If simulator perturbation function."""
    s = get_state()[loc_id]
    sim = dict(s)
    sim["rainfall_24h"] = max(0, s["rainfall_24h"] + rainfall_delta)
    sim["rainfall_3day"] = max(0, s["rainfall_3day"] + rainfall_delta * 2.2)
    sim["soil_moisture"] = min(100.0, max(0.0, s["soil_moisture"] + soil_delta))
    sim["vegetation_index"] = min(1.0, max(0.0, s["vegetation_index"] + veg_delta))
    return sim


def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))

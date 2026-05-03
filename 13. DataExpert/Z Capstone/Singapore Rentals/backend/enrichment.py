"""
Static MRT/LRT station data + dynamic school data from OneMap.
Both are cached in memory after first load.
"""
from __future__ import annotations
import json, math, ssl, urllib.request

# ── Haversine distance ────────────────────────────────────────────────────────

def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance in metres between two WGS-84 coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ── MRT / LRT stations (all operational lines as of 2025) ────────────────────
# Format: (name, lat, lng)

MRT_STATIONS: list[tuple[str, float, float]] = [
    # NS Line
    ("Jurong East", 1.3331, 103.7420), ("Bukit Batok", 1.3491, 103.7497),
    ("Bukit Gombak", 1.3588, 103.7516), ("Choa Chu Kang", 1.3853, 103.7444),
    ("Yew Tee", 1.3972, 103.7476), ("Kranji", 1.4252, 103.7616),
    ("Marsiling", 1.4323, 103.7742), ("Woodlands", 1.4369, 103.7860),
    ("Admiralty", 1.4406, 103.8007), ("Sembawang", 1.4490, 103.8199),
    ("Canberra", 1.4431, 103.8298), ("Yishun", 1.4294, 103.8354),
    ("Khatib", 1.4175, 103.8330), ("Yio Chu Kang", 1.3818, 103.8447),
    ("Ang Mo Kio", 1.3700, 103.8495), ("Bishan", 1.3510, 103.8489),
    ("Braddell", 1.3408, 103.8470), ("Toa Payoh", 1.3327, 103.8472),
    ("Novena", 1.3204, 103.8437), ("Newton", 1.3130, 103.8378),
    ("Orchard", 1.3047, 103.8322), ("Somerset", 1.2999, 103.8388),
    ("Dhoby Ghaut", 1.2992, 103.8454), ("City Hall", 1.2930, 103.8520),
    ("Raffles Place", 1.2831, 103.8513), ("Marina Bay", 1.2762, 103.8539),
    ("Marina South Pier", 1.2708, 103.8631),
    # EW Line
    ("Pasir Ris", 1.3730, 103.9493), ("Tampines", 1.3530, 103.9453),
    ("Simei", 1.3434, 103.9529), ("Tanah Merah", 1.3271, 103.9462),
    ("Bedok", 1.3240, 103.9299), ("Kembangan", 1.3210, 103.9124),
    ("Eunos", 1.3197, 103.9029), ("Paya Lebar", 1.3183, 103.8930),
    ("Aljunied", 1.3161, 103.8830), ("Kallang", 1.3113, 103.8713),
    ("Lavender", 1.3074, 103.8622), ("Bugis", 1.3009, 103.8554),
    ("City Hall", 1.2930, 103.8520), ("Raffles Place", 1.2831, 103.8513),
    ("Tanjong Pagar", 1.2765, 103.8455), ("Outram Park", 1.2799, 103.8395),
    ("Tiong Bahru", 1.2864, 103.8271), ("Redhill", 1.2892, 103.8168),
    ("Queenstown", 1.2945, 103.8059), ("Commonwealth", 1.3024, 103.7980),
    ("Buona Vista", 1.3072, 103.7899), ("Dover", 1.3111, 103.7786),
    ("Clementi", 1.3152, 103.7651), ("Jurong East", 1.3331, 103.7420),
    ("Chinese Garden", 1.3423, 103.7324), ("Lakeside", 1.3441, 103.7209),
    ("Boon Lay", 1.3388, 103.7063), ("Pioneer", 1.3368, 103.6970),
    ("Joo Koon", 1.3278, 103.6786), ("Gul Circle", 1.3198, 103.6610),
    ("Tuas Crescent", 1.3214, 103.6484), ("Tuas West Road", 1.3303, 103.6393),
    ("Tuas Link", 1.3403, 103.6370),
    ("Expo", 1.3355, 103.9614), ("Changi Airport", 1.3573, 103.9887),
    # NE Line
    ("HarbourFront", 1.2651, 103.8200), ("Outram Park", 1.2799, 103.8395),
    ("Chinatown", 1.2844, 103.8445), ("Clarke Quay", 1.2884, 103.8467),
    ("Dhoby Ghaut", 1.2992, 103.8454), ("Little India", 1.3066, 103.8494),
    ("Farrer Park", 1.3122, 103.8543), ("Boon Keng", 1.3193, 103.8615),
    ("Potong Pasir", 1.3314, 103.8691), ("Woodleigh", 1.3394, 103.8709),
    ("Serangoon", 1.3498, 103.8738), ("Kovan", 1.3600, 103.8852),
    ("Hougang", 1.3712, 103.8923), ("Buangkok", 1.3830, 103.8929),
    ("Sengkang", 1.3915, 103.8954), ("Punggol", 1.4053, 103.9023),
    # CC Line
    ("Dhoby Ghaut", 1.2992, 103.8454), ("Bras Basah", 1.2966, 103.8508),
    ("Esplanade", 1.2933, 103.8554), ("Promenade", 1.2934, 103.8611),
    ("Nicoll Highway", 1.2999, 103.8636), ("Stadium", 1.3029, 103.8752),
    ("Mountbatten", 1.3062, 103.8822), ("Dakota", 1.3082, 103.8884),
    ("Paya Lebar", 1.3183, 103.8930), ("MacPherson", 1.3267, 103.8898),
    ("Tai Seng", 1.3357, 103.8877), ("Bartley", 1.3424, 103.8797),
    ("Serangoon", 1.3498, 103.8738), ("Lorong Chuan", 1.3513, 103.8641),
    ("Bishan", 1.3510, 103.8489), ("Marymount", 1.3486, 103.8396),
    ("Caldecott", 1.3376, 103.8398), ("Botanic Gardens", 1.3224, 103.8153),
    ("Farrer Road", 1.3174, 103.8075), ("Holland Village", 1.3118, 103.7963),
    ("Buona Vista", 1.3072, 103.7899), ("one-north", 1.2994, 103.7872),
    ("Kent Ridge", 1.2939, 103.7847), ("Haw Par Villa", 1.2826, 103.7820),
    ("Pasir Panjang", 1.2762, 103.7911), ("Labrador Park", 1.2726, 103.8024),
    ("Telok Blangah", 1.2700, 103.8095), ("HarbourFront", 1.2651, 103.8200),
    ("Bayfront", 1.2818, 103.8591), ("Marina Bay", 1.2762, 103.8539),
    # DT Line
    ("Bukit Panjang", 1.3786, 103.7762), ("Cashew", 1.3696, 103.7749),
    ("Hillview", 1.3625, 103.7675), ("Beauty World", 1.3409, 103.7760),
    ("King Albert Park", 1.3351, 103.7827), ("Sixth Avenue", 1.3285, 103.7955),
    ("Tan Kah Kee", 1.3259, 103.8081), ("Botanic Gardens", 1.3224, 103.8153),
    ("Stevens", 1.3194, 103.8252), ("Newton", 1.3130, 103.8378),
    ("Little India", 1.3066, 103.8494), ("Rochor", 1.3043, 103.8524),
    ("Bugis", 1.3009, 103.8554), ("Promenade", 1.2934, 103.8611),
    ("Bayfront", 1.2818, 103.8591), ("Downtown", 1.2793, 103.8530),
    ("Telok Ayer", 1.2816, 103.8481), ("Fort Canning", 1.2920, 103.8444),
    ("Bencoolen", 1.2975, 103.8493), ("Jalan Besar", 1.3046, 103.8556),
    ("Bendemeer", 1.3130, 103.8622), ("Geylang Bahru", 1.3216, 103.8715),
    ("Mattar", 1.3262, 103.8842), ("MacPherson", 1.3267, 103.8898),
    ("Ubi", 1.3291, 103.8993), ("Kaki Bukit", 1.3349, 103.9078),
    ("Bedok North", 1.3330, 103.9156), ("Bedok Reservoir", 1.3365, 103.9315),
    ("Tampines West", 1.3458, 103.9378), ("Tampines", 1.3530, 103.9453),
    ("Tampines East", 1.3566, 103.9532), ("Upper Changi", 1.3416, 103.9614),
    ("Expo", 1.3355, 103.9614),
    # TE Line (operational stations)
    ("Woodlands North", 1.4480, 103.7864), ("Woodlands", 1.4369, 103.7860),
    ("Woodlands South", 1.4274, 103.7913), ("Springleaf", 1.3998, 103.8161),
    ("Lentor", 1.3843, 103.8353), ("Mayflower", 1.3702, 103.8360),
    ("Bright Hill", 1.3627, 103.8326), ("Upper Thomson", 1.3548, 103.8318),
    ("Caldecott", 1.3376, 103.8398), ("Stevens", 1.3194, 103.8252),
    ("Napier", 1.3058, 103.8193), ("Orchard Boulevard", 1.3019, 103.8265),
    ("Orchard", 1.3047, 103.8322), ("Great World", 1.2942, 103.8311),
    ("Havelock", 1.2879, 103.8379), ("Outram Park", 1.2799, 103.8395),
    ("Maxwell", 1.2798, 103.8446), ("Shenton Way", 1.2759, 103.8479),
    ("Marina Bay", 1.2762, 103.8539), ("Gardens by the Bay", 1.2814, 103.8655),
    ("Tanjong Rhu", 1.3028, 103.8743), ("Katong Park", 1.3076, 103.8877),
    ("Tanjong Katong", 1.3060, 103.9005), ("Marine Parade", 1.3026, 103.9075),
    ("Marine Terrace", 1.3030, 103.9137), ("Siglap", 1.3107, 103.9253),
    ("Bayshore", 1.3151, 103.9390), ("Bedok South", 1.3196, 103.9485),
    ("Sungei Bedok", 1.3340, 103.9657),
]

# Deduplicate by name+coordinates
_seen: set[tuple[str, float, float]] = set()
_unique: list[tuple[str, float, float]] = []
for _s in MRT_STATIONS:
    key = (_s[0], round(_s[1], 4), round(_s[2], 4))
    if key not in _seen:
        _seen.add(key)
        _unique.append(_s)
MRT_STATIONS = _unique


def nearest_mrt(lat: float, lng: float) -> dict:
    best_name, best_dist = "", float("inf")
    for name, slat, slng in MRT_STATIONS:
        d = haversine_m(lat, lng, slat, slng)
        if d < best_dist:
            best_dist, best_name = d, name
    return {"station": best_name, "distance_m": round(best_dist)}


# ── Schools from OneMap (cached) ─────────────────────────────────────────────

_schools_cache: list[dict] | None = None
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


_SCHOOL_KEYWORDS = ("PRIMARY SCHOOL", "SECONDARY SCHOOL", "JUNIOR COLLEGE", "HIGH SCHOOL")

# Words that indicate a real MOE/EduMall school vs. a random named "school"
_SCHOOL_MARKERS = ("PRIMARY", "SECONDARY", "JUNIOR COLLEGE", "HIGH SCHOOL",
                   "INSTITUTE", "ACADEMY", "POLYTECHNIC", "INTERNATIONAL SCHOOL")


def _fetch_one_term(term: str, headers: dict) -> list[dict]:
    results: list[dict] = []
    page = 1
    while True:
        url = (
            f"https://www.onemap.gov.sg/api/common/elastic/search"
            f"?searchVal={term.replace(' ', '+')}&returnGeom=Y&getAddrDetails=N&pageNum={page}"
        )
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=8) as resp:
                data = json.loads(resp.read())
        except Exception:
            break
        for r in data.get("results", []):
            try:
                lat, lng = float(r["LATITUDE"]), float(r["LONGITUDE"])
                name = r.get("SEARCHVAL", "").strip().upper()
                if lat and lng and any(m in name for m in _SCHOOL_MARKERS):
                    results.append({"name": name.title(), "lat": lat, "lng": lng})
            except (KeyError, ValueError):
                continue
        if page >= data.get("totalNumPages", 1):
            break
        page += 1
    return results


def _fetch_schools() -> list[dict]:
    """Fetch real schools from OneMap using specific search terms."""
    headers = {"User-Agent": "SingaporeRentalsDashboard/1.0"}
    seen: set[tuple[float, float]] = set()
    schools: list[dict] = []
    for term in _SCHOOL_KEYWORDS:
        for s in _fetch_one_term(term, headers):
            key = (round(s["lat"], 4), round(s["lng"], 4))
            if key not in seen:
                seen.add(key)
                schools.append(s)
    return schools


def get_schools() -> list[dict]:
    global _schools_cache
    if _schools_cache is None:
        _schools_cache = _fetch_schools()
    return _schools_cache


def schools_within(lat: float, lng: float, radius_m: float = 1000) -> list[dict]:
    return [
        s for s in get_schools()
        if haversine_m(lat, lng, s["lat"], s["lng"]) <= radius_m
    ]


# ── MRT line sequences ────────────────────────────────────────────────────────
# Each line is an ordered list of station names; coordinates looked up from MRT_STATIONS.

_COORD = {name: (lat, lng) for name, lat, lng in MRT_STATIONS}

MRT_LINE_SEQUENCES: dict[str, dict] = {
    "NS": {
        "color": "#D42E12",
        "stations": [
            "Jurong East","Bukit Batok","Bukit Gombak","Choa Chu Kang","Yew Tee",
            "Kranji","Marsiling","Woodlands","Admiralty","Sembawang","Canberra",
            "Yishun","Khatib","Yio Chu Kang","Ang Mo Kio","Bishan","Braddell",
            "Toa Payoh","Novena","Newton","Orchard","Somerset","Dhoby Ghaut",
            "City Hall","Raffles Place","Marina Bay","Marina South Pier",
        ],
    },
    "EW": {
        "color": "#009645",
        "stations": [
            "Tuas Link","Tuas West Road","Tuas Crescent","Gul Circle","Joo Koon",
            "Pioneer","Boon Lay","Lakeside","Chinese Garden","Jurong East",
            "Clementi","Dover","Buona Vista","Commonwealth","Queenstown","Redhill",
            "Tiong Bahru","Outram Park","Tanjong Pagar","Raffles Place","City Hall",
            "Bugis","Lavender","Kallang","Aljunied","Paya Lebar","Eunos",
            "Kembangan","Bedok","Tanah Merah","Simei","Tampines","Pasir Ris",
        ],
    },
    "EW-CG": {
        "color": "#009645",
        "stations": ["Tanah Merah","Expo","Changi Airport"],
    },
    "NE": {
        "color": "#9900AA",
        "stations": [
            "HarbourFront","Outram Park","Chinatown","Clarke Quay","Dhoby Ghaut",
            "Little India","Farrer Park","Boon Keng","Potong Pasir","Woodleigh",
            "Serangoon","Kovan","Hougang","Buangkok","Sengkang","Punggol",
        ],
    },
    "CC": {
        "color": "#FA9E0D",
        "stations": [
            "Dhoby Ghaut","Bras Basah","Esplanade","Promenade","Nicoll Highway",
            "Stadium","Mountbatten","Dakota","Paya Lebar","MacPherson","Tai Seng",
            "Bartley","Serangoon","Lorong Chuan","Bishan","Marymount","Caldecott",
            "Botanic Gardens","Farrer Road","Holland Village","Buona Vista",
            "one-north","Kent Ridge","Haw Par Villa","Pasir Panjang","Labrador Park",
            "Telok Blangah","HarbourFront",
        ],
    },
    "CC-CE": {
        "color": "#FA9E0D",
        "stations": ["Promenade","Bayfront","Marina Bay"],
    },
    "DT": {
        "color": "#005EC4",
        "stations": [
            "Bukit Panjang","Cashew","Hillview","Beauty World","King Albert Park",
            "Sixth Avenue","Tan Kah Kee","Botanic Gardens","Stevens","Newton",
            "Little India","Rochor","Bugis","Promenade","Bayfront","Downtown",
            "Telok Ayer","Fort Canning","Bencoolen","Jalan Besar","Bendemeer",
            "Geylang Bahru","Mattar","MacPherson","Ubi","Kaki Bukit","Bedok North",
            "Bedok Reservoir","Tampines West","Tampines","Tampines East",
            "Upper Changi","Expo",
        ],
    },
    "TE": {
        "color": "#9D5B25",
        "stations": [
            "Woodlands North","Woodlands","Woodlands South","Springleaf","Lentor",
            "Mayflower","Bright Hill","Upper Thomson","Caldecott","Stevens",
            "Napier","Orchard Boulevard","Orchard","Great World","Havelock",
            "Outram Park","Maxwell","Shenton Way","Marina Bay","Gardens by the Bay",
            "Tanjong Rhu","Katong Park","Tanjong Katong","Marine Parade",
            "Marine Terrace","Siglap","Bayshore","Bedok South","Sungei Bedok",
        ],
    },
}


def mrt_stops_geojson() -> dict:
    """Return GeoJSON FeatureCollection of MRT station stops (unique, coloured by primary line)."""
    seen: dict[str, str] = {}   # name → color of first line encountered
    for info in MRT_LINE_SEQUENCES.values():
        for name in info["stations"]:
            if name not in seen:
                seen[name] = info["color"]

    features = []
    for name, color in seen.items():
        if name in _COORD:
            lat, lng = _COORD[name]
            features.append({
                "type": "Feature",
                "properties": {"name": name, "color": color},
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
            })
    return {"type": "FeatureCollection", "features": features}


def mrt_lines_geojson() -> dict:
    """Return GeoJSON FeatureCollection of MRT lines as LineStrings."""
    features = []
    for line_id, info in MRT_LINE_SEQUENCES.items():
        coords = []
        for name in info["stations"]:
            if name in _COORD:
                lat, lng = _COORD[name]
                coords.append([lng, lat])   # GeoJSON is [lng, lat]
        if len(coords) >= 2:
            features.append({
                "type": "Feature",
                "properties": {"line": line_id, "color": info["color"]},
                "geometry": {"type": "LineString", "coordinates": coords},
            })
    return {"type": "FeatureCollection", "features": features}

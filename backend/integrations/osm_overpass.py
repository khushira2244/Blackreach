# integrations/osm_overpass.py
"""
OSM (via Overpass API) helper for Blackreach.

Goal:
- Query semantic safety context around a coordinate (within radius_m)
- Return compact "Gemini-ready" summary:
  - context_flags: is_isolated, is_dark, in_green_belt, has_police_nearby
  - raw_stats: security_points, medical_points, social_eyes, dark_segments
  - terrain: detected tags (wood/forest/park/scrub/grass/etc.)

Delhi/India upgrades included:
1) Nature/green detection expanded: natural, landuse, leisure, boundary
2) Lighting reality check: if lit != yes on relevant highway types, count as dark
3) Weighted stats: police > medical > social eyes; flags derived from stats

No API key required.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set
import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


# These highway types are the ones that matter most for pedestrian safety in India.
# (You can tweak anytime)
PEDESTRIAN_RELEVANT_HIGHWAYS = {
    "footway",
    "path",
    "residential",
    "tertiary",
    "service",
    "unclassified",
    "living_street",
    "track",
    "cycleway",
    "steps",
}


# Terrain tags we care about around IIT Delhi / RK Puram / Ridge areas
TERRAIN_TAGS = {
    "wood",
    "forest",
    "scrub",
    "park",
    "grass",
    "recreation_ground",
}

# boundary tag variants you may encounter
BOUNDARY_TAGS = {
    "forest",
    "protected_area",
    "national_park",
}


def build_overpass_query(lat: float, lng: float, radius_m: int) -> str:
    """
    One combined query to keep it fast:
    - amenities for help and "social eyes"
    - ways for highway + lighting
    - terrain tags (natural/landuse/leisure/boundary)
    """
    return f"""
    [out:json][timeout:20];
    (
      node(around:{radius_m},{lat},{lng})["amenity"~"police|hospital|clinic|pharmacy|cafe|restaurant"];
      node(around:{radius_m},{lat},{lng})["shop"];
      way(around:{radius_m},{lat},{lng})["highway"];
      way(around:{radius_m},{lat},{lng})["natural"];
      way(around:{radius_m},{lat},{lng})["landuse"];
      way(around:{radius_m},{lat},{lng})["leisure"];
      way(around:{radius_m},{lat},{lng})["boundary"];
    );
    out tags center;
    """


async def overpass_raw(lat: float, lng: float, radius_m: int = 500) -> Dict[str, Any]:
    q = build_overpass_query(lat, lng, radius_m)
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.post(OVERPASS_URL, data={"data": q})
        resp.raise_for_status()
        return resp.json()


def summarize_overpass(raw: Dict[str, Any]) -> Dict[str, Any]:
    elements = raw.get("elements") or []
    if not isinstance(elements, list):
        elements = []

    # Gemini brain-food: small number of meaningful counters
    stats = {
        "security_points": 0,  # police
        "medical_points": 0,   # hospital/clinic
        "social_eyes": 0,      # cafes/restaurant/shops
        "dark_segments": 0,    # likely dark road/path segments
    }

    terrain: Set[str] = set()

    for el in elements:
        tags = el.get("tags") or {}
        if not isinstance(tags, dict):
            continue

        amenity = tags.get("amenity")
        shop = tags.get("shop")

        # 1) Priority: police > medical > social eyes
        if amenity == "police":
            stats["security_points"] += 1
        elif amenity in ("hospital", "clinic"):
            stats["medical_points"] += 1
        elif amenity in ("cafe", "restaurant") or shop:
            stats["social_eyes"] += 1

        # 2) India lighting reality check:
        # If lit != yes on pedestrian-relevant roads, treat as dark.
        highway_type = tags.get("highway")
        lit_status = tags.get("lit")  # often missing in India
        if highway_type in PEDESTRIAN_RELEVANT_HIGHWAYS and lit_status != "yes":
            stats["dark_segments"] += 1

        # 3) Delhi green-belts: natural/wood, landuse=forest, leisure=park, boundary=forest-ish
        n = tags.get("natural")
        if n in TERRAIN_TAGS:
            terrain.add(n)

        lu = tags.get("landuse")
        if lu in TERRAIN_TAGS:
            terrain.add(lu)

        le = tags.get("leisure")
        if le in TERRAIN_TAGS:
            terrain.add(le)

        b = tags.get("boundary")
        if b in BOUNDARY_TAGS:
            terrain.add(f"boundary:{b}")

    # Flags (keep explainable)
    context_flags = {
        "is_isolated": (stats["social_eyes"] == 0 and stats["security_points"] == 0),
        "is_dark": (stats["dark_segments"] > 0),
        "in_green_belt": (len(terrain) > 0),
        "has_police_nearby": (stats["security_points"] > 0),
    }

    # Optional: a simple "hint score" for UI (not a universal truth, just a demo metric)
    # You can tweak weights.
    safety_boost = (10 * stats["security_points"]) + (5 * stats["medical_points"]) + (2 * stats["social_eyes"])
    risk_penalty = (3 * stats["dark_segments"]) + (6 if context_flags["in_green_belt"] else 0) + (5 if context_flags["is_isolated"] else 0)
    context_score = max(0, safety_boost - risk_penalty)

    return {
        "context_flags": context_flags,
        "raw_stats": stats,
        "terrain": sorted(list(terrain))[:12],
        "context_score": context_score,
        "elements_count": len(elements),
    }


async def overpass_summary(lat: float, lng: float, radius_m: int = 500) -> Dict[str, Any]:
    raw = await overpass_raw(lat, lng, radius_m=radius_m)
    return {
        "query": {"lat": lat, "lng": lng, "radius_m": radius_m},
        "summary": summarize_overpass(raw),
    }


async def segment_overpass_summary(samples: List[Dict[str, float]], radius_m: int = 500) -> Dict[str, Any]:
    """
    If you want route sampling (25/60/100%), same pattern as your Places segment summary.
    """
    per_sample: List[Dict[str, Any]] = []

    merged_stats = {
        "security_points": 0,
        "medical_points": 0,
        "social_eyes": 0,
        "dark_segments": 0,
    }
    merged_terrain: Set[str] = set()

    flags_any = {
        "is_isolated_any": False,
        "is_dark_any": False,
        "in_green_belt_any": False,
        "has_police_nearby_any": False,
    }

    for s in samples:
        lat = float(s["lat"])
        lng = float(s["lng"])
        res = await overpass_summary(lat, lng, radius_m=radius_m)
        per_sample.append(res)

        summ = res["summary"]
        rs = summ.get("raw_stats") or {}
        for k in merged_stats.keys():
            merged_stats[k] += int(rs.get(k, 0))

        for t in (summ.get("terrain") or []):
            merged_terrain.add(t)

        cf = summ.get("context_flags") or {}
        flags_any["is_isolated_any"] = flags_any["is_isolated_any"] or bool(cf.get("is_isolated"))
        flags_any["is_dark_any"] = flags_any["is_dark_any"] or bool(cf.get("is_dark"))
        flags_any["in_green_belt_any"] = flags_any["in_green_belt_any"] or bool(cf.get("in_green_belt"))
        flags_any["has_police_nearby_any"] = flags_any["has_police_nearby_any"] or bool(cf.get("has_police_nearby"))

    return {
        "samples": samples,
        "radius_m": radius_m,
        "merged": {
            "raw_stats_total": merged_stats,
            "terrain_union": sorted(list(merged_terrain))[:12],
            "flags_any": flags_any,
        },
        "per_sample": per_sample,
    }

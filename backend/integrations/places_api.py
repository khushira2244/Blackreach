# integrations/places_api.py
"""
Places API (New) helper for Blackreach.

Goal:
- Query "what exists near a coordinate" (Nearby Search)
- Return a compact summary for Gemini:
  - poi_count
  - open_count
  - types_count (police/hospital/cafe/parking/transit/industrial/park/bar/night_club/etc.)
  - dead_zone flag

ENV REQUIRED:
- GOOGLE_MAPS_API_KEY

Notes (Places API New):
- Uses HTTP header "X-Goog-Api-Key"
- Requires "X-Goog-FieldMask" header, otherwise response will be empty/minimal.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

PLACES_NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Keep fields minimal for speed/cost
DEFAULT_FIELDMASK = ",".join(
    [
        "places.types",
        "places.businessStatus",
        "places.displayName",
    ]
)

# Place types you care about (extend anytime)
# (We'll count any unknown types too, but these are the ones your UI/Gemini reasons over.)
TRACK_TYPES = {
    "police",
    "hospital",
    "pharmacy",
    "shopping_mall",
    "cafe",
    "restaurant",
    "bar",
    "night_club",
    "park",
    "parking",
    "subway_station",
    "transit_station",
    "bus_station",
    "train_station",
    "airport",
    "gas_station",
    "lodging",
    "tourist_attraction",
    "school",
    "university",
    "stadium",
    "movie_theater",
    "bank",
    "atm",
    "supermarket",
    "convenience_store",
    "department_store",
    "gym",
    "place_of_worship",
    "construction",
    "industrial",
    "warehouse",
}


def _get_env(name: str, default: Optional[str] = None) -> str:
    v = os.getenv(name, default)
    if not v:
        raise RuntimeError(f"{name} is missing in environment")
    return v


def _inc(d: Dict[str, int], key: str, by: int = 1) -> None:
    d[key] = int(d.get(key, 0)) + by


def summarize_places(places: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Converts raw Places response (list of place dicts) into compact summary.
    """
    poi_count = len(places)
    open_count = 0
    types_count: Dict[str, int] = {}

    for p in places:
        # businessStatus: "OPERATIONAL" vs others (CLOSED_TEMPORARILY, CLOSED_PERMANENTLY)
        # Places New doesn't guarantee openNow on all calls; keep it robust.
        bs = (p.get("businessStatus") or "").upper()
        if bs == "OPERATIONAL":
            open_count += 1

        types = p.get("types") or []
        if isinstance(types, list):
            for t in types:
                # Count all types; emphasize the track list
                if isinstance(t, str) and t:
                    _inc(types_count, t)

    # Dead-zone heuristic: too few POIs
    dead_zone = poi_count <= 1  # tune if needed

    # Optional: also return "top types"
    top_types = sorted(types_count.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {
        "poi_count": poi_count,
        "open_count": open_count,
        "dead_zone": dead_zone,
        "types_count": types_count,
        "top_types": [{"type": k, "count": v} for k, v in top_types],
    }


async def nearby_search_raw(
    lat: float,
    lng: float,
    radius_m: int = 200,
    max_results: int = 20,
    fieldmask: str = DEFAULT_FIELDMASK,
) -> Dict[str, Any]:
    """
    Calls Places API (New) Nearby Search and returns the raw JSON.

    radius_m:
      - 100–250m is good for "what's around this point".
      - You will call this 3 times (25/60/100%), so keep radius small and max_results modest.
    """
    api_key = _get_env("GOOGLE_MAPS_API_KEY")

    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": fieldmask,
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_m),
            }
        },
        "maxResultCount": int(max_results),
    }

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.post(PLACES_NEARBY_URL, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def nearby_search_summary(
    lat: float,
    lng: float,
    radius_m: int = 200,
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    Calls Places Nearby Search (New) and returns a compact summary.
    Never throws for parsing issues; only raises for missing env or HTTP errors.
    """
    raw = await nearby_search_raw(
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        max_results=max_results,
    )
    places = raw.get("places") or []
    if not isinstance(places, list):
        places = []
    summary = summarize_places(places)

    return {
        "query": {"lat": lat, "lng": lng, "radius_m": radius_m, "max_results": max_results},
        "summary": summary,
    }


async def segment_places_summary(
    samples: List[Dict[str, float]],
    radius_m: int = 200,
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    Convenience: call Nearby search on multiple sample points and merge summaries.

    samples: [{"lat":..,"lng":..}, ...] (typically 3 points: 25/60/100)
    """
    combined_types: Dict[str, int] = {}
    total_poi = 0
    total_open = 0
    any_dead_zone = False
    per_sample: List[Dict[str, Any]] = []

    for s in samples:
        lat = float(s["lat"])
        lng = float(s["lng"])
        res = await nearby_search_summary(lat, lng, radius_m=radius_m, max_results=max_results)
        per_sample.append(res)

        summ = res["summary"]
        total_poi += int(summ.get("poi_count", 0))
        total_open += int(summ.get("open_count", 0))
        any_dead_zone = any_dead_zone or bool(summ.get("dead_zone", False))

        types_count = summ.get("types_count") or {}
        if isinstance(types_count, dict):
            for k, v in types_count.items():
                if isinstance(k, str) and isinstance(v, int):
                    _inc(combined_types, k, v)

    top_types = sorted(combined_types.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {
        "samples": samples,
        "radius_m": radius_m,
        "max_results": max_results,
        "merged": {
            "poi_count_total": total_poi,
            "open_count_total": total_open,
            "dead_zone_any": any_dead_zone,
            "types_count": combined_types,
            "top_types": [{"type": k, "count": v} for k, v in top_types],
        },
        "per_sample": per_sample,  # useful for debugging + demo “trend”
    }

import os
from typing import Optional, Tuple

import httpx

ROADS_SNAP_URL = "https://roads.googleapis.com/v1/snapToRoads"


async def snap_to_roads(lat: float, lng: float) -> Optional[Tuple[float, float]]:
    """
    Async Snap-to-Roads.
    Returns (snapped_lat, snapped_lng) or None if snapping fails.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is missing in environment")

    params = {
        "path": f"{lat},{lng}",
        "interpolate": "false",
        "key": api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(ROADS_SNAP_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    snapped = data.get("snappedPoints") or []
    if not snapped:
        return None

    loc = snapped[0].get("location") or {}
    s_lat = loc.get("latitude")
    s_lng = loc.get("longitude")

    if s_lat is None or s_lng is None:
        return None

    return float(s_lat), float(s_lng)

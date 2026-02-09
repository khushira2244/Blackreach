import httpx
from core.config import GOOGLE_MAPS_API_KEY

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


async def compute_routes_polyline(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    travel_mode: str = "DRIVE",
) -> dict:
    """
    Calls Google Routes API and returns minimal route info needed for Phase-1 slider:
    - encoded polyline
    - distance (meters)
    - duration (seconds)
    """

    body = {
        "origin": {
            "location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}
        },
        "destination": {
            "location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}
        },
        "travelMode": travel_mode,
        "computeAlternativeRoutes": False,
        "routingPreference": "TRAFFIC_UNAWARE",
        "units": "METRIC",
        "languageCode": "en-US",
    }

    headers = {
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        # Ask only what we need (super important)
        "X-Goog-FieldMask": "routes.polyline.encodedPolyline,routes.distanceMeters,routes.duration",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(ROUTES_URL, json=body, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"Routes API error {resp.status_code}: {resp.text}")

    data = resp.json()
    if not data.get("routes"):
        raise RuntimeError(f"Routes API: no routes returned: {data}")

    r0 = data["routes"][0]
    polyline = r0["polyline"]["encodedPolyline"]
    distance_m = int(r0["distanceMeters"])
    duration_s = int(str(r0["duration"]).replace("s", ""))

    return {
        "polyline": polyline,
        "distance_m": distance_m,
        "duration_s": duration_s,
    }

  
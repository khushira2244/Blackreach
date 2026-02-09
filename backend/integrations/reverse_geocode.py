import httpx
from core.config import GOOGLE_MAPS_API_KEY

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# We prefer "areas", not exact street.
PREFERRED_TYPES = [
    "sublocality_level_1",
    "sublocality",
    "neighborhood",
    "locality",
    "administrative_area_level_2",
    "administrative_area_level_1",
]

async def reverse_geocode_area(lat: float, lng: float) -> str:
    params = {
        "latlng": f"{lat},{lng}",
        "key": GOOGLE_MAPS_API_KEY,
        "language": "en",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(GEOCODE_URL, params=params)

    if resp.status_code != 200:
        raise RuntimeError(f"Geocoding error {resp.status_code}: {resp.text}")

    data = resp.json()
    if data.get("status") != "OK":
        raise RuntimeError(f"Geocoding status: {data.get('status')} {data.get('error_message','')}")

    results = data.get("results", [])
    if not results:
        return "Unknown Area"

    # Try to pick an "area-like" component (not road/street)
    for r in results:
        for comp in r.get("address_components", []):
            types = comp.get("types", [])
            for t in PREFERRED_TYPES:
                if t in types:
                    return comp.get("long_name", "Unknown Area")

    # Fallback: use formatted address (last resort)
    return results[0].get("formatted_address", "Unknown Area")

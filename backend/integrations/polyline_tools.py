from math import radians, sin, cos, sqrt, atan2
from typing import List, Dict


def decode_polyline(encoded: str) -> List[Dict[str, float]]:
    """
    Decode a Google encoded polyline into a list of {lat, lng}.
    Pure Python (no extra dependency).
    """
    points = []
    index = 0
    lat = 0
    lng = 0
    length = len(encoded)

    while index < length:
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += dlat

        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        dlng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += dlng

        points.append({"lat": lat / 1e5, "lng": lng / 1e5})

    return points


def haversine_m(a: Dict[str, float], b: Dict[str, float]) -> float:
    """
    Distance between two lat/lng points in meters.
    """
    R = 6371000.0
    lat1 = radians(a["lat"])
    lon1 = radians(a["lng"])
    lat2 = radians(b["lat"])
    lon2 = radians(b["lng"])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    s = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(s), sqrt(1 - s))
    return R * c


def sample_points_every_m(points: List[Dict[str, float]], every_m: int = 500) -> List[Dict[str, float]]:
    """
    Given a dense polyline (decoded points), return a smaller list of points
    approximately every `every_m` meters along the path.

    This is what you'll reverse-geocode to get area names for the slider.
    """
    if not points:
        return []

    sampled = [points[0]]
    dist_acc = 0.0

    for i in range(1, len(points)):
        seg = haversine_m(points[i - 1], points[i])
        dist_acc += seg

        if dist_acc >= every_m:
            sampled.append(points[i])
            dist_acc = 0.0

    # Ensure destination included
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])

    return sampled


def dedupe_close_points(points: List[Dict[str, float]], min_gap_m: int = 150) -> List[Dict[str, float]]:
    """
    Optional helper: remove points that are too close to each other.
    Helps reduce reverse geocoding calls (cost + speed).
    """
    if not points:
        return []

    out = [points[0]]
    for p in points[1:]:
        if haversine_m(out[-1], p) >= min_gap_m:
            out.append(p)
    return out

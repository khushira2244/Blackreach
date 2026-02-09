
import math
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from integrations.routes_api import compute_routes_polyline
from integrations.polyline_tools import decode_polyline, sample_points_every_m
from integrations.reverse_geocode import reverse_geocode_area

router = APIRouter(prefix="/journey", tags=["journey"])


# -------------------------
# Models
# -------------------------
class LatLng(BaseModel):
    lat: float
    lng: float


class JourneyPlanReq(BaseModel):
    origin: LatLng
    destination: LatLng
    travelMode: str = "DRIVE"


Mode = Literal["TRACKING", "PERSONNEL"]


class JourneyPriceReq(BaseModel):
    distance_m: int = Field(..., ge=1)
    areas_count: int = Field(..., ge=2)
    start_index: int = Field(..., ge=0)
    end_index: int = Field(..., ge=0)
    mode: Mode = "TRACKING"


# -------------------------
# Routes
# -------------------------
@router.post("/plan")
async def plan_journey(req: JourneyPlanReq):
    try:
        # 1) Get route polyline + distance/duration from Google Routes API
        route = await compute_routes_polyline(
            origin_lat=req.origin.lat,
            origin_lng=req.origin.lng,
            dest_lat=req.destination.lat,
            dest_lng=req.destination.lng,
            travel_mode=req.travelMode,
        )

        encoded = route["polyline"]

        # 2) Decode polyline to dense points
        points = decode_polyline(encoded)

        # 3) Sample points every N meters for reverse geocoding (slider brain)
        sampled = sample_points_every_m(points, every_m=500)

        # 4) Reverse geocode sampled points into area labels (dedupe consecutive)
        areas = []
        last = None
        for p in sampled:
            area = await reverse_geocode_area(p["lat"], p["lng"])
            if area and area != last:
                areas.append(area)
                last = area

        return {
            "polyline": route["polyline"],
            "distance_m": route["distance_m"],
            "duration_s": route["duration_s"],
            "areas": areas,
            "sample_points": sampled,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/price")
def price_journey(req: JourneyPriceReq):
    # Validate indices range
    if req.start_index >= req.areas_count:
        raise HTTPException(status_code=400, detail="start_index must be < areas_count")

    if req.end_index >= req.areas_count:
        raise HTTPException(status_code=400, detail="end_index must be < areas_count")

    # Validate ordering
    if req.start_index >= req.end_index:
        raise HTTPException(status_code=400, detail="end_index must be greater than start_index")

    # Coverage ratio based on slider selection (segments covered / total segments)
    denom = req.areas_count - 1  # safe because areas_count >= 2
    ratio = (req.end_index - req.start_index) / denom  # expected 0..1
    ratio = max(0.0, min(1.0, ratio))  # defensive clamp

    covered_m = req.distance_m * ratio
    covered_km = covered_m / 1000.0

    # Simple hackathon pricing tiers
    if req.mode == "TRACKING":
        base = 29
        per_km = 6
    else:  # PERSONNEL
        base = 149
        per_km = 20

    variable = math.ceil(covered_km * per_km)
    price_inr = int(base + variable)

    return {
        "covered_km": round(covered_km, 2),
        "mode": req.mode,
        "estimatedPriceINR": price_inr,
        "breakdown": {
            "base": base,
            "per_km": per_km,
            "ratio": round(ratio, 3),
        },
    }

// src/components/Map/TrackingCommonMap.jsx
import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  Tooltip,
  useMap,
  Circle,
} from "react-leaflet";
import { useEffect, useMemo } from "react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";


import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function FollowMarker({ position, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (!position) return;
    map.setView(position, zoom, { animate: true });
  }, [map, position, zoom]);
  return null;
}


const makePulseIcon = () =>
  L.divIcon({
    className: "subcenter-pulse-icon",
    html: `<span class="pulse-ring"></span><span class="pulse-dot"></span>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });

export default function TrackingCommonMap({
  plan,
  liveIdx = 0,
  zoom = 14,
  height = 420,
  startLabel = "Start",
  endLabel = "End",
  currentLabel = "",
  showSubcenters = false,
  subcenters = [], 
}) {
  const points = plan?.sample_points || [];

  const safeIdx = Math.max(0, Math.min(liveIdx, Math.max(points.length - 1, 0)));
  const current = points?.[safeIdx] || null;

  const start = points?.[0] || null;
  const end = points?.[points.length - 1] || null;

  const currentPos = useMemo(() => {
    if (!current) return [28.54559, 77.19274];
    return [current.lat, current.lng];
  }, [current]);

  const routePositions = useMemo(() => {
    return points.map((p) => [p.lat, p.lng]);
  }, [points]);

  const pulseIcon = useMemo(() => makePulseIcon(), []);

  return (
    <div
      style={{
        height,
        width: "100%",
        borderRadius: 12,
        overflow: "hidden",
        position: "relative",
      }}
    >
     
      <style>{`
        .subcenter-pulse-icon { background: transparent; border: none; }
        .subcenter-pulse-icon .pulse-dot{
          position:absolute; left:50%; top:50%;
          width:10px; height:10px; transform:translate(-50%,-50%);
          border-radius:50%;
          background:#ff2d2d;
          box-shadow:0 0 10px rgba(255,45,45,.8);
        }
        .subcenter-pulse-icon .pulse-ring{
          position:absolute; left:50%; top:50%;
          width:10px; height:10px; transform:translate(-50%,-50%);
          border-radius:50%;
          border:2px solid rgba(255,45,45,.75);
          animation:pulse 1.6s ease-out infinite;
        }
        @keyframes pulse{
          0%{ width:10px; height:10px; opacity:.9; }
          100%{ width:52px; height:52px; opacity:0; }
        }
      `}</style>

      <MapContainer center={currentPos} zoom={zoom} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution="© OpenStreetMap"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {routePositions.length >= 2 && <Polyline positions={routePositions} weight={4} />}

        {start && (
          <Marker position={[start.lat, start.lng]}>
            <Tooltip permanent direction="top" offset={[0, -10]} opacity={1}>
              {startLabel}
            </Tooltip>
          </Marker>
        )}

        {end && (
          <Marker position={[end.lat, end.lng]}>
            <Tooltip permanent direction="top" offset={[0, -10]} opacity={1}>
              {endLabel}
            </Tooltip>
          </Marker>
        )}

     
        {showSubcenters &&
          Array.isArray(subcenters) &&
          subcenters.map((sc) => {
            if (typeof sc?.lat !== "number" || typeof sc?.lng !== "number") return null;
            const radius = typeof sc.radius_m === "number" ? sc.radius_m : 250;

            return (
              <span key={sc.id || `${sc.lat},${sc.lng}`}>
                <Circle
                  center={[sc.lat, sc.lng]}
                  radius={radius}
                  pathOptions={{
                    color: "red",
                    fillColor: "red",
                    fillOpacity: 0.12,
                    weight: 1,
                  }}
                />
                <Marker position={[sc.lat, sc.lng]} icon={pulseIcon}>
                  <Tooltip direction="top" offset={[0, -10]} opacity={1} permanent={false}>
                    {sc.name || "Subcenter"}
                  </Tooltip>
                </Marker>
              </span>
            );
          })}

        {current && (
          <>
            <FollowMarker position={currentPos} zoom={zoom} />
            <Marker position={[current.lat, current.lng]}>
              <Tooltip direction="top" offset={[0, -10]} opacity={1} permanent>
                {currentLabel || "Live"}
              </Tooltip>
            </Marker>
          </>
        )}
      </MapContainer>
    </div>
  );
}

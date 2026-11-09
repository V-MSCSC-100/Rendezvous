"""
HF Deluxe Pro Manager - OSRM Routing API Client
Calculates road routes, distances, durations, and geometry for multi-stop motorcycle trips.
Includes offline Haversine distance fallback and non-blocking asynchronous execution.
"""

import math
import threading
import requests
import logging
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any, Optional, Callable

logger = logging.getLogger("hf_manager.routing")

OSRM_DEFAULT_URL = "https://router.project-osrm.org"


@dataclass
class RouteResult:
    distance_km: float
    duration_minutes: float
    geometry_coords: List[Tuple[float, float]]  # List of (latitude, longitude)
    is_estimate_fallback: bool = False
    error_message: Optional[str] = None


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in km."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


class RoutingService:
    """Thread-safe OSRM routing client with offline fallback."""

    def __init__(self, base_url: str = OSRM_DEFAULT_URL):
        self.base_url = base_url.rstrip("/")

    def calculate_route(
        self,
        waypoint_coords: List[Tuple[float, float]],  # List of (lat, lon)
        timeout: float = 10.0,
    ) -> RouteResult:
        """
        Calculate driving route across ordered waypoints via OSRM.
        Falls back to haversine estimation if offline or request fails.
        """
        if len(waypoint_coords) < 2:
            return RouteResult(
                distance_km=0.0,
                duration_minutes=0.0,
                geometry_coords=waypoint_coords,
                error_message="At least 2 points are required for route calculation.",
            )

        # OSRM expects coordinates as lon,lat;lon,lat;...
        coord_strings = [f"{lon:.6f},{lat:.6f}" for lat, lon in waypoint_coords]
        coords_path = ";".join(coord_strings)
        url = f"{self.base_url}/route/v1/driving/{coords_path}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
        }

        try:
            resp = requests.get(
                url,
                params=params,
                headers={"User-Agent": "HFDeluxeProManager/1.0"},
                timeout=timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and "routes" in data and len(data["routes"]) > 0:
                    primary_route = data["routes"][0]
                    dist_km = round(primary_route["distance"] / 1000.0, 1)
                    dur_min = round(primary_route["duration"] / 60.0, 1)
                    
                    # Convert geojson [lon, lat] coordinates to (lat, lon) tuples
                    raw_coords = primary_route["geometry"]["coordinates"]
                    path_coords = [(float(pt[1]), float(pt[0])) for pt in raw_coords]

                    return RouteResult(
                        distance_km=dist_km,
                        duration_minutes=dur_min,
                        geometry_coords=path_coords,
                        is_estimate_fallback=False,
                    )
        except Exception as e:
            logger.warning("OSRM routing request failed: %s. Using Haversine approximation.", e)

        # Offline Haversine approximation fallback
        return self._calculate_haversine_fallback(waypoint_coords)

    def _calculate_haversine_fallback(
        self, waypoint_coords: List[Tuple[float, float]]
    ) -> RouteResult:
        """Calculates approximate road distance based on straight-line distances * winding factor."""
        total_dist = 0.0
        for i in range(len(waypoint_coords) - 1):
            p1 = waypoint_coords[i]
            p2 = waypoint_coords[i + 1]
            straight_dist = haversine_distance_km(p1[0], p1[1], p2[0], p2[1])
            # Road winding factor: approx 1.25x - 1.3x straight-line distance
            total_dist += straight_dist * 1.28

        total_dist = round(total_dist, 1)
        # Average motorcycle touring speed in India: approx 45-50 km/h
        est_duration = round((total_dist / 48.0) * 60.0, 1)

        return RouteResult(
            distance_km=total_dist,
            duration_minutes=est_duration,
            geometry_coords=waypoint_coords,
            is_estimate_fallback=True,
            error_message="Offline mode: Distance estimated via Haversine road model.",
        )

    def calculate_route_async(
        self,
        waypoint_coords: List[Tuple[float, float]],
        callback: Callable[[RouteResult], None],
        timeout: float = 10.0,
    ):
        """Asynchronously calculates route in background thread without freezing Tkinter."""
        def worker():
            res = self.calculate_route(waypoint_coords, timeout=timeout)
            callback(res)

        t = threading.Thread(target=worker, daemon=True)
        t.start()


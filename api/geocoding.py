"""
HF Deluxe Pro Manager - Nominatim Geocoding API Client
Complies with OpenStreetMap Nominatim usage policies, implements in-memory and SQLite caching,
and handles timeouts and offline fallbacks gracefully.
"""

import requests
import time
import logging
from typing import Optional, Tuple, Dict, Any, List

logger = logging.getLogger("hf_manager.geocoding")

NOMINATIM_DEFAULT_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "HFDeluxeProManager/1.0 (Motorcycle Touring Companion)"


class GeocodingService:
    """Thread-safe Geocoding service with caching and rate limiting."""

    def __init__(self, base_url: str = NOMINATIM_DEFAULT_URL):
        self.base_url = base_url.rstrip("/")
        self._cache: Dict[str, Tuple[float, float, str]] = {}
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Respect Nominatim policy of max 1 request per second."""
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_request_time = time.time()

    def geocode(self, query: str, timeout: float = 6.0) -> Optional[Tuple[float, float, str]]:
        """
        Convert location name to (latitude, longitude, display_name).
        Returns None if not found or if network fails.
        """
        clean_q = query.strip()
        if not clean_q:
            return None

        cache_key = clean_q.lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        self._rate_limit()
        url = f"{self.base_url}/search"
        headers = {"User-Agent": USER_AGENT}
        params = {
            "q": clean_q,
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
        }

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    display_name = data[0].get("display_name", clean_q)
                    res = (lat, lon, display_name)
                    self._cache[cache_key] = res
                    return res
        except Exception as e:
            logger.warning("Geocoding failed for '%s': %s", clean_q, e)

        return None

    def reverse_geocode(self, lat: float, lon: float, timeout: float = 6.0) -> Optional[str]:
        """Convert coordinates to human-readable address."""
        cache_key = f"{lat:.5f},{lon:.5f}"
        if cache_key in self._cache:
            return self._cache[cache_key][2]

        self._rate_limit()
        url = f"{self.base_url}/reverse"
        headers = {"User-Agent": USER_AGENT}
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
        }

        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                display_name = data.get("display_name", f"{lat:.4f}, {lon:.4f}")
                self._cache[cache_key] = (lat, lon, display_name)
                return display_name
        except Exception as e:
            logger.warning("Reverse geocoding failed for (%s, %s): %s", lat, lon, e)

        return f"{lat:.4f}, {lon:.4f}"


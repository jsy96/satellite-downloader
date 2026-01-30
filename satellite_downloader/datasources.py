"""
Data source abstraction for satellite imagery providers.

Supports multiple satellite imagery data sources including Google Satellite
and Sentinel-2 via Microsoft Planetary Computer.
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests


class DataSource(ABC):
    """
    Abstract base class for satellite imagery data sources.

    All data sources must implement the methods defined in this class.
    """

    def __init__(self):
        self.session = requests.Session()

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this data source."""
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return a description of this data source."""
        pass

    @abstractmethod
    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        """
        Build tile URL for given coordinates.

        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            zoom: Zoom level

        Returns:
            URL to fetch the tile
        """
        pass

    @abstractmethod
    def get_supported_zoom_levels(self) -> range:
        """Return range of supported zoom levels."""
        pass

    @abstractmethod
    def get_projection(self) -> str:
        """Return the projection/CRS used by this data source."""
        pass

    @abstractmethod
    def get_max_cc(self) -> float:
        """Return maximum cloud cover percentage (0-100)."""
        pass

    @abstractmethod
    def requires_auth(self) -> bool:
        """Return True if this data source requires authentication."""
        pass

    def get_auth_headers(self) -> Dict[str, str]:
        """Return authentication headers if required."""
        return {}

    def get_tile_size(self) -> int:
        """Return tile size in pixels (default 256)."""
        return 256


class GoogleDataSource(DataSource):
    """
    Google Satellite imagery data source.

    Uses Google's XYZ tile service with global coverage.
    """

    TILE_URL = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT
        })

    def get_name(self) -> str:
        return "google"

    def get_description(self) -> str:
        return "Google Satellite imagery (global coverage, RGB)"

    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        return self.TILE_URL.format(x=x, y=y, z=zoom)

    def get_supported_zoom_levels(self) -> range:
        return range(0, 21)  # Google supports up to zoom 20

    def get_projection(self) -> str:
        return "EPSG:3857"

    def get_max_cc(self) -> float:
        return 0  # Google imagery is pre-processed

    def requires_auth(self) -> bool:
        return False


class Sentinel2DataSource(DataSource):
    """
    Sentinel-2 imagery data source via Microsoft Planetary Computer.

    Sentinel-2 is a European Space Agency mission providing global coverage
    with 13 spectral bands and 10-60m resolution.

    This data source uses the Microsoft Planetary Computer's STAC API
    which provides free access to Sentinel-2 L2A data.
    """

    BASE_URL = "https://planetarycomputer.microsoft.com/api/data/v1"
    COLLECTION = "sentinel-2-l2a"
    TILE_URL_TEMPLATE = "{base_url}/tilejson/{collection}/{z}/{x}/{y}.tilejson.json"

    def __init__(self, max_cloud_cover: float = 20.0):
        """
        Initialize Sentinel-2 data source.

        Args:
            max_cloud_cover: Maximum cloud cover percentage (0-100)
        """
        super().__init__()
        self.max_cloud_cover = max_cloud_cover
        self._use_xyz_service = True  # Use XYZ tile service for simplicity

    def get_name(self) -> str:
        return "sentinel2"

    def get_description(self) -> str:
        return f"Sentinel-2 MSI (ESA, max cloud cover: {self.max_cloud_cover}%)"

    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        """
        Get tile URL for Sentinel-2 imagery.

        Uses the Planetary Computer XYZ tile service which automatically
        selects the most recent, least cloudy image for each tile.
        """
        # Use Planetary Computer's XYZ tile service
        # This service returns a rendered RGB image from Sentinel-2 data
        return (
            f"https://tiles.planetarycomputer.microsoft.com/"
            f"data/sentinel-2-l2a/{zoom}/{x}/{y}?asset=cog_visual"
        )

    def get_supported_zoom_levels(self) -> range:
        # Sentinel-2 L2A supports zoom levels 0-14
        # Zoom 14 ≈ 10m resolution (native resolution)
        return range(0, 15)

    def get_projection(self) -> str:
        return "EPSG:3857"

    def get_max_cc(self) -> float:
        return self.max_cloud_cover

    def requires_auth(self) -> bool:
        return False  # Planetary Computer XYZ service is free

    def search_scenes(self, bbox: Tuple[float, float, float, float],
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     limit: int = 10) -> List[Dict]:
        """
        Search for available Sentinel-2 scenes using STAC API.

        Args:
            bbox: Bounding box (min_lon, min_lat, max_lon, max_lat)
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)
            limit: Maximum number of results

        Returns:
            List of scene metadata
        """
        min_lon, min_lat, max_lon, max_lat = bbox

        # Build STAC search query
        search_url = f"{self.BASE_URL}/stac/search"
        params = {
            "collections": [self.COLLECTION],
            "bbox": [min_lon, min_lat, max_lon, max_lat],
            "limit": limit,
            "query": {
                "eo:cloud_cover": {
                    "lt": self.max_cloud_cover
                }
            }
        }

        # Add date range if specified
        if start_date or end_date:
            date_range = f"{start_date or '..'}/{end_date or '..'}"
            params["time"] = date_range

        try:
            response = self.session.post(search_url, json=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            scenes = []
            for feature in data.get("features", []):
                scenes.append({
                    "id": feature["id"],
                    "datetime": feature["properties"].get("datetime"),
                    "cloud_cover": feature["properties"].get("eo:cloud_cover", 0),
                    "geometry": feature.get("geometry"),
                    "assets": feature.get("assets", {})
                })

            return scenes
        except requests.RequestException as e:
            print(f"Warning: STAC search failed: {e}")
            return []


class DataSourceFactory:
    """
    Factory class for creating data source instances.
    """

    _sources: Dict[str, DataSource] = {}

    @classmethod
    def register_source(cls, source: DataSource):
        """Register a data source."""
        cls._sources[source.get_name()] = source

    @classmethod
    def get_source(cls, name: str, **kwargs) -> DataSource:
        """
        Get a data source by name.

        Args:
            name: Data source name ('google' or 'sentinel2')
            **kwargs: Additional arguments for the data source

        Returns:
            DataSource instance

        Raises:
            ValueError: If data source is not found
        """
        source_map = {
            "google": GoogleDataSource,
            "sentinel2": Sentinel2DataSource,
            "sentinel-2": Sentinel2DataSource,
            "s2": Sentinel2DataSource,
        }

        source_class = source_map.get(name.lower())
        if not source_class:
            available = list(source_map.keys())
            raise ValueError(
                f"Unknown data source: {name}. "
                f"Available sources: {', '.join(available)}"
            )

        return source_class(**kwargs)

    @classmethod
    def list_sources(cls) -> List[Dict[str, str]]:
        """
        List all available data sources.

        Returns:
            List of data source info dictionaries
        """
        sources = [
            GoogleDataSource(),
            Sentinel2DataSource()
        ]

        return [
            {
                "name": s.get_name(),
                "description": s.get_description(),
                "projection": s.get_projection(),
                "zoom_levels": f"{s.get_supported_zoom_levels().start}-{s.get_supported_zoom_levels().stop - 1}",
                "requires_auth": s.requires_auth()
            }
            for s in sources
        ]

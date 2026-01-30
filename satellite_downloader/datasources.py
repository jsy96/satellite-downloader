"""
Data source abstraction for satellite imagery providers.

Supports multiple free satellite imagery and map data sources:
- Sentinel-2 (ESA, via NASA GIBS)
- Landsat 8/9 (NASA/USGS, via NASA GIBS)
- MODIS Terra (NASA, via NASA GIBS)
- Esri World Imagery (multi-source mosaic)
- OpenStreetMap (rendered map tiles)
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


class Sentinel2DataSource(DataSource):
    """
    Sentinel-2 imagery data source via NASA GIBS.

    Sentinel-2 is a European Space Agency mission providing global coverage
    with 13 spectral bands and 10-60m resolution.

    This data source uses NASA GIBS (Global Imagery Browse Services)
    which provides free access to Sentinel-2 imagery via WMTS.

    Layer: COPERNICUS_S2_RADIOMETRY (Sentinel-2 Radiometry)
    """

    # NASA GIBS WMTS endpoint
    GIBS_URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/COPERNICUS_S2_RADIOMETRY/default/{time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png"

    def __init__(self, max_cloud_cover: float = 20.0):
        """
        Initialize Sentinel-2 data source.

        Args:
            max_cloud_cover: Maximum cloud cover percentage (0-100)
            Note: NASA GIBS provides pre-computed best available imagery
        """
        super().__init__()
        self.max_cloud_cover = max_cloud_cover
        # Use current date for "latest" imagery
        from datetime import datetime
        self.time = datetime.utcnow().strftime("%Y-%m-%d")

    def get_name(self) -> str:
        return "sentinel2"

    def get_description(self) -> str:
        return f"Sentinel-2 MSI via NASA GIBS (ESA, latest imagery)"

    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        """
        Get tile URL for Sentinel-2 imagery from NASA GIBS.

        GIBS WMTS format uses: TileCol=x, TileRow=y (flipped y)
        """
        # Flip Y for WMTS (TMS vs WMTS coordinate difference)
        max_y = 2 ** zoom - 1
        flipped_y = max_y - y

        return self.GIBS_URL.format(
            time=self.time,
            TileMatrixSet="GoogleMapsCompatible",
            TileMatrix=zoom,
            TileRow=flipped_y,
            TileCol=x
        )

    def get_supported_zoom_levels(self) -> range:
        # NASA GIBS supports zoom levels 0-13 for Sentinel-2
        # Zoom 13 ≈ 12m resolution
        return range(0, 14)

    def get_projection(self) -> str:
        return "EPSG:3857"

    def get_max_cc(self) -> float:
        return self.max_cloud_cover

    def requires_auth(self) -> bool:
        return False  # NASA GIBS is free


class LandsatDataSource(DataSource):
    """
    Landsat 8/9 imagery data source via NASA GIBS.

    Landsat is a joint NASA/USGS program providing the longest continuous
    space-based record of Earth's land in existence.

    This data source uses NASA GIBS (Global Imagery Browse Services)
    which provides free access to Landsat imagery via WMTS.

    Layer: LC09_L1TP (Landsat 9) - falls back to LC08_L1TP (Landsat 8)
    """

    # NASA GIBS WMTS endpoint for Landsat 9
    GIBS_URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/LC09_L1TP/default/{time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png"

    def __init__(self, max_cloud_cover: float = 40.0):
        """
        Initialize Landsat data source.

        Args:
            max_cloud_cover: Maximum cloud cover percentage (0-100)
            Note: NASA GIBS provides pre-computed best available imagery
        """
        super().__init__()
        self.max_cloud_cover = max_cloud_cover
        # Use current date for "latest" imagery
        self.time = datetime.utcnow().strftime("%Y-%m-%d")

    def get_name(self) -> str:
        return "landsat"

    def get_description(self) -> str:
        return f"Landsat 8/9 via NASA GIBS (NASA/USGS, 30m resolution)"

    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        """
        Get tile URL for Landsat imagery from NASA GIBS.

        GIBS WMTS format uses: TileCol=x, TileRow=y (flipped y)
        """
        # Flip Y for WMTS (TMS vs WMTS coordinate difference)
        max_y = 2 ** zoom - 1
        flipped_y = max_y - y

        return self.GIBS_URL.format(
            time=self.time,
            TileMatrixSet="GoogleMapsCompatible",
            TileMatrix=zoom,
            TileRow=flipped_y,
            TileCol=x
        )

    def get_supported_zoom_levels(self) -> range:
        # NASA GIBS supports zoom levels 0-12 for Landsat
        # Zoom 12 ≈ 30m resolution (native Landsat resolution)
        return range(0, 13)

    def get_projection(self) -> str:
        return "EPSG:3857"

    def get_max_cc(self) -> float:
        return self.max_cloud_cover

    def requires_auth(self) -> bool:
        return False  # NASA GIBS is free


class MODISDataSource(DataSource):
    """
    MODIS imagery data source via NASA GIBS.

    MODIS (Moderate Resolution Imaging Spectroradiometer) is a key instrument
    aboard the Terra (EOS AM) and Aqua (EOS PM) satellites.

    This data source uses NASA GIBS (Global Imagery Browse Services)
    which provides free access to MODIS imagery via WMTS.

    Layer: MODIS_Terra_TrueColor - Daily global imagery
    """

    # NASA GIBS WMTS endpoint for MODIS Terra
    GIBS_URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_TrueColor/default/{time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.png"

    def __init__(self, max_cloud_cover: float = 50.0):
        """
        Initialize MODIS data source.

        Args:
            max_cloud_cover: Maximum cloud cover percentage (0-100)
            Note: MODIS daily imagery has higher cloud tolerance
        """
        super().__init__()
        self.max_cloud_cover = max_cloud_cover
        # Use current date for "latest" imagery
        self.time = datetime.utcnow().strftime("%Y-%m-%d")

    def get_name(self) -> str:
        return "modis"

    def get_description(self) -> str:
        return f"MODIS Terra via NASA GIBS (NASA, 250m resolution, daily)"

    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        """
        Get tile URL for MODIS imagery from NASA GIBS.

        GIBS WMTS format uses: TileCol=x, TileRow=y (flipped y)
        """
        # Flip Y for WMTS (TMS vs WMTS coordinate difference)
        max_y = 2 ** zoom - 1
        flipped_y = max_y - y

        return self.GIBS_URL.format(
            time=self.time,
            TileMatrixSet="GoogleMapsCompatible",
            TileMatrix=zoom,
            TileRow=flipped_y,
            TileCol=x
        )

    def get_supported_zoom_levels(self) -> range:
        # NASA GIBS supports zoom levels 0-9 for MODIS
        # Zoom 9 ≈ 250m resolution (native MODIS resolution)
        return range(0, 10)

    def get_projection(self) -> str:
        return "EPSG:3857"

    def get_max_cc(self) -> float:
        return self.max_cloud_cover

    def requires_auth(self) -> bool:
        return False  # NASA GIBS is free


class EsriDataSource(DataSource):
    """
    Esri World Imagery data source.

    Esri World Imagery provides high-quality satellite and aerial imagery
    from multiple providers, compiled into a seamless global map.

    This is a free service provided by Esri for non-commercial use.
    """

    # Esri World Imagery tile server
    TILE_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT
        })

    def get_name(self) -> str:
        return "esri"

    def get_description(self) -> str:
        return "Esri World Imagery (multi-source, high resolution)"

    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        # Esri uses standard XYZ tile format (no Y flip needed)
        return self.TILE_URL.format(x=x, y=y, z=zoom)

    def get_supported_zoom_levels(self) -> range:
        return range(0, 18)  # Esri supports up to zoom 17

    def get_projection(self) -> str:
        return "EPSG:3857"

    def get_max_cc(self) -> float:
        return 0  # Esri imagery is pre-processed mosaics

    def requires_auth(self) -> bool:
        return False


class OSMDataSource(DataSource):
    """
    OpenStreetMap data source.

    OSM provides free map tiles rendered from OpenStreetMap data.
    Note: This is not satellite imagery but rendered map tiles.
    """

    # OpenStreetMap tile server
    TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT
        })

    def get_name(self) -> str:
        return "osm"

    def get_description(self) -> str:
        return "OpenStreetMap (rendered map tiles, not imagery)"

    def get_tile_url(self, x: int, y: int, zoom: int) -> str:
        # OSM uses standard XYZ tile format (no Y flip needed)
        return self.TILE_URL.format(x=x, y=y, z=zoom)

    def get_supported_zoom_levels(self) -> range:
        return range(0, 20)  # OSM supports up to zoom 19

    def get_projection(self) -> str:
        return "EPSG:3857"

    def get_max_cc(self) -> float:
        return 0  # Not applicable for rendered maps

    def requires_auth(self) -> bool:
        return False


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
            name: Data source name
            **kwargs: Additional arguments for the data source

        Returns:
            DataSource instance

        Raises:
            ValueError: If data source is not found
        """
        source_map = {
            "sentinel2": Sentinel2DataSource,
            "sentinel-2": Sentinel2DataSource,
            "s2": Sentinel2DataSource,
            "sentinel": Sentinel2DataSource,
            "landsat": LandsatDataSource,
            "l8": LandsatDataSource,
            "l9": LandsatDataSource,
            "lc08": LandsatDataSource,
            "lc09": LandsatDataSource,
            "modis": MODISDataSource,
            "terra": MODISDataSource,
            "esri": EsriDataSource,
            "worldimagery": EsriDataSource,
            "osm": OSMDataSource,
            "openstreetmap": OSMDataSource,
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
            Sentinel2DataSource(),
            LandsatDataSource(),
            MODISDataSource(),
            EsriDataSource(),
            OSMDataSource()
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

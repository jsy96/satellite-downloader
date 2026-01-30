"""
Tile downloader with caching and retry support.

Downloads satellite imagery tiles from Google XYZ tile service
with support for concurrent downloads and caching.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from typing import Dict, List, Tuple, Optional, Callable

import requests
from PIL import Image

from .cache import CacheManager
from .tiles import get_tiles_in_bbox


class TileDownloader:
    """
    Downloads satellite imagery tiles from Google XYZ tile service.

    Features:
    - Concurrent downloads with thread pool
    - Automatic retry on failure
    - Caching support for resume capability
    - Progress tracking
    """

    # Google satellite tile URL template
    TILE_URL = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"

    # User agent to avoid blocking
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def __init__(self, cache_manager: Optional[CacheManager] = None,
                 max_workers: int = 8, retry_count: int = 3,
                 request_delay: float = 0.1):
        """
        Initialize tile downloader.

        Args:
            cache_manager: Cache manager for storing tiles (None for no caching)
            max_workers: Maximum number of concurrent download threads
            retry_count: Number of retries for failed downloads
            request_delay: Delay between requests in seconds
        """
        self.cache = cache_manager or CacheManager()
        self.max_workers = max_workers
        self.retry_count = retry_count
        self.request_delay = request_delay

        # Configure session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.USER_AGENT
        })

    def _build_tile_url(self, x: int, y: int, zoom: int) -> str:
        """Build tile URL for given coordinates."""
        return self.TILE_URL.format(x=x, y=y, z=zoom)

    def _download_tile_data(self, x: int, y: int, zoom: int) -> Optional[bytes]:
        """
        Download a single tile with retry logic.

        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            zoom: Zoom level

        Returns:
            Tile data as bytes, or None if download failed
        """
        url = self._build_tile_url(x, y, zoom)

        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()

                # Verify we got an image
                content_type = response.headers.get('Content-Type', '')
                if 'image' not in content_type.lower():
                    print(f"Warning: Unexpected content type for tile ({zoom}, {x}, {y}): {content_type}")

                return response.content

            except requests.RequestException as e:
                if attempt == self.retry_count - 1:
                    print(f"Failed to download tile ({zoom}, {x}, {y}) after {self.retry_count} attempts: {e}")
                    return None
                time.sleep(1 * (attempt + 1))  # Exponential backoff

        return None

    def get_tile(self, x: int, y: int, zoom: int,
                 use_cache: bool = True) -> Optional[Image.Image]:
        """
        Get a tile, using cache if available.

        Args:
            x: Tile X coordinate
            y: Tile Y coordinate
            zoom: Zoom level
            use_cache: Whether to use cached tiles

        Returns:
            PIL Image of the tile, or None if download failed
        """
        # Check cache first
        if use_cache and self.cache.has_tile(zoom, x, y):
            cached_data = self.cache.get_tile(zoom, x, y)
            if cached_data:
                try:
                    return Image.open(BytesIO(cached_data))
                except Exception as e:
                    print(f"Warning: Could not load cached tile ({zoom}, {x}, {y}): {e}")

        # Download tile
        data = self._download_tile_data(x, y, zoom)
        if data is None:
            return None

        # Cache the downloaded data
        try:
            img = Image.open(BytesIO(data))
            if use_cache:
                self.cache.put_tile(zoom, x, y, data)
            return img
        except Exception as e:
            print(f"Warning: Could not open tile image ({zoom}, {x}, {y}): {e}")
            return None

    def download_area(self, min_lon: float, min_lat: float,
                      max_lon: float, max_lat: float,
                      zoom: int,
                      progress_callback: Optional[Callable[[int, int], None]] = None,
                      use_cache: bool = True) -> List[Tuple[Image.Image, int, int]]:
        """
        Download all tiles for a bounding box.

        Args:
            min_lon: Minimum longitude
            min_lat: Minimum latitude
            max_lon: Maximum longitude
            max_lat: Maximum latitude
            zoom: Zoom level
            progress_callback: Optional callback function (completed, total)
            use_cache: Whether to use cached tiles

        Returns:
            List of (image, x, y) tuples for successfully downloaded tiles
        """
        tiles, (x_min, y_min, x_max, y_max) = get_tiles_in_bbox(
            min_lon, min_lat, max_lon, max_lat, zoom
        )

        total_tiles = len(tiles)
        results = []
        failed = []

        def download_single(tile_coords: Tuple[int, int]) -> Optional[Tuple[Image.Image, int, int]]:
            x, y = tile_coords
            img = self.get_tile(x, y, zoom, use_cache=use_cache)
            if img:
                return (img, x, y)
            return None

        # Download concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(download_single, tile): tile for tile in tiles}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                else:
                    failed.append(futures[future])

                # Update progress
                completed = len(results)
                if progress_callback:
                    progress_callback(completed, total_tiles)

                # Small delay to avoid rate limiting
                time.sleep(self.request_delay)

        # Report failures
        if failed:
            print(f"Warning: {len(failed)} tiles failed to download")

        return results

    def get_tile_info(self, min_lon: float, min_lat: float,
                      max_lon: float, max_lat: float,
                      zoom: int) -> Dict:
        """
        Get information about tiles needed for a bounding box.

        Args:
            min_lon: Minimum longitude
            min_lat: Minimum latitude
            max_lon: Maximum longitude
            max_lat: Maximum latitude
            zoom: Zoom level

        Returns:
            Dictionary with tile information
        """
        tiles, (x_min, y_min, x_max, y_max) = get_tiles_in_bbox(
            min_lon, min_lat, max_lon, max_lat, zoom
        )

        # Count cached and pending tiles
        cached_count = 0
        pending_count = 0

        for x, y in tiles:
            if self.cache.has_tile(zoom, x, y):
                cached_count += 1
            else:
                pending_count += 1

        return {
            'zoom': zoom,
            'x_min': x_min,
            'x_max': x_max,
            'y_min': y_min,
            'y_max': y_max,
            'tile_count': len(tiles),
            'cached_count': cached_count,
            'pending_count': pending_count,
            'estimated_size_mb': round(len(tiles) * 50 / 1024, 2)  # Approx 50KB per tile
        }

    def clear_cache(self):
        """Clear the tile cache."""
        self.cache.clear()

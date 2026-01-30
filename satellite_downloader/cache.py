"""
Cache management for tile downloads with resume capability.

Supports caching downloaded tiles to disk and tracking download progress
for resumable downloads.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .tiles import lonlat_to_tile


class CacheManager:
    """
    Manages tile cache for resumable downloads.

    Stores downloaded tiles on disk with an index file for tracking.
    Allows resuming interrupted downloads by skipping already cached tiles.
    """

    def __init__(self, cache_dir: str = ".tile_cache"):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory to store cached tiles
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_index(self):
        """Save cache index to disk."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache index: {e}")

    def _get_tile_key(self, zoom: int, x: int, y: int) -> str:
        """Get cache key for a tile."""
        return f"{zoom}_{x}_{y}"

    def _get_tile_path(self, zoom: int, x: int, y: int) -> Path:
        """Get file path for a cached tile."""
        # Organize tiles in subdirectories by zoom level
        zoom_dir = self.cache_dir / str(zoom)
        zoom_dir.mkdir(exist_ok=True)
        return zoom_dir / f"{x}_{y}.png"

    def get_tile(self, zoom: int, x: int, y: int) -> Optional[bytes]:
        """
        Get cached tile data.

        Args:
            zoom: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate

        Returns:
            Tile data as bytes, or None if not cached
        """
        key = self._get_tile_key(zoom, x, y)
        if key not in self.index:
            return None

        path = self._get_tile_path(zoom, x, y)
        if not path.exists():
            # Remove from index if file doesn't exist
            del self.index[key]
            return None

        try:
            with open(path, 'rb') as f:
                return f.read()
        except IOError:
            return None

    def put_tile(self, zoom: int, x: int, y: int, data: bytes) -> bool:
        """
        Store a tile in cache.

        Args:
            zoom: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate
            data: Tile image data as bytes

        Returns:
            True if successfully cached, False otherwise
        """
        key = self._get_tile_key(zoom, x, y)
        path = self._get_tile_path(zoom, x, y)

        try:
            with open(path, 'wb') as f:
                f.write(data)

            self.index[key] = {
                'timestamp': datetime.now().isoformat(),
                'size': len(data),
                'x': x,
                'y': y,
                'zoom': zoom
            }
            self.save_index()
            return True
        except IOError as e:
            print(f"Warning: Could not cache tile {key}: {e}")
            return False

    def has_tile(self, zoom: int, x: int, y: int) -> bool:
        """
        Check if a tile is cached.

        Args:
            zoom: Zoom level
            x: Tile X coordinate
            y: Tile Y coordinate

        Returns:
            True if tile is cached and valid
        """
        key = self._get_tile_key(zoom, x, y)
        if key not in self.index:
            return False

        path = self._get_tile_path(zoom, x, y)
        return path.exists()

    def get_cached_tiles(self, min_lon: float, min_lat: float,
                         max_lon: float, max_lat: float,
                         zoom: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Get cached and pending tiles for a bounding box.

        Args:
            min_lon: Minimum longitude
            min_lat: Minimum latitude
            max_lon: Maximum longitude
            max_lat: Maximum latitude
            zoom: Zoom level

        Returns:
            Tuple of (cached_tiles, pending_tiles) where each is a list of (x, y) coordinates
        """
        from .tiles import get_tiles_in_bbox

        all_tiles, _ = get_tiles_in_bbox(min_lon, min_lat, max_lon, max_lat, zoom)

        cached = []
        pending = []

        for x, y in all_tiles:
            if self.has_tile(zoom, x, y):
                cached.append((x, y))
            else:
                pending.append((x, y))

        return cached, pending

    def clear(self):
        """Clear all cached tiles and index."""
        try:
            # Remove all tile files
            for zoom_dir in self.cache_dir.iterdir():
                if zoom_dir.is_dir() and zoom_dir.name.isdigit():
                    for tile_file in zoom_dir.glob("*.png"):
                        tile_file.unlink()
                    zoom_dir.rmdir()

            # Remove index
            if self.index_file.exists():
                self.index_file.unlink()

            self.index = {}
        except IOError as e:
            print(f"Warning: Could not clear cache: {e}")

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_size = sum(entry.get('size', 0) for entry in self.index.values())
        total_tiles = len(self.index)

        # Count tiles by zoom level
        zoom_counts = {}
        for entry in self.index.values():
            z = entry.get('zoom', 0)
            zoom_counts[z] = zoom_counts.get(z, 0) + 1

        return {
            'total_tiles': total_tiles,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'zoom_levels': sorted(zoom_counts.keys()),
            'tiles_by_zoom': zoom_counts,
            'cache_dir': str(self.cache_dir)
        }

    def cleanup_old_tiles(self, max_age_days: int = 30):
        """
        Remove tiles older than specified age.

        Args:
            max_age_days: Maximum age in days
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)
        keys_to_remove = []

        for key, entry in self.index.items():
            try:
                timestamp = datetime.fromisoformat(entry['timestamp'])
                if timestamp < cutoff:
                    # Remove file
                    zoom = entry['zoom']
                    x = entry['x']
                    y = entry['y']
                    path = self._get_tile_path(zoom, x, y)
                    if path.exists():
                        path.unlink()
                    keys_to_remove.append(key)
            except (KeyError, ValueError, IOError):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.index[key]

        if keys_to_remove:
            self.save_index()
            print(f"Cleaned up {len(keys_to_remove)} old tiles")


class TileCacheEntry:
    """Represents a single cached tile entry."""

    def __init__(self, zoom: int, x: int, y: int, data: bytes, timestamp: str = None):
        self.zoom = zoom
        self.x = x
        self.y = y
        self.data = data
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'zoom': self.zoom,
            'x': self.x,
            'y': self.y,
            'size': len(self.data),
            'timestamp': self.timestamp
        }

"""
Utility functions for the satellite downloader.

Provides helper functions for validation, formatting, and logging.
"""

import sys
from typing import Tuple, Optional


def validate_bbox(min_lon: float, min_lat: float,
                  max_lon: float, max_lat: float) -> bool:
    """
    Validate bounding box coordinates.

    Args:
        min_lon: Minimum longitude
        min_lat: Minimum latitude
        max_lon: Maximum longitude
        max_lat: Maximum latitude

    Returns:
        True if valid, raises ValueError otherwise
    """
    if not -180 <= min_lon <= 180:
        raise ValueError(f"min_lon must be between -180 and 180, got {min_lon}")
    if not -180 <= max_lon <= 180:
        raise ValueError(f"max_lon must be between -180 and 180, got {max_lon}")
    if not -90 <= min_lat <= 90:
        raise ValueError(f"min_lat must be between -90 and 90, got {min_lat}")
    if not -90 <= max_lat <= 90:
        raise ValueError(f"max_lat must be between -90 and 90, got {max_lat}")
    if min_lon >= max_lon:
        raise ValueError(f"min_lon must be less than max_lon, got {min_lon} >= {max_lon}")
    if min_lat >= max_lat:
        raise ValueError(f"min_lat must be less than max_lat, got {min_lat} >= {max_lat}")

    return True


def validate_resolution(resolution: float) -> bool:
    """
    Validate resolution value.

    Args:
        resolution: Resolution in degrees

    Returns:
        True if valid, raises ValueError otherwise
    """
    if resolution <= 0:
        raise ValueError(f"Resolution must be positive, got {resolution}")
    if resolution < 0.00001:
        print(f"Warning: Very small resolution ({resolution}) may result in huge downloads")
    if resolution > 1:
        print(f"Warning: Large resolution ({resolution}) may result in very coarse images")

    return True


def validate_zoom(zoom: int) -> bool:
    """
    Validate zoom level.

    Args:
        zoom: Zoom level

    Returns:
        True if valid, raises ValueError otherwise
    """
    if not 0 <= zoom <= 25:
        raise ValueError(f"Zoom level must be between 0 and 25, got {zoom}")

    return True


def format_bytes(size_bytes: int) -> str:
    """
    Format byte size as human readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.23 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_bbox(min_lon: float, min_lat: float,
                max_lon: float, max_lat: float) -> str:
    """
    Format bounding box as string.

    Args:
        min_lon: Minimum longitude
        min_lat: Minimum latitude
        max_lon: Maximum longitude
        max_lat: Maximum latitude

    Returns:
        Formatted string
    """
    return f"[{min_lon:.4f}, {min_lat:.4f}, {max_lon:.4f}, {max_lat:.4f}]"


def parse_resolution(resolution_str: str) -> float:
    """
    Parse resolution string to float.

    Args:
        resolution_str: Resolution as string

    Returns:
        Resolution as float
    """
    try:
        return float(resolution_str)
    except ValueError:
        raise ValueError(f"Invalid resolution: {resolution_str}. Must be a number.")


def get_center_point(min_lon: float, min_lat: float,
                     max_lon: float, max_lat: float) -> Tuple[float, float]:
    """
    Get center point of bounding box.

    Args:
        min_lon: Minimum longitude
        min_lat: Minimum latitude
        max_lon: Maximum longitude
        max_lat: Maximum latitude

    Returns:
        Tuple of (center_lon, center_lat)
    """
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2
    return center_lon, center_lat


def estimate_download_size(tile_count: int) -> dict:
    """
    Estimate download size for a given number of tiles.

    Args:
        tile_count: Number of tiles to download

    Returns:
        Dictionary with size estimates
    """
    # Approximate sizes
    avg_tile_size_kb = 50
    total_kb = tile_count * avg_tile_size_kb
    total_mb = total_kb / 1024

    return {
        'tile_count': tile_count,
        'estimated_kb': total_kb,
        'estimated_mb': total_mb,
        'formatted': format_bytes(total_kb * 1024)
    }


class ProgressTracker:
    """
    Simple progress tracker for downloads.
    """

    def __init__(self, total: int, description: str = "Downloading"):
        """
        Initialize progress tracker.

        Args:
            total: Total items to process
            description: Description of task
        """
        self.total = total
        self.current = 0
        self.description = description
        self.last_percentage = -1

    def update(self, increment: int = 1):
        """
        Update progress.

        Args:
            increment: Amount to increment by
        """
        self.current += increment
        self._print_progress()

    def _print_progress(self):
        """Print current progress."""
        if self.total > 0:
            percentage = int(self.current * 100 / self.total)

            # Only print when percentage changes
            if percentage != self.last_percentage:
                bar_length = 40
                filled = int(bar_length * self.current / self.total)
                bar = '=' * filled + '-' * (bar_length - filled)

                print(f"\r{self.description}: [{bar}] {percentage}% ({self.current}/{self.total})", end='')
                if percentage == 100:
                    print()  # New line when complete

                self.last_percentage = percentage

    def complete(self):
        """Mark as complete."""
        self.current = self.total
        self._print_progress()


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user to confirm an action.

    Args:
        message: Confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    prompt = f"{message} ({'Y/n' if default else 'y/N'}): "

    while True:
        response = input(prompt).strip().lower()

        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False

        print("Please enter 'y' or 'n'")


def print_summary(info: dict):
    """
    Print download summary.

    Args:
        info: Dictionary with download information
    """
    print("\n" + "=" * 50)
    print("Download Summary")
    print("=" * 50)

    if 'bbox' in info:
        min_lon, min_lat, max_lon, max_lat = info['bbox']
        print(f"Area: {format_bbox(min_lon, min_lat, max_lon, max_lat)}")
        center_lon, center_lat = get_center_point(min_lon, min_lat, max_lon, max_lat)
        print(f"Center: [{center_lon:.4f}, {center_lat:.4f}]")

    if 'resolution' in info:
        print(f"Resolution: {info['resolution']:.6f} degrees")

    if 'zoom' in info:
        print(f"Zoom Level: {info['zoom']}")

    if 'tile_count' in info:
        size_info = estimate_download_size(info['tile_count'])
        print(f"Tiles: {info['tile_count']}")
        print(f"Estimated Size: {size_info['formatted']}")

    if 'output' in info:
        print(f"Output: {info['output']}")

    if 'bigtiff' in info:
        print(f"BigTIFF: {'Enabled' if info['bigtiff'] else 'Auto'}")

    print("=" * 50 + "\n")

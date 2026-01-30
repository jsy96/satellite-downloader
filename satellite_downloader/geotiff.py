"""
GeoTIFF generation utilities.

Creates GeoTIFF files from downloaded tiles with proper georeferencing
and supports BigTIFF format for large files.
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from typing import List, Tuple, Dict, Optional, Any

from .tiles import tile_to_mercator, tile_to_lonlat, TILE_SIZE


class GeoTIFFWriter:
    """
    Writes GeoTIFF files from downloaded tiles.

    Handles tile merging, georeferencing, and BigTIFF support.
    """

    def __init__(self, bigtiff: bool = False, compression: str = 'lzw'):
        """
        Initialize GeoTIFF writer.

        Args:
            bigtiff: Whether to use BigTIFF format
            compression: Compression method (lzw, deflate, jpeg, none)
        """
        self.bigtiff = bigtiff
        self.compression = compression

    def _determine_bigtiff(self, width: int, height: int, tile_count: int) -> str:
        """
        Determine if BigTIFF should be used based on image size.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            tile_count: Number of tiles

        Returns:
            'YES', 'NO', or 'IF_SAFER' for BIGTIFF parameter
        """
        if self.bigtiff:
            return 'YES'

        # Use BigTIFF for very large images
        estimated_size = width * height * 3  # RGB bytes
        if estimated_size > 4 * 1024 * 1024 * 1024:  # > 4GB
            return 'YES'
        if tile_count > 10000:
            return 'IF_SAFER'

        return 'IF_SAFER'

    def _merge_tiles(self, tiles: List[Tuple[Any, int, int]],
                     tile_info: Dict) -> np.ndarray:
        """
        Merge tiles into a single image array.

        Args:
            tiles: List of (PIL Image, x, y) tuples
            tile_info: Dictionary with x_min, y_min, x_max, y_max, zoom

        Returns:
            Merged image as numpy array (height, width, 3)
        """
        x_min = tile_info['x_min']
        y_min = tile_info['y_min']
        x_max = tile_info['x_max']
        y_max = tile_info['y_max']

        # Calculate output dimensions
        tiles_x = x_max - x_min + 1
        # Note: In tile coords, y_max <= y_min (Y increases downward from top)
        tiles_y = y_min - y_max + 1
        width = tiles_x * TILE_SIZE
        height = tiles_y * TILE_SIZE

        # Create canvas
        merged = np.zeros((height, width, 3), dtype=np.uint8)

        # Place tiles on canvas
        for img, x, y in tiles:
            # Convert PIL to numpy
            img_array = np.array(img)

            # Handle different image modes
            if len(img_array.shape) == 2:  # Grayscale
                img_array = np.stack([img_array] * 3, axis=2)
            elif img_array.shape[2] == 4:  # RGBA
                img_array = img_array[:, :, :3]  # Remove alpha

            # Calculate position
            px = (x - x_min) * TILE_SIZE
            # For Y: reference from y_max (top) since Y increases downward
            py = (y - y_max) * TILE_SIZE

            # Ensure image is 256x256
            if img_array.shape[:2] != (TILE_SIZE, TILE_SIZE):
                img_array = np.array(img.resize((TILE_SIZE, TILE_SIZE)))

            # Place on canvas
            try:
                merged[py:py+TILE_SIZE, px:px+TILE_SIZE] = img_array
            except ValueError as e:
                print(f"Warning: Could not place tile ({x}, {y}): {e}")

        return merged

    def _calculate_bounds(self, tile_info: Dict) -> Tuple[float, float, float, float]:
        """
        Calculate bounds for the tile area in Web Mercator (EPSG:3857) coordinates.

        Using Web Mercator ensures tiles are square (equal meters per pixel)
        and prevents image distortion when viewing in GIS software.

        Args:
            tile_info: Dictionary with tile coordinates

        Returns:
            Tuple of (left, bottom, right, top) in meters (Web Mercator)
        """
        x_min = tile_info['x_min']
        y_min = tile_info['y_min']
        x_max = tile_info['x_max']
        y_max = tile_info['y_max']
        zoom = tile_info['zoom']

        # Get bounds in Web Mercator coordinates (meters)
        # Note: In tile coords, y_max is top (smaller value), y_min is bottom (larger value)
        left, top = tile_to_mercator(x_min, y_max, zoom)
        right, bottom = tile_to_mercator(x_max + 1, y_min + 1, zoom)

        return left, bottom, right, top

    def create_geotiff(self, tiles: List[Tuple[Any, int, int]],
                       tile_info: Dict,
                       output_path: str) -> Dict:
        """
        Create a GeoTIFF file from downloaded tiles.

        Args:
            tiles: List of (PIL Image, x, y) tuples
            tile_info: Dictionary with x_min, y_min, x_max, y_max, zoom
            output_path: Output file path

        Returns:
            Dictionary with output file information
        """
        # Merge tiles
        print("Merging tiles...")
        merged = self._merge_tiles(tiles, tile_info)
        height, width = merged.shape[:2]

        # Calculate bounds
        left, bottom, right, top = self._calculate_bounds(tile_info)

        # Create affine transform
        transform = from_bounds(left, bottom, right, top, width, height)

        # Determine BigTIFF setting
        bigtiff_setting = self._determine_bigtiff(width, height, tile_info.get('tile_count', len(tiles)))

        # Create profile with explicit CRS
        # Use CRS.from_epsg to ensure full coordinate system definition
        crs_3857 = CRS.from_epsg(3857)

        profile = {
            'driver': 'GTiff',
            'height': height,
            'width': width,
            'count': 3,  # RGB
            'dtype': 'uint8',
            'crs': crs_3857,  # Use CRS object for complete definition
            'transform': transform,
            'BIGTIFF': bigtiff_setting,
            'compress': self.compression,
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256,
            'nodata': None,
        }

        # Write GeoTIFF
        print(f"Writing GeoTIFF to {output_path}...")
        with rasterio.open(output_path, 'w', **profile) as dst:
            # Explicitly set CRS to ensure it's written correctly
            dst.crs = crs_3857
            # Rasterio expects (bands, height, width)
            data = np.transpose(merged, [2, 0, 1])
            dst.write(data)

            # Add metadata
            dst.update_tags(
                source='Google Satellite Imagery',
                software='satellite-downloader',
                zoom=tile_info['zoom'],
                tile_count=len(tiles)
            )

        # Also calculate geographic bounds for display purposes
        x_min = tile_info['x_min']
        y_min = tile_info['y_min']
        x_max = tile_info['x_max']
        y_max = tile_info['y_max']
        zoom = tile_info['zoom']
        geo_left, geo_top = tile_to_lonlat(x_min, y_max, zoom)
        geo_right, geo_bottom = tile_to_lonlat(x_max + 1, y_min + 1, zoom)

        return {
            'path': output_path,
            'width': width,
            'height': height,
            'bands': 3,
            'dtype': 'uint8',
            'crs': 'EPSG:3857',  # Web Mercator
            'bounds': (left, bottom, right, top),
            'geo_bounds': (geo_left, geo_bottom, geo_right, geo_top),  # Geographic bounds in degrees
            'bigtiff': bigtiff_setting == 'YES',
            'compression': self.compression
        }

    def create_geotiff_tiled(self, tiles_generator,
                             tile_info: Dict,
                             output_path: str,
                             chunk_size: int = 100) -> Dict:
        """
        Create a GeoTIFF file from a tiles generator (for large areas).

        Processes tiles in chunks to avoid memory issues.

        Args:
            tiles_generator: Generator yielding (PIL Image, x, y) tuples
            tile_info: Dictionary with x_min, y_min, x_max, y_max, zoom
            output_path: Output file path
            chunk_size: Number of tiles to process per chunk

        Returns:
            Dictionary with output file information
        """
        x_min = tile_info['x_min']
        y_min = tile_info['y_min']
        x_max = tile_info['x_max']
        y_max = tile_info['y_max']

        # Calculate dimensions
        tiles_x = x_max - x_min + 1
        # Note: In tile coords, y_max <= y_min (Y increases downward from top)
        tiles_y = y_min - y_max + 1
        width = tiles_x * TILE_SIZE
        height = tiles_y * TILE_SIZE

        # Calculate bounds
        left, bottom, right, top = self._calculate_bounds(tile_info)
        transform = from_bounds(left, bottom, right, top, width, height)

        # Determine BigTIFF setting
        tile_count = tiles_x * tiles_y
        bigtiff_setting = self._determine_bigtiff(width, height, tile_count)

        # Create profile with explicit CRS
        crs_3857 = CRS.from_epsg(3857)

        profile = {
            'driver': 'GTiff',
            'height': height,
            'width': width,
            'count': 3,
            'dtype': 'uint8',
            'crs': crs_3857,  # Use CRS object for complete definition
            'transform': transform,
            'BIGTIFF': bigtiff_setting,
            'compress': self.compression,
            'tiled': True,
            'blockxsize': 256,
            'blockysize': 256
        }

        # Write in chunks
        print(f"Writing large GeoTIFF to {output_path}...")
        with rasterio.open(output_path, 'w', **profile) as dst:
            # Explicitly set CRS to ensure it's written correctly
            dst.crs = crs_3857
            chunk = []

            for item in tiles_generator:
                chunk.append(item)

                if len(chunk) >= chunk_size:
                    self._write_chunk(dst, chunk, x_min, y_max)
                    chunk = []

            # Write remaining tiles
            if chunk:
                self._write_chunk(dst, chunk, x_min, y_max)

            # Add metadata
            dst.update_tags(
                source='Google Satellite Imagery',
                software='satellite-downloader',
                zoom=tile_info['zoom'],
                tile_count=tile_count
            )

        # Also calculate geographic bounds for display purposes
        x_min = tile_info['x_min']
        y_min = tile_info['y_min']
        x_max = tile_info['x_max']
        y_max = tile_info['y_max']
        zoom = tile_info['zoom']
        geo_left, geo_top = tile_to_lonlat(x_min, y_max, zoom)
        geo_right, geo_bottom = tile_to_lonlat(x_max + 1, y_min + 1, zoom)

        return {
            'path': output_path,
            'width': width,
            'height': height,
            'bands': 3,
            'dtype': 'uint8',
            'crs': 'EPSG:3857',  # Web Mercator
            'bounds': (left, bottom, right, top),
            'geo_bounds': (geo_left, geo_bottom, geo_right, geo_top),  # Geographic bounds in degrees
            'bigtiff': bigtiff_setting == 'YES',
            'compression': self.compression
        }

    def _write_chunk(self, dst, chunk: List, x_min: int, y_max: int):
        """Write a chunk of tiles to the GeoTIFF."""
        for img, x, y in chunk:
            img_array = np.array(img)

            # Handle different image modes
            if len(img_array.shape) == 2:  # Grayscale
                img_array = np.stack([img_array] * 3, axis=2)
            elif img_array.shape[2] == 4:  # RGBA
                img_array = img_array[:, :, :3]

            # Calculate window position
            px = (x - x_min) * TILE_SIZE
            # For Y: reference from y_max (top) since Y increases downward
            py = (y - y_max) * TILE_SIZE

            # Define window
            window = rasterio.windows.Window(px, py, TILE_SIZE, TILE_SIZE)

            # Write window
            data = np.transpose(img_array, [2, 0, 1])
            dst.write(data, window=window)


def create_geotiff(tiles: List[Tuple[Any, int, int]],
                   tile_info: Dict,
                   output_path: str,
                   bigtiff: bool = False,
                   compression: str = 'lzw') -> Dict:
    """
    Convenience function to create a GeoTIFF from tiles.

    Args:
        tiles: List of (PIL Image, x, y) tuples
        tile_info: Dictionary with x_min, y_min, x_max, y_max, zoom
        output_path: Output file path
        bigtiff: Whether to use BigTIFF format
        compression: Compression method

    Returns:
        Dictionary with output file information
    """
    writer = GeoTIFFWriter(bigtiff=bigtiff, compression=compression)
    return writer.create_geotiff(tiles, tile_info, output_path)

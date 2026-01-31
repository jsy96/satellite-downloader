"""
Command line interface for satellite downloader.

Provides CLI for downloading satellite imagery and maps from multiple
free sources (Sentinel-2, Landsat, MODIS, Esri, OSM) and exporting as GeoTIFF.
"""

import sys
import traceback
from typing import Optional

import click

from .cache import CacheManager
from .datasources import DataSourceFactory
from .downloader import TileDownloader
from .geotiff import GeoTIFFWriter
from .tiles import (
    calculate_zoom, calculate_resolution_from_zoom, get_tiles_in_bbox,
    parse_bbox as parse_bbox_str, parse_extent as parse_extent_str
)
from .utils import (
    validate_bbox, validate_resolution, validate_zoom,
    print_summary, estimate_download_size, ProgressTracker
)


@click.command()
@click.option('--bbox', type=str, help='Bounding box: min_lon,min_lat,max_lon,max_lat')
@click.option('--extent', type=str, help='Extent string: "E{min}-E{max},N{min}-N{max}"')
@click.option('--resolution', type=float, help='Output resolution in degrees (e.g., 0.0001)')
@click.option('--zoom', type=int, help='Explicit zoom level (overrides resolution)')
@click.option('--output', '-o', type=str, required=True, help='Output GeoTIFF file path')
@click.option('--bigtiff', is_flag=True, help='Force BigTIFF format')
@click.option('--cache', type=str, default='.tile_cache', help='Cache directory for resume capability')
@click.option('--workers', type=int, default=4, help='Number of download workers (default: 4)')
@click.option('--compression', type=click.Choice(['lzw', 'deflate', 'jpeg', 'none']), default='lzw',
              help='Compression method (default: lzw)')
@click.option('--no-cache', is_flag=True, help='Disable caching')
@click.option('--clear-cache', is_flag=True, help='Clear cache before downloading')
@click.option('--source', type=str, default='esri',
              help='Data source: sentinel2/s2, landsat/l8, modis, esri (default: esri, recommended)')
@click.option('--cloud-cover', type=float, default=20.0,
              help='Maximum cloud cover percentage for S2/Landsat/MODIS (default: 20)')
@click.option('-v', '--verbose', count=True,
              help='Increase verbosity (can be used multiple times)')
@click.version_option(version='1.0.2')
def main(bbox: Optional[str], extent: Optional[str], resolution: Optional[float],
         zoom: Optional[int], output: str, bigtiff: bool, cache: str,
         workers: int, compression: str, no_cache: bool, clear_cache: bool,
         source: str, cloud_cover: float, verbose: int = 0):
    """
    Download satellite imagery and export as GeoTIFF.

    \b
    Examples:
        # Using bbox with Sentinel-2
        satellite-download --bbox 110,30,110.1,30.1 --resolution 0.0001 --output area.tif

        # Using Landsat data
        satellite-download --bbox 110,30,110.1,30.1 --source landsat --zoom 12 --output area.tif

        # Using MODIS (good for large areas)
        satellite-download --bbox 110,30,111,31 --source modis --zoom 9 --output large.tif

        # Using Esri World Imagery (high resolution)
        satellite-download --bbox 110,30,110.1,30.1 --source esri --zoom 17 --output detailed.tif

        # Large area with BigTIFF
        satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output large.tif --bigtiff
    """
    try:
        # Validate cloud cover parameter
        if not 0 <= cloud_cover <= 100:
            click.echo(f"Error: --cloud-cover must be between 0 and 100, got {cloud_cover}", err=True)
            sys.exit(1)

        # Create data source
        data_source = DataSourceFactory.get_source(
            source,
            max_cloud_cover=cloud_cover
        )

        # Parse bounding box
        if bbox:
            min_lon, min_lat, max_lon, max_lat = parse_bbox_str(bbox)
        elif extent:
            min_lon, min_lat, max_lon, max_lat = parse_extent_str(extent)
        else:
            click.echo("Error: Either --bbox or --extent must be specified", err=True)
            sys.exit(1)

        # Validate bounding box
        validate_bbox(min_lon, min_lat, max_lon, max_lat)

        # Determine zoom level
        if zoom is not None:
            validate_zoom(zoom)
        elif resolution is not None:
            validate_resolution(resolution)
            center_lat = (min_lat + max_lat) / 2
            zoom = calculate_zoom(resolution, center_lat)
        else:
            click.echo("Error: Either --resolution or --zoom must be specified", err=True)
            sys.exit(1)

        # Validate zoom level for the data source
        supported_zooms = data_source.get_supported_zoom_levels()
        if zoom not in supported_zooms:
            click.echo(
                f"Error: Zoom level {zoom} is not supported by {data_source.get_name()}. "
                f"Supported range: {supported_zooms.start}-{supported_zooms.stop - 1}",
                err=True
            )
            sys.exit(1)

        # Get tile information
        tiles, (x_min, y_min, x_max, y_max) = get_tiles_in_bbox(
            min_lon, min_lat, max_lon, max_lat, zoom
        )
        tile_count = len(tiles)

        # Calculate actual resolution from final zoom level
        center_lat = (min_lat + max_lat) / 2
        actual_resolution = calculate_resolution_from_zoom(zoom, center_lat)

        # Setup cache manager
        if no_cache:
            cache_manager = None
        else:
            cache_manager = CacheManager(cache_dir=cache)
            if clear_cache:
                click.echo(f"Clearing cache: {cache}")
                cache_manager.clear()

        # Setup downloader with data source
        downloader = TileDownloader(
            cache_manager=cache_manager,
            max_workers=workers,
            retry_count=3,
            request_delay=0.05,
            data_source=data_source
        )

        # Display data source info
        click.echo(f"Data source: {data_source.get_description()}")

        # Get tile info (including cached tiles)
        tile_info = downloader.get_tile_info(
            min_lon, min_lat, max_lon, max_lat, zoom
        )

        # Print summary
        summary = {
            'bbox': (min_lon, min_lat, max_lon, max_lat),
            'resolution': actual_resolution,  # Use actual resolution from zoom level
            'zoom': zoom,
            'tile_count': tile_count,
            'output': output,
            'bigtiff': bigtiff,
            'compression': compression
        }

        if cache_manager and not no_cache:
            summary['cached'] = tile_info['cached_count']
            summary['pending'] = tile_info['pending_count']
            if tile_info['cached_count'] > 0:
                click.echo(f"Found {tile_info['cached_count']} cached tiles, will download {tile_info['pending_count']} new tiles")

        print_summary(summary)

        # Confirm for large downloads
        if tile_count > 1000:
            size_info = estimate_download_size(tile_count)
            click.echo(f"Warning: This will download approximately {size_info['formatted']}")
            if not click.confirm("Continue?", default=False):
                click.echo("Download cancelled")
                sys.exit(0)

        # Download tiles
        progress = ProgressTracker(tile_count, "Downloading tiles")

        def progress_callback(completed: int, total: int):
            nonlocal progress
            progress.current = completed
            progress._print_progress()

        click.echo("Starting download...")
        downloaded_tiles = downloader.download_area(
            min_lon, min_lat, max_lon, max_lat, zoom,
            progress_callback=progress_callback,
            use_cache=not no_cache
        )

        if not downloaded_tiles:
            click.echo("Error: No tiles were successfully downloaded", err=True)
            sys.exit(1)

        click.echo(f"\nDownloaded {len(downloaded_tiles)} tiles")

        # Create GeoTIFF
        click.echo("Creating GeoTIFF...")

        tile_info_dict = {
            'x_min': x_min,
            'y_min': y_min,
            'x_max': x_max,
            'y_max': y_max,
            'zoom': zoom,
            'tile_count': tile_count
        }

        writer = GeoTIFFWriter(bigtiff=bigtiff, compression=compression)
        result = writer.create_geotiff(downloaded_tiles, tile_info_dict, output)

        # Print result
        click.echo("\n" + "=" * 50)
        click.echo("GeoTIFF created successfully!")
        click.echo("=" * 50)
        click.echo(f"File: {result['path']}")
        click.echo(f"Size: {result['width']} x {result['height']} pixels")
        # Display geographic bounds (degrees) for user convenience
        if 'geo_bounds' in result:
            geo_left, geo_bottom, geo_right, geo_top = result['geo_bounds']
            click.echo(f"Bounds (lat/lon): [{geo_left:.6f}, {geo_bottom:.6f}, "
                       f"{geo_right:.6f}, {geo_top:.6f}]")
        click.echo(f"CRS: {result['crs']} (Web Mercator)")
        if result['bigtiff']:
            click.echo("Format: BigTIFF")
        if result['compression']:
            click.echo(f"Compression: {result['compression']}")
        click.echo("=" * 50)

        # Cache stats
        if cache_manager and not no_cache:
            stats = cache_manager.get_stats()
            click.echo(f"\nCache stats: {stats['total_tiles']} tiles, {stats['total_size_mb']} MB")

    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        if verbose > 0:
            traceback.print_exc()
        sys.exit(1)


def run_cli():
    """Entry point for console script."""
    main()


if __name__ == '__main__':
    run_cli()

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from satellite_downloader import DataSourceFactory


def handler(event, context):
    """Vercel Python handler function."""
    try:
        factory = DataSourceFactory()
        sources = []

        descriptions = {
            "sentinel2": "ESA Sentinel-2 imagery (10m resolution, optical)",
            "landsat": "NASA Landsat 8/9 imagery (30m resolution, optical)",
            "modis": "NASA MODIS Terra imagery (250m resolution, daily)",
            "esri": "Esri World Imagery (1m resolution, multi-source)",
            "osm": "OpenStreetMap (vector rendering, not real imagery)"
        }

        resolutions = {
            "sentinel2": "~10m per pixel",
            "landsat": "~30m per pixel",
            "modis": "~250m per pixel",
            "esri": "~1m per pixel (variable)",
            "osm": "Vector rendering"
        }

        for source_id, source in factory.get_all_sources().items():
            min_zoom, max_zoom = source.get_supported_zoom_levels()
            sources.append({
                "id": source_id,
                "name": source_id.replace("_", " ").title(),
                "description": descriptions.get(source_id, "Satellite imagery data source"),
                "resolution": resolutions.get(source_id, "Variable resolution"),
                "zoom_levels": list(range(min_zoom, max_zoom + 1)),
                "requires_auth": source.requires_auth(),
                "max_cloud_cover": getattr(source, 'get_max_cc', lambda: 100)()
            })

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(sources)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

"""
Vercel Serverless Function: Get available data sources
"""
from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Add parent directory to path to import satellite_downloader
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from satellite_downloader import DataSourceFactory


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET request to get data sources."""
        try:
            # Set CORS headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

            # Get data sources
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

            self.wfile.write(json.dumps(sources).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        """Handle OPTIONS request for CORS."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

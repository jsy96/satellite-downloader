import json
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def handler(event, context):
    """Vercel Python handler function."""
    try:
        # Parse request body
        body = event.get('body', '{}')
        if isinstance(body, str):
            params = json.loads(body)
        else:
            params = body

        # Extract parameters
        bbox = params.get('bbox')
        extent = params.get('extent')
        source = params.get('source', 'sentinel2')
        zoom = params.get('zoom')
        resolution = params.get('resolution')
        cloud_cover = params.get('cloud_cover', 20)
        compression = params.get('compression', 'lzw')
        workers = params.get('workers', 8)

        # Validate
        if not bbox and not extent:
            raise ValueError("Either bbox or extent must be provided")

        # Parse bbox if provided
        if bbox:
            min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
        else:
            # Parse extent (simplified)
            parts = extent.split(',')
            e_part = parts[0].replace('E', '').replace('e', '')
            n_part = parts[1].replace('N', '').replace('n', '')
            e_min, e_max = map(float, e_part.split('-'))
            n_min, n_max = map(float, n_part.split('-'))
            min_lon, min_lat, max_lon, max_lat = e_min, n_min, e_max, n_max

        # Calculate area
        lon_diff = max_lon - min_lon
        lat_diff = max_lat - min_lat
        area_km2 = (lon_diff * 111) * (lat_diff * 111)

        # Generate task ID
        task_id = str(uuid.uuid4())[:8]

        # Build CLI command
        cmd_parts = [
            "satellite-download",
            "--bbox", f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "--source", source,
            "--output", f"area_{task_id}.tif"
        ]

        if zoom:
            cmd_parts.extend(["--zoom", str(zoom)])
        if resolution:
            cmd_parts.extend(["--resolution", str(resolution)])
        if cloud_cover != 20:
            cmd_parts.extend(["--cloud-cover", str(cloud_cover)])
        if compression != "lzw":
            cmd_parts.extend(["--compression", compression])
        if workers != 8:
            cmd_parts.extend(["--workers", str(workers)])

        command = " ".join(cmd_parts)

        response = {
            "task_id": task_id,
            "status": "queued",
            "command": command,
            "area_km2": round(area_km2, 2),
            "can_download_directly": area_km2 < 100,
            "message": f"Area size: {area_km2:.2f} km². " +
                      ("Download can be processed directly." if area_km2 < 100
                       else "Area too large for serverless processing. Please run the command locally."),
            "instructions": {
                "option1": "Copy and run the command above in your terminal",
                "option2": f"Or use Claude Code skill: 'Download satellite imagery for bbox {bbox} from {source}'"
            },
            "bbox": {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat
            },
            "parameters": {
                "source": source,
                "zoom": zoom,
                "resolution": resolution,
                "cloud_cover": cloud_cover,
                "compression": compression
            }
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response)
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

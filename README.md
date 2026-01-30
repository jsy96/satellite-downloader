# Satellite Downloader

AI Skill for downloading Google satellite imagery and exporting as GeoTIFF format.

## Features

- Download Google satellite imagery by bounding box and resolution
- Support for EPSG:4326 (WGS84) coordinate system
- Export to GeoTIFF format with BigTIFF support
- Resume capability with cache management
- Progress bar for download status

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

```bash
# Using bbox (min_lon, min_lat, max_lon, max_lat)
satellite-download --bbox 110,30,110.1,30.1 --resolution 0.0001 --output area.tif
```

### Using Extent String

```bash
# Format: "E{min_lon}-E{max_lon},N{min_lat}-N{max_lat}"
satellite-download --extent "E110-E110.1,N30-N30.1" --resolution 0.0001 --output area.tif
```

### BigTIFF Support

```bash
# Enable BigTIFF for large areas
satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output large.tif --bigtiff
```

### Custom Cache Directory

```bash
# Specify cache directory for resume capability
satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output area.tif --cache .cache
```

## Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--bbox` | Bounding box: min_lon,min_lat,max_lon,max_lat | `110,30,110.1,30.1` |
| `--extent` | Extent string: "E{min}-E{max},N{min}-N{max}" | `"E110-E110.1,N30-N30.1"` |
| `--resolution` | Output resolution in degrees | `0.0001` |
| `--output` | Output GeoTIFF file path | `area.tif` |
| `--bigtiff` | Enable BigTIFF format (flag) | - |
| `--cache` | Cache directory for resume capability | `.cache` |
| `--workers` | Number of download workers (default: 8) | `16` |
| `--zoom` | Explicit zoom level (overrides resolution) | `18` |

## Resolution and Zoom Level

| Resolution (degrees) | Zoom Level | Ground Resolution |
|---------------------|------------|-------------------|
| 0.1 | 14 | ~1.1 km |
| 0.01 | 16 | ~110 m |
| 0.001 | 18 | ~11 m |
| 0.0001 | 20 | ~1.1 m |

## Output Validation

```bash
# Check GeoTIFF info
gdalinfo output.tif

# View in QGIS
# Open QGIS → Layer → Add Layer → Add Raster Layer
```

## Cache Structure

```
.cache/
├── cache_index.json      # Cache index file
├── 18_123456_654321.png  # Cached tiles: {zoom}_{x}_{y}.png
└── ...
```

## Examples

### Small Area Test

```bash
# Download 0.01° × 0.01° area (about 1km × 1km)
satellite-download --bbox 110,30,110.01,30.01 --resolution 0.0001 --output test.tif
```

### Large Area with BigTIFF

```bash
# Download 1° × 1° area with BigTIFF
satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output large.tif --bigtiff --workers 16
```

### Resume Interrupted Download

```bash
# If download is interrupted, simply re-run the same command
# The tool will automatically use cached tiles
satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output area.tif --cache .cache
```

## Notes

1. **Google Terms of Service**: Please comply with Google Maps/Earth Terms of Service
2. **Rate Limiting**: The tool includes delays to avoid being blocked
3. **Large Areas**: For very large areas, consider downloading in smaller chunks
4. **Memory**: Large area downloads use chunked processing to avoid memory issues

## License

MIT License

## Sources

- [QGIS Plugins Repository](https://plugins.qgis.org/)
- [Google Earth Engine Python API](https://developers.google.com/earth-engine/tutorials/community/intro-to-python-api)
- [Google-Map-Downloader](https://github.com/zhengjie9510/google-map-downloader)
- [geemap](https://pypi.org/project/geemap/)

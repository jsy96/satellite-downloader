---
name: satellite-download
description: Download Google satellite imagery for any area and export as GeoTIFF format
model: sonnet
---

# Satellite Downloader

Download Google satellite imagery for specified geographic areas and export as GeoTIFF files with proper georeferencing.

## When to Use

Use this skill when users want to:
- Download satellite imagery for a specific location
- Create GeoTIFF files from Google Satellite imagery
- Get aerial/satellite photos for GIS work or mapping

Examples:
- "Download satellite imagery for Beijing from 116.3,39.8 to 116.5,40.0"
- "I need a high-resolution satellite image of Shanghai Pudong"
- "Get satellite data for coordinates 110,30 to 110.1,30.1"

## How It Works

### Web Mercator Tile System

Google Maps uses the Web Mercator projection with XYZ tile coordinates:
- **X axis**: Increases from west to east (0 to 2^zoom - 1)
- **Y axis**: Increases from north to south (0 to 2^zoom - 1)
- **Tile size**: 256x256 pixels

Each tile at zoom level Z covers an area of approximately:
```
ground_resolution = 40075016.68 / (256 * 2^Z) meters/pixel
```

### Coordinate Conversion

The tool converts between geographic coordinates (lat/lon) and tile coordinates:

**lat/lon → tile:**
```python
n = 2^zoom
x = int((lon + 180) / 360 * n)
y = int((1 - asinh(tan(lat_rad)) / π) / 2 * n)
```

**tile → lat/lon:**
```python
n = 2^zoom
lon = x / n * 360 - 180
lat = atan(sinh(π * (1 - 2*y / n)))
```

### Download Process

1. Calculate zoom level from requested resolution
2. Determine tile range for the bounding box
3. Download tiles concurrently (default 8 workers)
4. Merge tiles into a single image
5. Create GeoTIFF with proper georeferencing (EPSG:4326)

## Parameters

### Required

| Parameter | Format | Example |
|-----------|--------|---------|
| `--bbox` | min_lon,min_lat,max_lon,max_lat | `110,30,110.1,30.1` |
| `--extent` | E{min}-E{max},N{min}-N{max} | `E110-E110.1,N30-N30.1` |
| `--output` | file path | `area.tif` |

### Optional

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--resolution` | Resolution in degrees | auto |
| `--zoom` | Explicit zoom level (1-22) | auto |
| `--bigtiff` | Enable BigTIFF for large files | auto |
| `--compression` | lzw, deflate, jpeg, none | lzw |
| `--workers` | Concurrent downloads | 8 |
| `--cache` | Cache directory | .tile_cache |

## Zoom Level Guide

| Zoom | Resolution | Area Coverage | Detail Level | Use Case |
|------|-----------|---------------|--------------|----------|
| 10 | ~100m/pixel | ~2000km × 2000km | City overview | Large regions |
| 14 | ~10m/pixel | ~250km × 250km | Street level | Town districts |
| 18 | ~1m/pixel | ~15km × 15km | Building detail | Neighborhoods |
| 20 | ~0.3m/pixel | ~4km × 4km | Maximum | Small areas |

**Important**: Higher zoom = exponentially more tiles. Always test with small areas first.

## Common Tasks

### Download Small Area (Recommended for Testing)

```bash
satellite-download --bbox 110,30,110.01,30.01 --resolution 0.0001 --output test.tif
```

### Download with Explicit Zoom

```bash
satellite-download --bbox 110,30,110.1,30.1 --zoom 18 --output detailed.tif
```

### Download Large Area

```bash
satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output large.tif --bigtiff --workers 16
```

### Resume Interrupted Download

```bash
# Re-run the same command - cached tiles will be reused
satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output area.tif
```

## Output Format

The generated GeoTIFF file contains:
- **RGB imagery**: 3 bands, uint8, 256x256 pixel tiles
- **CRS**: EPSG:4326 (WGS84)
- **Georeferencing**: Affine transform linking pixels to coordinates
- **Compression**: LZW by default (reduces file size)
- **Metadata**: Source, zoom level, tile count

## Quality Criteria

### Good Download Checklist

- [ ] Test with small area first (< 100 tiles)
- [ ] Verify bounds in output match request
- [ ] Check file size is reasonable (not corrupted)
- [ ] Validate with `gdalinfo output.tif`
- [ ] Visual check in QGIS or similar

### Signs of Problems

- **"negative dimensions" error**: Coordinate calculation bug (check y_min/y_max)
- **"no tiles downloaded"**: Zoom/tile calculation issue
- **Corrupted output**: Network issues or incomplete download
- **Very large file**: May need BigTIFF or higher compression

## Pitfalls to Avoid

### 1. Y-Axis Confusion

In tile coordinates, Y increases **downward** (north to south):
- `y_max` = top (smaller value)
- `y_min` = bottom (larger value)
- Always ensure `y_max <= y_min`

### 2. Large Downloads

At zoom 18+, a 1° × 1° area = **millions of tiles**:
- Always calculate tile count before downloading
- Use `--bigtiff` for files > 4GB
- Consider downloading in chunks

### 3. Rate Limiting

Google may throttle excessive requests:
- Tool includes delays between requests
- Don't increase workers too much (max ~16)
- Cache helps avoid re-downloads

### 4. Bounds Calculation

Remember the tile-to-latlon conversion:
- Tile (x, y) → returns **top-left** corner
- For bottom-right, use (x+1, y+1)
- In EPSG:4326: bottom < top (lat increases northward)

## Example Workflow

**User Request**: "Download satellite imagery for Tokyo Bay area"

**Step 1**: Determine coordinates
- Tokyo Bay approximately: 139.7°E to 140.0°E, 35.5°N to 35.7°N

**Step 2**: Choose appropriate zoom
- For overview: zoom 14 (~10m/pixel)
- For detail: zoom 16-18

**Step 3**: Estimate tile count
```
tiles ≈ (Δlon × 2^zoom / 360) × (Δlat × 2^zoom / 180)
at zoom 14: ≈ 50 tiles
at zoom 18: ≈ 1200 tiles
```

**Step 4**: Run download
```bash
satellite-download --bbox 139.7,35.5,140.0,35.7 --zoom 16 --output tokyo_bay.tif
```

**Step 5**: Verify
```bash
gdalinfo tokyo_bay.tif
```

## Dependencies

- Python ≥ 3.8
- click (CLI framework)
- rasterio (GeoTIFF writing)
- PIL/Pillow (image handling)
- requests (HTTP downloads)
- numpy (array operations)

## Source

Based on Web Mercator tile standard used by Google Maps/Earth.
Reference: https://en.wikipedia.org/wiki/Web_Mercator_projection

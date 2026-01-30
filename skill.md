# Satellite Downloader Skill

Download Google satellite imagery for any area and export as GeoTIFF format.

## When to use this skill

Use this skill when the user wants to:
- Download satellite imagery for a specific geographic area
- Create a GeoTIFF file from Google Satellite imagery
- Get high-resolution aerial/satellite photos for mapping or GIS work

## Parameters

### Required
- `--bbox` or `--extent`: Define the area to download
  - `--bbox`: "min_lon,min_lat,max_lon,max_lat" (e.g., "110,30,110.1,30.1")
  - `--extent`: "E{min}-E{max},N{min}-N{max}" (e.g., "E110-E110.1,N30-N30.1")
- `--output`: Output file path (e.g., "area.tif")

### Optional
- `--resolution`: Resolution in degrees (e.g., 0.0001 = ~11m per pixel)
- `--zoom`: Explicit zoom level (1-22, higher = more detail)
- `--bigtiff`: Use BigTIFF format for very large areas (>4GB)
- `--compression`: Compression method - lzw, deflate, jpeg, none
- `--workers`: Number of concurrent downloads (default: 8)

## Zoom Level Guide

| Zoom | Resolution | Detail Level | Use Case |
|------|-----------|--------------|----------|
| 10 | ~100m/pixel | City overview | Large regions |
| 14 | ~10m/pixel | Street level | Town districts |
| 18 | ~1m/pixel | Building detail | Individual buildings |
| 20 | ~0.3m/pixel | Maximum detail | Small areas only |

## Examples

### Basic usage
```
satellite-download --bbox 110,30,110.1,30.1 --resolution 0.0001 --output area.tif
```

### High zoom for small area
```
satellite-download --bbox 110,30,110.01,30.01 --zoom 18 --output detailed.tif
```

### Large area
```
satellite-download --bbox 110,30,111,31 --resolution 0.0001 --output large.tif --bigtiff
```

## Output

The skill generates:
- GeoTIFF file with proper georeferencing (EPSG:4326)
- RGB satellite imagery
- Compression to reduce file size

## Tips

1. Start with a small area to test before downloading large regions
2. Use `--resolution` for automatic zoom calculation, or specify `--zoom` directly
3. Enable BigTIFF for areas larger than 100x100 tiles
4. The tool has built-in caching - interrupted downloads can be resumed
5. Typical tile size: 256x256 pixels, ~50KB per tile

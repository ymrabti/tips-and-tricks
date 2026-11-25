uv init --name pymodname

uv add -r requirements.txt

uv run app.py

## GISco — GIS file collector

`gisco.py` opens a desktop UI (tkinter, no extra dependency) that harvests GIS datasets
from a folder tree into a single destination folder.

```powershell
cd python
uv run gisco.py
# or
.\.venv\Scripts\python.exe gisco.py
```

What the UI configures:

- **GIS file types** — neon chips per format family (shapefile and all its sidecars, file
  geodatabase folders, GeoPackage, KML/KMZ, GeoJSON/TopoJSON, GML, GPX, CAD, MapInfo, E00,
  FlatGeobuf, OSM, rasters, ESRI/QGIS layers and projects). Rasters are off by default;
  `Extra extensions` accepts a comma-separated list for anything not covered by a chip.
- **File size filter (MIN / MAX, MB)** — applies to every selected format, not just shapefiles:
  shapefile datasets are sized as `shp+shx+dbf+prj+cpg+…` summed together, every other format uses
  its own file size. `0` (or an empty field) means no bound, so you can keep a window such as
  `2 MB … 512 MB`. Skipped datasets are reported in the console with the measured size.
- **Keywords** — case-insensitive filter on file stems, comma separated.
- **Preserve folder tree** — copies into mirrored sub-folders; unchecked flattens everything
  into the destination root using the `FLATTEN SEPARATOR` breadcrumb (default `__`) and
  `_1`, `_2` suffixes for name collisions.
- **Transform selected to GeoJSON (EPSG:4326)** — converts every GDAL-readable vector dataset
  with geopandas/pyogrio, reprojecting to WGS84. Multi-layer GeoPackages emit one
  `<stem>_<layer>.geojson` per layer. Uncheck **Keep original files** to write only the
  GeoJSON (shapefile sidecars are then skipped too).
- **Dry run** — prints the plan in the console panel without writing anything.

GeoJSON conversion needs `geopandas` and `pyogrio` (already in `pyproject.toml`); the
checkbox is disabled automatically when they cannot be imported.

"""GISco - collect GIS datasets from a folder tree into a single destination.

Run without arguments to open the neon configuration UI.
"""

from __future__ import annotations

import os
import queue
import shutil
import threading
import tkinter as tk
from dataclasses import dataclass, field
from datetime import datetime
from tkinter import filedialog, font as tkfont, messagebox
from typing import Callable, Iterable

# Extensions that make up one shapefile dataset (their sizes are summed)
SHAPEFILE_PARTS = {
    "shp",
    "shx",
    "dbf",
    "prj",
    "cpg",
    "sbn",
    "sbx",
    "qix",
    "fbn",
    "fbx",
    "ain",
    "aih",
    "ixs",
    "mxs",
    "atx",
    "qpj",
    "idx",
    "shp.xml",
}

# Vector data
VECTOR_EXTENSIONS = set(SHAPEFILE_PARTS) | {
    "gpkg",
    "kml",
    "kmz",
    "geojson",
    "gml",
    "gpx",
    "dxf",
    "dwg",
    "dgn",
    "tab",
    "mif",
    "mid",
    "e00",
    "osm",
    "pbf",
    "topojson",
    "fgb",
}

# Layers, maps, projects, packages
PROJECT_EXTENSIONS = {
    "lyr",
    "lyrx",
    "sd",
    "sddraft",
    "mxd",
    "aprx",
    "qgs",
    "qgz",
    "qlr",
    "mpk",
    "ppkx",
    "mmpk",
    "tpk",
    "tpkx",
    "vtpk",
    "slpk",
    "stylx",
    "style",
    "pitem",
    "gpkx",
    "atbx",
    "tbx",
}

# Optional: raster data (off by default because tif/jp2/png etc. are ambiguous)
RASTER_EXTENSIONS = {
    "tif",
    "tiff",
    "img",
    "ecw",
    "sid",
    "jp2",
    "asc",
    "dem",
    "hgt",
    "tfw",
    "tifw",
    "wld",
    "jgw",
    "pgw",
    "bpw",
    "aux.xml",
    "ovr",
    "rrd",
    "las",
    "laz",
}

# Formats OGR can read as vector features, therefore convertible to GeoJSON
GEOJSON_READABLE = {
    "shp",
    "gpkg",
    "kml",
    "kmz",
    "geojson",
    "gml",
    "gpx",
    "dxf",
    "dgn",
    "tab",
    "mif",
    "e00",
    "fgb",
    "topojson",
}

# Extensions made of two parts; must be checked before os.path.splitext
COMPOUND_EXTENSIONS = (".shp.xml", ".aux.xml")

# UI format chips: (key, label, extensions, accent, default_on)
FORMAT_CHIPS = (
    (
        "Vector",
        (
            ("shp", "SHAPEFILE", SHAPEFILE_PARTS, True),
            ("gpkg", "GEOPACKAGE", {"gpkg"}, True),
            ("gdb", "FILE GDB", set(), True),
            ("kml", "KML / KMZ", {"kml", "kmz"}, True),
            ("geojson", "GEOJSON / TOPOJSON", {"geojson", "topojson"}, True),
            ("gml", "GML", {"gml"}, True),
            ("gpx", "GPX", {"gpx"}, True),
            ("cad", "DXF / DWG / DGN", {"dxf", "dwg", "dgn"}, True),
            ("mapinfo", "MAPINFO", {"tab", "mif", "mid"}, True),
            ("e00", "E00", {"e00"}, True),
            ("fgb", "FLATGEOBUF", {"fgb"}, True),
            ("osm", "OSM / PBF", {"osm", "pbf"}, True),
        ),
    ),
    (
        "Rasters",
        (
            ("tif", "GEOTIFF", {"tif", "tiff", "tfw", "tifw"}, False),
            ("img", "ERDAS IMG", {"img"}, False),
            ("ecw", "ECW", {"ecw"}, False),
            ("sid", "MRSID", {"sid"}, False),
            ("jp2", "JPEG2000", {"jp2", "jgw"}, False),
            ("grid", "ASC / DEM / HGT", {"asc", "dem", "hgt"}, False),
            ("world", "WORLD FILES", {"wld", "pgw", "bpw", "aux.xml"}, False),
            ("pyramid", "OVR / RRD", {"ovr", "rrd"}, False),
            ("lidar", "LAS / LAZ", {"las", "laz"}, False),
        ),
    ),
    (
        "Projects & layers",
        (
            ("esri_layers", "ESRI LAYERS", {"lyr", "lyrx", "sd", "sddraft", "stylx", "style", "pitem", "atbx", "tbx"}, True),
            ("esri_projects", "ARCMAP / PRO", {"mxd", "aprx"}, True),
            ("qgis", "QGIS", {"qgs", "qgz", "qlr"}, True),
            ("packages", "PACKAGES", {"mpk", "ppkx", "mmpk", "tpk", "tpkx", "vtpk", "slpk", "gpkx"}, True),
        ),
    ),
)

# key -> extension set, so the UI and the engine agree on what each chip selects
CHIP_EXTENSIONS: dict[str, set[str]] = {
    key: {ext.lower().lstrip(".") for ext in extensions}
    for _category, entries in FORMAT_CHIPS
    for key, _label, extensions, _default_on in entries
}


class GiscoError(Exception):
    """User-facing configuration or filesystem error."""


def make_long_path_safe(path: str) -> str:
    """Prepend the Windows extended path prefix to bypass the 260 char limit."""
    abs_path = os.path.abspath(path)
    if os.name == "nt" and not abs_path.startswith("\\\\?\\"):
        return "\\\\?\\" + abs_path
    return abs_path


def split_name(filename: str) -> tuple[str, str]:
    """Split into (stem, extension-with-dot), handling compound extensions."""
    lower = filename.lower()
    for comp in COMPOUND_EXTENSIONS:
        if lower.endswith(comp):
            return filename[: -len(comp)], comp
    stem, ext = os.path.splitext(filename)
    return stem, ext.lower()


def format_size(num_bytes: float) -> str:
    """Human readable byte count."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(num_bytes) < 1024 or unit == "TB":
            return f"{num_bytes:.0f} {unit}" if unit in ("B", "KB") else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def geojson_backend_available() -> tuple[bool, str]:
    """Tell whether the GeoJSON transform can run in this interpreter."""
    try:
        import geopandas  # noqa: F401
        import pyogrio  # noqa: F401
    except Exception as exc:  # pragma: no cover - depends on the environment
        return False, str(exc)
    return True, ""


@dataclass
class CopyOptions:
    """Everything the collector needs to know, independent of the UI."""

    source: str
    dest: str
    extensions: set[str] = field(default_factory=set)
    include_gdb: bool = True
    keywords: list[str] = field(default_factory=list)
    min_size_mb: float = 0.0
    max_size_mb: float = 0.0
    preserve_tree: bool = True
    separator: str = "__"
    convert_geojson: bool = False
    keep_originals: bool = True
    dry_run: bool = False


@dataclass
class Stats:
    """Counters reported back to the UI."""

    files: int = 0
    gdbs: int = 0
    converted: int = 0
    skipped: int = 0
    failed: int = 0

    def summary(self) -> str:
        return (
            f"{self.files} file(s), {self.gdbs} geodatabase(s) copied, "
            f"{self.converted} GeoJSON written, {self.skipped} skipped, "
            f"{self.failed} failed"
        )


@dataclass
class _Member:
    path: str
    stem: str
    ext: str  # lowercase, with dot


@dataclass
class _GdbItem:
    src: str
    rel_dir: str
    name: str


@dataclass
class _GroupItem:
    rel_dir: str
    members: list[_Member]


LogFn = Callable[[str, str], None]
ProgressFn = Callable[[int, int], None]


def _keyword_ok(stem: str, keywords: Iterable[str]) -> bool:
    keywords = list(keywords)
    if not keywords:
        return True
    lowered = stem.lower()
    return any(keyword in lowered for keyword in keywords)


def _representative(members: list[_Member]) -> str:
    """Pick the file worth naming in a log line (shapefile first)."""
    for member in members:
        if member.ext.lower() == ".shp":
            return member.path
    return members[0].path


def build_plan(
    options: CopyOptions,
    on_log: LogFn | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> tuple[list[_GdbItem | _GroupItem], int, bool]:
    """Walk the source tree and return what would be copied.

    Returns (items, size_filtered_datasets_skipped, was_stopped).
    """
    on_log = on_log or (lambda message, level="info": None)
    should_stop = should_stop or (lambda: False)

    source_abs = os.path.abspath(options.source)
    dest_abs = os.path.abspath(options.dest)
    allowed = {ext.lower().lstrip(".") for ext in options.extensions}
    keywords = [keyword.lower() for keyword in options.keywords]
    min_bytes = int(options.min_size_mb * 1024 * 1024) if options.min_size_mb > 0 else 0
    max_bytes = int(options.max_size_mb * 1024 * 1024) if options.max_size_mb > 0 else 0

    items: list[_GdbItem | _GroupItem] = []
    skipped = 0

    for root, dirs, files in os.walk(source_abs):
        if should_stop():
            return items, skipped, True

        # Never walk into the destination folder (even if nested in the source)
        dirs[:] = [d for d in dirs if os.path.abspath(os.path.join(root, d)) != dest_abs]
        dirs.sort()

        # An unreadable or malformed folder must not abort the scan
        try:
            rel_dir = os.path.relpath(root, source_abs)
            rel_dir = "" if rel_dir == "." else rel_dir

            for directory in list(dirs):
                if not directory.lower().endswith(".gdb"):
                    continue
                dirs.remove(directory)  # don't descend into internal .gdbtable etc.
                if not options.include_gdb:
                    continue
                if not _keyword_ok(directory[:-4], keywords):
                    continue
                items.append(
                    _GdbItem(
                        src=os.path.join(root, directory),
                        rel_dir=rel_dir,
                        name=directory,
                    )
                )

            groups: dict[str, list[_Member]] = {}
            for filename in sorted(files):
                stem, ext = split_name(filename)
                if ext.lstrip(".").lower() not in allowed:
                    continue
                if not _keyword_ok(stem, keywords):
                    continue
                groups.setdefault(stem.lower(), []).append(
                    _Member(path=os.path.join(root, filename), stem=stem, ext=ext)
                )

            for members in groups.values():
                # Shapefile datasets are sized with their sidecars; other formats on their own
                has_shapefile = any(member.ext.lower() == ".shp" for member in members)
                dataset_bytes = 0
                for member in members:
                    if has_shapefile and member.ext.lstrip(".").lower() not in SHAPEFILE_PARTS:
                        continue
                    try:
                        dataset_bytes += os.path.getsize(member.path)
                    except OSError:
                        continue

                if min_bytes and dataset_bytes < min_bytes:
                    skipped += 1
                    on_log(
                        f"Skipped small dataset: {_representative(members)} "
                        f"({format_size(dataset_bytes)} < {format_size(min_bytes)})",
                        "warning",
                    )
                    continue
                if max_bytes and dataset_bytes > max_bytes:
                    skipped += 1
                    on_log(
                        f"Skipped oversized dataset: {_representative(members)} "
                        f"({format_size(dataset_bytes)} > {format_size(max_bytes)})",
                        "warning",
                    )
                    continue
                items.append(_GroupItem(rel_dir=rel_dir, members=members))
        except Exception as exc:
            on_log(f"Skipped unreadable folder {root}: {exc}", "warning")
            continue

    return items, skipped, False


def _is_taken(path: str, planned: set[str]) -> bool:
    return os.path.exists(make_long_path_safe(path)) or os.path.normcase(path) in planned


def _unique_path(target_dir: str, base_stem: str, suffix: str, planned: set[str]) -> str:
    candidate = os.path.join(target_dir, f"{base_stem}{suffix}")
    counter = 0
    while _is_taken(candidate, planned):
        counter += 1
        candidate = os.path.join(target_dir, f"{base_stem}_{counter}{suffix}")
    return candidate


def _slug(value: str) -> str:
    cleaned = [ch if ch.isalnum() or ch in "-_" else "_" for ch in value]
    slug = "".join(cleaned).strip("_")
    return slug or "layer"


def _try_paths(path: str):
    yield make_long_path_safe(path)
    if os.name == "nt":
        yield path


def _read_layer(path: str, layer: str | None):
    import geopandas as gpd

    last_error: Exception | None = None
    for candidate in _try_paths(path):
        try:
            return gpd.read_file(candidate, layer=layer, engine="pyogrio")
        except Exception as exc:  # pragma: no cover - depends on GDAL/driver
            last_error = exc
    raise last_error  # type: ignore[misc]


def _write_geojson(frame, path: str) -> None:
    last_error: Exception | None = None
    for candidate in _try_paths(path):
        try:
            frame.to_file(candidate, driver="GeoJSON", engine="pyogrio")
            return
        except Exception as exc:  # pragma: no cover - depends on GDAL/driver
            last_error = exc
    raise last_error  # type: ignore[misc]


def _convert_member(
    member: _Member,
    target_dir: str,
    prefix: str,
    suffix: str,
    options: CopyOptions,
    stats: Stats,
    planned: set[str],
    on_log: LogFn,
    should_stop: Callable[[], bool],
) -> None:
    """Convert every layer of one dataset; a failing layer never stops the run."""
    try:
        from pyogrio import list_layers
    except Exception as exc:  # pragma: no cover - depends on the environment
        raise GiscoError(
            "GeoJSON transform needs geopandas + pyogrio (pip install geopandas pyogrio)."
        ) from exc

    try:
        layers = [row[0] for row in list_layers(member.path)]
    except Exception as exc:
        on_log(f"GeoJSON layer listing failed: {member.path}: {exc}", "warning")
        layers = []

    multi_layer = len(layers) > 1
    for layer in layers or [None]:
        if should_stop():
            return
        try:
            _convert_layer(
                member, layer, multi_layer, target_dir, prefix, suffix, options, stats, planned, on_log
            )
        except Exception as exc:
            stats.failed += 1
            on_log(f"GeoJSON conversion failed: {_where(member, layer if multi_layer else None)}: {exc}", "error")


def _where(member: _Member, layer: str | None) -> str:
    return f"{member.path} [layer {layer}]" if layer else member.path


def _convert_layer(
    member: _Member,
    layer: str | None,
    multi_layer: bool,
    target_dir: str,
    prefix: str,
    suffix: str,
    options: CopyOptions,
    stats: Stats,
    planned: set[str],
    on_log: LogFn,
) -> None:
    base = f"{prefix}{member.stem}{suffix}"
    if multi_layer and layer:
        base = f"{base}_{_slug(layer)}"
    out_path = _unique_path(target_dir, base, ".geojson", planned)
    planned.add(os.path.normcase(out_path))

    if options.dry_run:
        on_log(f"[DRY RUN] Would write GeoJSON: {member.path} -> {out_path}", "path")
        stats.converted += 1
        return

    try:
        frame = _read_layer(member.path, layer)
    except Exception as exc:
        stats.failed += 1
        on_log(f"GeoJSON read failed: {_where(member, layer if multi_layer else None)}: {exc}", "error")
        return

    if getattr(frame, "empty", True):
        stats.skipped += 1
        on_log(f"GeoJSON skipped (no features): {_where(member, layer if multi_layer else None)}", "warning")
        return
    if not hasattr(frame, "geometry"):
        stats.skipped += 1
        on_log(f"GeoJSON skipped (not a vector layer): {_where(member, layer if multi_layer else None)}", "warning")
        return

    crs = getattr(frame, "crs", None)
    epsg = None
    can_reproject = crs is not None and hasattr(crs, "to_epsg")
    if can_reproject:
        try:
            epsg = crs.to_epsg()
        except Exception:
            can_reproject, epsg = False, None

    if crs is None:
        on_log(
            f"No CRS in {os.path.basename(member.path)} - GeoJSON written as-is",
            "warning",
        )
    elif not can_reproject:
        on_log(
            f"Unusable CRS metadata in {os.path.basename(member.path)} - GeoJSON written as-is",
            "warning",
        )
    elif epsg != 4326:
        try:
            frame = frame.to_crs(4326)
        except Exception as exc:
            stats.failed += 1
            on_log(f"Reprojection to EPSG:4326 failed: {member.path}: {exc}", "error")
            return

    try:
        os.makedirs(make_long_path_safe(target_dir), exist_ok=True)
        _write_geojson(frame, out_path)
    except Exception as exc:
        stats.failed += 1
        on_log(f"GeoJSON write failed: {out_path}: {exc}", "error")
        return

    stats.converted += 1
    on_log(f"GeoJSON: {member.path} -> {out_path}", "success")


def run_job(
    options: CopyOptions,
    on_log: LogFn | None = None,
    on_progress: ProgressFn | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> Stats:
    """Scan the source folder and copy/convert every matching GIS dataset."""
    on_log = on_log or (lambda message, level="info": None)
    on_progress = on_progress or (lambda done, total: None)
    should_stop = should_stop or (lambda: False)

    stats = Stats()
    source_abs = os.path.abspath(options.source)
    dest_abs = os.path.abspath(options.dest)

    if not os.path.exists(source_abs):
        raise GiscoError(f"The source folder '{options.source}' does not exist.")
    if not os.path.isdir(source_abs):
        raise GiscoError(f"'{options.source}' is not a directory.")
    if not options.dest.strip():
        raise GiscoError("Choose a destination folder.")
    if os.path.normcase(source_abs) == os.path.normcase(dest_abs):
        raise GiscoError("The destination must be different from the source folder.")

    tag = "[DRY RUN] " if options.dry_run else ""
    on_log(f"Scanning {source_abs}", "header")

    items, skipped, stopped = build_plan(options, on_log, should_stop)
    stats.skipped = skipped
    if stopped:
        on_log("Stopped while scanning.", "warning")
        return stats
    if not items:
        on_log("No matching GIS datasets found.", "warning")
        return stats

    on_log(
        f"Plan: {len(items)} dataset(s), {skipped} skipped by size "
        f"({'tree preserved' if options.preserve_tree else 'flat output'})",
        "info",
    )

    dest_safe = make_long_path_safe(dest_abs)
    if not options.dry_run:
        try:
            os.makedirs(dest_safe, exist_ok=True)
        except OSError as exc:
            raise GiscoError(f"Cannot create destination '{options.dest}': {exc}") from exc

    planned: set[str] = set()
    total = len(items)

    def target_dir_for(rel_dir: str) -> str:
        if options.preserve_tree and rel_dir:
            return os.path.join(dest_abs, rel_dir)
        return dest_abs

    def prefix_for(rel_dir: str) -> str:
        if options.preserve_tree or not rel_dir:
            return ""
        return options.separator.join(rel_dir.split(os.sep)) + options.separator

    def process_item(item: _GdbItem | _GroupItem) -> None:
        target_dir = target_dir_for(item.rel_dir)
        prefix = prefix_for(item.rel_dir)

        if isinstance(item, _GdbItem):
            counter = 0
            out_name = f"{prefix}{item.name}"
            while _is_taken(os.path.join(target_dir, out_name), planned):
                counter += 1
                out_name = f"{prefix}{item.name[:-4]}_{counter}.gdb"
            shown = os.path.join(options.dest, os.path.relpath(os.path.join(target_dir, out_name), dest_abs))
            planned.add(os.path.normcase(os.path.join(target_dir, out_name)))
            if options.dry_run:
                on_log(f"{tag}Would copy GDB: {item.src} -> {shown}", "path")
                stats.gdbs += 1
                return
            try:
                os.makedirs(make_long_path_safe(target_dir), exist_ok=True)
                shutil.copytree(
                    make_long_path_safe(item.src),
                    make_long_path_safe(os.path.join(target_dir, out_name)),
                )
                stats.gdbs += 1
                on_log(f"Copied GDB: {item.src} -> {shown}", "success")
            except Exception as exc:
                stats.failed += 1
                on_log(f"Failed to copy GDB {item.name}: {exc}", "error")
            return

        # A shapefile converted on its own loses its sidecars, so the whole family goes
        shapefile_convert_only = (
            options.convert_geojson
            and not options.keep_originals
            and any(member.ext.lower() == ".shp" for member in item.members)
        )

        def group_outputs(for_suffix: str) -> list[tuple[str, _Member, str]]:
            entries = []
            for member in item.members:
                key = member.ext.lstrip(".").lower()
                convertible = options.convert_geojson and key in GEOJSON_READABLE
                dropped_sidecar = shapefile_convert_only and key in SHAPEFILE_PARTS
                copy_original = not dropped_sidecar and (not convertible or options.keep_originals)
                base = f"{prefix}{member.stem}{for_suffix}"
                if copy_original:
                    entries.append(("copy", member, os.path.join(target_dir, base + member.ext)))
                if convertible:
                    entries.append(("convert", member, os.path.join(target_dir, base + ".geojson")))
            return entries

        # One suffix for the whole group so ro.shp/.shx/.dbf/.prj share a name
        counter = 0
        suffix = ""
        while any(_is_taken(path, planned) for _kind, _member, path in group_outputs(suffix)):
            counter += 1
            suffix = f"_{counter}"

        for kind, member, dest_path in group_outputs(suffix):
            if kind == "copy":
                planned.add(os.path.normcase(dest_path))
                shown = os.path.join(options.dest, os.path.relpath(dest_path, dest_abs))
                if options.dry_run:
                    on_log(f"{tag}Would copy: {member.path} -> {shown}", "path")
                    stats.files += 1
                    continue
                try:
                    os.makedirs(make_long_path_safe(target_dir), exist_ok=True)
                    shutil.copy2(make_long_path_safe(member.path), make_long_path_safe(dest_path))
                    stats.files += 1
                    on_log(f"Copied: {member.path} -> {shown}", "info")
                except Exception as exc:
                    stats.failed += 1
                    on_log(f"Failed to copy {member.ext or member.stem}: {member.path}: {exc}", "error")
                continue

            try:
                _convert_member(
                    member, target_dir, prefix, suffix, options, stats, planned, on_log, should_stop
                )
            except GiscoError as exc:
                on_log(str(exc), "error")
                stats.failed += 1

    stopped = False
    for index, item in enumerate(items, start=1):
        if should_stop():
            stopped = True
            break

        # One broken dataset must never abort the batch: log it and carry on
        try:
            process_item(item)
        except Exception as exc:
            stats.failed += 1
            label = item.name if isinstance(item, _GdbItem) else item.members[0].path
            on_log(f"Skipped after unexpected error: {label}: {exc}", "error")

        on_progress(index, total)

    verb = "would be processed" if options.dry_run else "processed"
    on_log(
        f"{tag}Done: {stats.summary()} - {verb}."
        + (" Nothing was written." if options.dry_run else ""),
        "warning" if stopped else "success",
    )
    if stopped:
        on_log("Stopped by user.", "warning")
    return stats


# --------------------------------------------------------------------------- #
# Neon cyberpunk theme
# --------------------------------------------------------------------------- #


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _rgb_to_hex(rgb: Iterable[float]) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(channel)))) for channel in rgb)


def mix(color_a: str, color_b: str, ratio: float) -> str:
    """Blend two hex colors (0 = color_a, 1 = color_b)."""
    a, b = _hex_to_rgb(color_a), _hex_to_rgb(color_b)
    return _rgb_to_hex(a[i] + (b[i] - a[i]) * ratio for i in range(3))


class Palette:
    BG = "#06050e"
    BG_SOFT = "#0b0818"
    PANEL = "#110a22"
    PANEL_SOFT = "#180f2e"
    INPUT = "#0c0918"
    BORDER = "#2a1c4d"
    TEXT = "#e9e6f7"
    MUTED = "#847fa6"
    CYAN = "#00f0ff"
    MAGENTA = "#ff2bd6"
    VIOLET = "#9d4edd"
    LIME = "#39ff14"
    AMBER = "#ffb400"
    RED = "#ff3b6b"


UI_FONT = "Segoe UI"
MONO_FONT = "Consolas"


def ui_font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    return (UI_FONT, size, weight)


def mono_font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    return (MONO_FONT, size, weight)


def _background_of(widget) -> str:
    try:
        return widget.cget("bg")
    except tk.TclError:
        return Palette.PANEL


class NeonCheck(tk.Frame):
    """Canvas-drawn checkbox with a neon glow when selected."""

    def __init__(
        self,
        master,
        text: str,
        variable: tk.BooleanVar,
        accent: str = Palette.CYAN,
        bg: str | None = None,
        font=None,
        command: Callable[[], None] | None = None,
    ):
        bg = bg or _background_of(master)
        super().__init__(master, bg=bg, cursor="hand2")
        self.var = variable
        self.accent = accent
        self.command = command
        self._bg = bg
        self._hover = False
        self._enabled = True

        self.canvas = tk.Canvas(
            self, width=17, height=17, bg=bg, highlightthickness=0, bd=0, cursor="hand2"
        )
        self.canvas.pack(side=tk.LEFT, padx=(0, 7))
        self.glow = self.canvas.create_rectangle(1, 1, 16, 16, outline=mix(bg, accent, 0.0), width=1)
        self.box = self.canvas.create_rectangle(
            3, 3, 14, 14, outline=mix(Palette.MUTED, bg, 0.25), width=1, fill=bg
        )
        self.tick = self.canvas.create_line(
            5.5,
            9,
            8,
            11.5,
            12,
            5.5,
            fill=bg,
            width=2,
            capstyle=tk.ROUND,
            joinstyle=tk.ROUND,
            state=tk.HIDDEN,
        )
        self.label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=Palette.TEXT,
            font=font or ui_font(9),
            cursor="hand2",
            anchor="w",
            justify=tk.LEFT,
        )
        self.label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        for widget in (self, self.canvas, self.label):
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

        self.var.trace_add("write", lambda *_: self._render())
        self._render()

    def _toggle(self, _event=None):
        if not self._enabled:
            return
        self.var.set(not self.var.get())
        if self.command:
            self.command()

    def _enter(self, _event=None):
        self._hover = True
        self._render()

    def _leave(self, _event=None):
        self._hover = False
        self._render()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self.label.configure(fg=Palette.TEXT if enabled else mix(Palette.TEXT, self._bg, 0.6))
        for widget in (self, self.canvas, self.label):
            widget.configure(cursor="hand2" if enabled else "arrow")
        self._render()

    def _render(self):
        checked = bool(self.var.get())
        accent = self.accent if self._enabled else mix(self.accent, self._bg, 0.78)
        if checked:
            self.canvas.itemconfigure(self.box, fill=accent, outline=accent)
            self.canvas.itemconfigure(self.glow, outline=mix(self._bg, accent, 0.45))
            self.canvas.itemconfigure(self.tick, fill=self._bg, state=tk.NORMAL)
        else:
            outline = mix(Palette.MUTED, accent, 0.75) if self._hover and self._enabled else mix(Palette.MUTED, self._bg, 0.3)
            self.canvas.itemconfigure(self.box, fill=self._bg, outline=outline)
            self.canvas.itemconfigure(self.glow, outline=mix(self._bg, accent, 0.22 if self._hover else 0.0))
            self.canvas.itemconfigure(self.tick, state=tk.HIDDEN)


class NeonButton(tk.Frame):
    """Flat neon button drawn with labels so the colors survive on Windows."""

    def __init__(
        self,
        master,
        text: str,
        command: Callable[[], None],
        accent: str = Palette.CYAN,
        solid: bool = False,
        bg: str | None = None,
        font=None,
    ):
        bg = bg or _background_of(master)
        super().__init__(master, bg=mix(bg, accent, 0.55), cursor="hand2")
        self.accent = accent
        self.solid = solid
        self._bg = bg
        self._command = command
        self._enabled = True
        self.label = tk.Label(
            self,
            text=text,
            bg=accent if solid else mix(bg, accent, 0.10),
            fg=Palette.BG if solid else accent,
            font=font or mono_font(9, "bold"),
            padx=16,
            pady=7,
            cursor="hand2",
        )
        self.label.pack(padx=1, pady=1, fill=tk.BOTH, expand=True)
        for widget in (self, self.label):
            widget.bind("<Button-1>", self._click)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

    def _click(self, _event=None):
        if self._enabled:
            self._command()

    def _enter(self, _event=None):
        if not self._enabled:
            return
        self.label.configure(bg=self.accent, fg=Palette.BG)

    def _leave(self, _event=None):
        if not self._enabled:
            return
        self.label.configure(
            bg=self.accent if self.solid else mix(self._bg, self.accent, 0.10),
            fg=Palette.BG if self.solid else self.accent,
        )

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        accent = self.accent if enabled else mix(self.accent, self._bg, 0.6)
        self.configure(bg=mix(self._bg, accent, 0.4), cursor="hand2" if enabled else "arrow")
        self.label.configure(
            bg=accent if self.solid else mix(self._bg, accent, 0.08),
            fg=Palette.BG if self.solid else accent,
            cursor="hand2" if enabled else "arrow",
        )


class GlowCard(tk.Frame):
    """Panel with a 1px neon edge and a mono section title."""

    def __init__(self, master, title: str, accent: str = Palette.CYAN, **kwargs):
        super().__init__(master, bg=mix(Palette.BG, accent, 0.4), **kwargs)
        self.accent = accent
        body = tk.Frame(self, bg=Palette.PANEL)
        body.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        header = tk.Frame(body, bg=Palette.PANEL)
        header.pack(fill=tk.X, padx=14, pady=(11, 4))
        tk.Frame(header, bg=accent, width=2, height=12).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(
            header,
            text=title.upper(),
            bg=Palette.PANEL,
            fg=accent,
            font=mono_font(9, "bold"),
        ).pack(side=tk.LEFT)
        self.content = tk.Frame(body, bg=Palette.PANEL)
        self.content.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))


class Chip(tk.Label):
    """Toggleable neon format chip."""

    def __init__(self, master, text: str, variable: tk.BooleanVar, accent: str, bg: str):
        super().__init__(
            master,
            text=text,
            font=mono_font(8, "bold"),
            padx=8,
            pady=4,
            bd=0,
            takefocus=0,
            cursor="hand2",
        )
        self.var = variable
        self.accent = accent
        self._bg = bg
        self._hover = False
        self.bind("<Button-1>", lambda _event: self.var.set(not self.var.get()))
        self.bind("<Enter>", lambda _event: self._render(hover=True))
        self.bind("<Leave>", lambda _event: self._render(hover=False))
        self.var.trace_add("write", lambda *_: self._render())
        self._render()

    def _render(self, hover: bool | None = None):
        if hover is not None:
            self._hover = hover
        if self.var.get():
            self.configure(
                bg=mix(self._bg, self.accent, 0.22),
                fg=self.accent,
                highlightthickness=1,
                highlightbackground=self.accent,
                highlightcolor=self.accent,
            )
        else:
            outline = mix(self._bg, self.accent, 0.4 if self._hover else 0.14)
            self.configure(
                bg=self._bg,
                fg=mix(Palette.MUTED, self.accent, 0.55 if self._hover else 0.0),
                highlightthickness=1,
                highlightbackground=outline,
                highlightcolor=outline,
            )


class NeonProgress(tk.Canvas):
    """Thin progress bar with a neon leading edge."""

    def __init__(self, master, bg: str = Palette.PANEL):
        super().__init__(master, height=14, bg=bg, highlightthickness=0, bd=0)
        self._bg = bg
        self._fraction = 0.0
        self.bind("<Configure>", lambda _event: self._render())
        self._render()

    def set(self, fraction: float) -> None:
        self._fraction = max(0.0, min(1.0, fraction))
        self._render()

    def _render(self):
        self.delete("all")
        width = max(1, self.winfo_width())
        height = 14
        self.create_rectangle(
            0, 2, width - 1, height - 3, outline=mix(self._bg, Palette.CYAN, 0.25), fill=Palette.BG_SOFT
        )
        if self._fraction > 0:
            end = int((width - 3) * self._fraction)
            for x in range(end):
                ratio = x / max(1, width - 3)
                color = mix(Palette.CYAN, Palette.MAGENTA, ratio)
                self.create_line(x + 1, 3, x + 1, height - 4, fill=color)
            self.create_line(end + 1, 2, end + 1, height - 3, fill=mix(Palette.CYAN, "#ffffff", 0.6), width=2)


class NeonHeaderBar(tk.Canvas):
    """Gradient rule with a slow moving light streak."""

    def __init__(self, master, height: int = 3):
        super().__init__(master, height=height, bg=Palette.BG, highlightthickness=0, bd=0)
        self._height = height
        self._streak = None
        self._position = -80
        self.bind("<Configure>", self._draw)
        self._animate()

    def _draw(self, _event=None):
        self.delete("all")
        width = max(1, self.winfo_width())
        for x in range(width):
            ratio = x / width
            if ratio < 0.5:
                color = mix(Palette.CYAN, Palette.MAGENTA, ratio * 2)
            else:
                color = mix(Palette.MAGENTA, Palette.VIOLET, (ratio - 0.5) * 2)
            self.create_line(x, 0, x, self._height, fill=mix(Palette.BG, color, 0.55))
        self._streak = self.create_rectangle(
            self._position, 0, self._position + 90, self._height,
            fill=mix(Palette.CYAN, "#ffffff", 0.7), width=0,
        )

    def _animate(self):
        try:
            width = max(1, self.winfo_width())
            self._position += 6
            if self._position > width + 80:
                self._position = -80
            if self._streak is not None:
                self.coords(self._streak, self._position, 0, self._position + 90, self._height)
            self.after(40, self._animate)
        except tk.TclError:
            return


class NeonScrollbar(tk.Canvas):
    """Slim canvas scrollbar so the tracks stay inside the neon palette."""

    def __init__(self, master, command, accent: str = Palette.CYAN, bg: str = Palette.PANEL):
        super().__init__(master, width=10, bg=bg, highlightthickness=0, bd=0, cursor="hand2")
        self._command = command
        self._accent = accent
        self._bg = bg
        self._first = 0.0
        self._last = 1.0
        self._drag_origin: int | None = None
        self._drag_first = 0.0
        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._drag)
        self.bind("<ButtonRelease-1>", lambda _event: self._stop_drag())

    def set(self, first, last) -> None:
        self._first, self._last = float(first), float(last)
        self._draw()

    def _stop_drag(self) -> None:
        self._drag_origin = None

    def _draw(self) -> None:
        self.delete("all")
        height = max(1, self.winfo_height())
        width = self.winfo_width()
        self.create_rectangle(
            width - 3,
            0,
            width - 1,
            height,
            fill=mix(self._bg, self._accent, 0.08),
            outline="",
        )
        top = int(self._first * height)
        bottom = min(height, max(top + 24, int(self._last * height)))
        self.create_rectangle(
            2,
            top,
            width - 1,
            bottom,
            fill=mix(Palette.PANEL_SOFT, self._accent, 0.5),
            outline=mix(self._bg, self._accent, 0.55),
        )

    def _press(self, event) -> None:
        height = max(1, self.winfo_height())
        span = self._last - self._first
        thumb_top, thumb_bottom = self._first * height, self._last * height
        if thumb_top <= event.y <= thumb_bottom:
            self._drag_origin = event.y
            self._drag_first = self._first
            return
        self._command("moveto", max(0.0, min(1.0, event.y / height - span / 2)))

    def _drag(self, event) -> None:
        if self._drag_origin is None:
            return
        height = max(1, self.winfo_height())
        delta = (event.y - self._drag_origin) / height
        self._command("moveto", max(0.0, min(1.0, self._drag_first + delta)))


def styled_entry(master, variable, width: int | None = None) -> tk.Entry:
    entry = tk.Entry(
        master,
        textvariable=variable,
        bg=Palette.INPUT,
        fg=Palette.TEXT,
        insertbackground=Palette.CYAN,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=1,
        highlightbackground=Palette.BORDER,
        highlightcolor=Palette.CYAN,
        font=ui_font(9),
        disabledbackground=mix(Palette.INPUT, Palette.BG, 0.5),
        disabledforeground=Palette.MUTED,
    )
    if width:
        entry.configure(width=width)
    return entry


class GiscoApp:
    """Neon configuration UI for the GIS collector."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.messages: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker: threading.Thread | None = None
        self.running = False
        self.geojson_ready, self.geojson_reason = geojson_backend_available()
        self._wheel_bound = False

        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar(value="_gis_everything")
        self.keywords_var = tk.StringVar()
        self.size_filter_enabled = tk.BooleanVar(value=False)
        self.min_size_value = tk.StringVar(value="0")
        self.max_size_value = tk.StringVar(value="250")
        self.separator_var = tk.StringVar(value="__")
        self.preserve_tree = tk.BooleanVar(value=True)
        self.convert_geojson = tk.BooleanVar(value=False)
        self.keep_originals = tk.BooleanVar(value=True)
        self.dry_run = tk.BooleanVar(value=False)
        self.extra_ext_var = tk.StringVar()

        self.chip_vars: dict[str, tk.BooleanVar] = {}
        self.chips: list[Chip] = []
        self.keep_copies_check: NeonCheck | None = None
        self.separator_entry: tk.Entry | None = None
        self.min_entry: tk.Entry | None = None
        self.max_entry: tk.Entry | None = None
        self.counters: dict[str, tk.Label] = {}

        self._configure_window()
        self._build_ui()
        self._sync_dependent_state()
        self._pump_messages()

    # -- window ------------------------------------------------------------

    def _configure_window(self) -> None:
        self.root.title("GISCO // GIS file collector")
        self.root.configure(bg=Palette.BG)
        self.root.geometry("1240x900")
        self.root.minsize(1020, 760)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _glow_title(self, parent, text: str, accent: str, size: int) -> tk.Frame:
        font = tkfont.Font(family=MONO_FONT, size=size, weight="bold")
        holder = tk.Frame(
            parent,
            bg=Palette.BG,
            width=font.measure(text) + 8,
            height=font.metrics("linespace") + 8,
        )
        holder.pack_propagate(False)
        for dx, dy, blend in ((3, 0, 0.25), (-3, 0, 0.25), (0, 3, 0.25), (0, -3, 0.25), (0, 0, 0.45)):
            tk.Label(
                holder,
                text=text,
                bg=Palette.BG,
                fg=mix(Palette.BG, accent, blend),
                font=mono_font(size, "bold"),
            ).place(x=dx + 2, y=dy + 2)
        tk.Label(
            holder,
            text=text,
            bg=Palette.BG,
            fg=mix(accent, "#ffffff", 0.55),
            font=mono_font(size, "bold"),
        ).place(x=2, y=2)
        return holder

    # -- layout ------------------------------------------------------------

    def _build_ui(self) -> None:
        main = tk.Frame(self.root, bg=Palette.BG, padx=18, pady=14)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1)

        # Header
        header = tk.Frame(main, bg=Palette.BG)
        header.grid(row=0, column=0, sticky="ew")
        title_row = tk.Frame(header, bg=Palette.BG)
        title_row.pack(fill=tk.X)
        self._glow_title(title_row, "GISCO", Palette.CYAN, 30).pack(side=tk.LEFT, padx=(0, 14))
        tk.Label(
            title_row,
            text="// GIS FILE COLLECTOR",
            bg=Palette.BG,
            fg=Palette.MAGENTA,
            font=mono_font(12, "bold"),
        ).pack(side=tk.LEFT, pady=(14, 0))
        tk.Label(
            header,
            text="shapefiles · file gdb · cad · geopackage · geojson transform",
            bg=Palette.BG,
            fg=Palette.MUTED,
            font=ui_font(9),
        ).pack(anchor="w", pady=(0, 8))
        NeonHeaderBar(header).pack(fill=tk.X, pady=(0, 12))

        # Paths
        paths = GlowCard(main, "Source & destination", Palette.CYAN)
        paths.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._path_row(paths.content, "Source folder", self.source_var, self._browse_source)
        self._path_row(paths.content, "Destination folder", self.dest_var, self._browse_dest)

        # Middle: formats + options
        middle = tk.Frame(main, bg=Palette.BG)
        middle.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        middle.columnconfigure(0, weight=3, uniform="mid")
        middle.columnconfigure(1, weight=2, uniform="mid")

        formats = GlowCard(middle, "GIS file types", Palette.VIOLET)
        formats.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self._build_format_panel(formats.content)

        right = tk.Frame(middle, bg=Palette.BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        filters = GlowCard(right, "Filters", Palette.CYAN)
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._build_filters(filters.content)

        behaviour = GlowCard(right, "Behaviour", Palette.MAGENTA)
        behaviour.grid(row=1, column=0, sticky="ew")
        self._build_behaviour(behaviour.content)

        # Actions
        actions = tk.Frame(main, bg=Palette.BG)
        actions.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.start_button = NeonButton(
            actions, "▶  START COLLECT", self._start, accent=Palette.LIME, solid=True
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        self.stop_button = NeonButton(actions, "■  STOP", self._stop, accent=Palette.RED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        NeonButton(actions, "CLEAR LOG", self._clear_log, accent=Palette.MUTED).pack(side=tk.LEFT)

        self.progress = NeonProgress(actions)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(18, 0))

        # Log
        log_card = GlowCard(main, "Console", Palette.LIME)
        log_card.grid(row=4, column=0, sticky="nsew")
        self._build_log(log_card.content)

        # Status bar
        status = tk.Frame(main, bg=Palette.BG)
        status.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        for key, accent in (
            ("copied", Palette.CYAN),
            ("converted", Palette.LIME),
            ("skipped", Palette.AMBER),
            ("failed", Palette.RED),
        ):
            tk.Label(
                status,
                text=key.upper(),
                bg=Palette.BG,
                fg=Palette.MUTED,
                font=mono_font(8),
            ).pack(side=tk.LEFT, padx=(0, 4))
            value = tk.Label(status, text="0", bg=Palette.BG, fg=accent, font=mono_font(9, "bold"))
            value.pack(side=tk.LEFT, padx=(0, 16))
            self.counters[key] = value

        self.state_var = tk.StringVar(value="IDLE")
        tk.Label(
            status,
            textvariable=self.state_var,
            bg=Palette.BG,
            fg=Palette.MAGENTA,
            font=mono_font(9, "bold"),
        ).pack(side=tk.RIGHT)

        self.stop_button.set_enabled(False)

    def _path_row(self, parent, label: str, variable: tk.StringVar, browse) -> None:
        row = tk.Frame(parent, bg=Palette.PANEL)
        row.pack(fill=tk.X, pady=3)
        tk.Label(
            row, text=label.upper(), bg=Palette.PANEL, fg=Palette.MUTED, font=mono_font(8), width=18, anchor="w"
        ).pack(side=tk.LEFT)
        entry = styled_entry(row, variable)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        NeonButton(row, "BROWSE", browse, accent=Palette.VIOLET, font=mono_font(8, "bold")).pack(side=tk.LEFT)

    def _build_format_panel(self, parent) -> None:
        wrapper = tk.Frame(parent, bg=Palette.PANEL)
        wrapper.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(wrapper, bg=Palette.PANEL, highlightthickness=0, bd=0, height=214)
        scroll = NeonScrollbar(wrapper, command=canvas.yview, accent=Palette.VIOLET)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=Palette.PANEL)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))

        self.formats_panel = wrapper
        wrapper.bind("<Enter>", self._bind_wheel)
        wrapper.bind("<Leave>", self._unbind_wheel)
        self._formats_canvas = canvas

        accents = {"Vector": Palette.CYAN, "Rasters": Palette.AMBER, "Projects & layers": Palette.MAGENTA}
        for category, entries in FORMAT_CHIPS:
            accent = accents.get(category, Palette.CYAN)
            header = tk.Frame(inner, bg=Palette.PANEL)
            header.pack(fill=tk.X, pady=(8, 3))
            tk.Label(
                header, text=category.upper(), bg=Palette.PANEL, fg=accent, font=mono_font(8, "bold")
            ).pack(side=tk.LEFT)
            group_vars = []
            for key, _label, _extensions, default_on in entries:
                variable = self.chip_vars.setdefault(key, tk.BooleanVar(value=default_on))
                group_vars.append(variable)
            for text, state in (("NONE", False), ("ALL", True)):
                link = tk.Label(
                    header,
                    text=text,
                    bg=Palette.PANEL,
                    fg=Palette.MUTED,
                    font=mono_font(7, "bold"),
                    cursor="hand2",
                )
                link.pack(side=tk.RIGHT, padx=(6, 0))
                link.bind("<Button-1>", lambda _event, v=group_vars, s=state: [var.set(s) for var in v])
                link.bind("<Enter>", lambda event: event.widget.configure(fg=accent))
                link.bind("<Leave>", lambda event: event.widget.configure(fg=Palette.MUTED))

            grid = tk.Frame(inner, bg=Palette.PANEL)
            grid.pack(fill=tk.X)
            chips = []
            for key, label, _extensions, _default_on in entries:
                chip = Chip(grid, label, self.chip_vars[key], accent, Palette.PANEL)
                chips.append(chip)
                self.chips.append(chip)
            self._make_flow(grid, chips, accent)

        extra = tk.Frame(inner, bg=Palette.PANEL)
        extra.pack(fill=tk.X, pady=(10, 4))
        tk.Label(
            extra,
            text="EXTRA EXTENSIONS",
            bg=Palette.PANEL,
            fg=Palette.MUTED,
            font=mono_font(8),
        ).pack(side=tk.LEFT, padx=(0, 8))
        styled_entry(extra, self.extra_ext_var).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        tk.Label(
            inner,
            text="comma separated, e.g.  laz, dwg, gpkg",
            bg=Palette.PANEL,
            fg=mix(Palette.MUTED, Palette.BG, 0.25),
            font=ui_font(8),
        ).pack(anchor="w")

    def _make_flow(self, grid: tk.Frame, chips: list[Chip], accent: str) -> None:
        state = {"columns": 0}

        def reflow(event=None):
            width = event.width if event is not None else grid.winfo_width()
            columns = max(1, (max(width, 1) + 4) // 128)
            if columns == state["columns"]:
                return
            previous = state["columns"]
            state["columns"] = columns
            for index, chip in enumerate(chips):
                chip.grid(row=index // columns, column=index % columns, sticky="ew", padx=2, pady=2)
            for column in range(max(previous, columns)):
                grid.columnconfigure(
                    column, weight=1 if column < columns else 0, uniform=f"chip{accent}"
                )

        grid.bind("<Configure>", reflow)
        reflow()

    def _build_filters(self, parent) -> None:
        size_row = tk.Frame(parent, bg=Palette.PANEL)
        size_row.pack(fill=tk.X, pady=(2, 2))
        NeonCheck(
            size_row,
            "File size filter — every GIS format",
            self.size_filter_enabled,
            accent=Palette.AMBER,
            command=self._sync_dependent_state,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        bounds = tk.Frame(parent, bg=Palette.PANEL)
        bounds.pack(fill=tk.X, pady=(0, 4), padx=(24, 0))
        tk.Label(
            bounds, text="MIN", bg=Palette.PANEL, fg=Palette.AMBER, font=mono_font(8, "bold"), width=4, anchor="w"
        ).pack(side=tk.LEFT)
        self.min_entry = styled_entry(bounds, self.min_size_value, width=8)
        self.min_entry.pack(side=tk.LEFT, ipady=3)
        tk.Label(bounds, text="MB", bg=Palette.PANEL, fg=Palette.AMBER, font=mono_font(8, "bold")).pack(
            side=tk.LEFT, padx=(5, 14)
        )
        tk.Label(
            bounds, text="MAX", bg=Palette.PANEL, fg=Palette.AMBER, font=mono_font(8, "bold"), width=4, anchor="w"
        ).pack(side=tk.LEFT)
        self.max_entry = styled_entry(bounds, self.max_size_value, width=8)
        self.max_entry.pack(side=tk.LEFT, ipady=3)
        tk.Label(bounds, text="MB", bg=Palette.PANEL, fg=Palette.AMBER, font=mono_font(8, "bold")).pack(
            side=tk.LEFT, padx=(5, 10)
        )
        tk.Label(
            bounds, text="0 = no limit", bg=Palette.PANEL, fg=mix(Palette.MUTED, Palette.BG, 0.2), font=ui_font(8)
        ).pack(side=tk.LEFT)

        tk.Label(
            parent,
            text="shapefile datasets are sized shp+shx+dbf+prj+…, other formats use their own size",
            bg=Palette.PANEL,
            fg=mix(Palette.MUTED, Palette.BG, 0.25),
            font=ui_font(8),
        ).pack(anchor="w", padx=(24, 0), pady=(0, 6))

        kw_row = tk.Frame(parent, bg=Palette.PANEL)
        kw_row.pack(fill=tk.X, pady=(4, 6))
        tk.Label(
            kw_row, text="KEYWORDS", bg=Palette.PANEL, fg=Palette.MUTED, font=mono_font(8), width=12, anchor="w"
        ).pack(side=tk.LEFT)
        styled_entry(kw_row, self.keywords_var).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        sep_row = tk.Frame(parent, bg=Palette.PANEL)
        sep_row.pack(fill=tk.X, pady=(2, 0))
        tk.Label(
            sep_row,
            text="FLATTEN SEPARATOR",
            bg=Palette.PANEL,
            fg=Palette.MUTED,
            font=mono_font(8),
            width=20,
            anchor="w",
        ).pack(side=tk.LEFT)
        self.separator_entry = styled_entry(sep_row, self.separator_var, width=8)
        self.separator_entry.pack(side=tk.LEFT, ipady=3)
        tk.Label(
            sep_row, text="used to prefix folder paths", bg=Palette.PANEL, fg=Palette.MUTED, font=ui_font(8)
        ).pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(
            parent,
            text="keyword match is case-insensitive on the file stem",
            bg=Palette.PANEL,
            fg=mix(Palette.MUTED, Palette.BG, 0.25),
            font=ui_font(8),
        ).pack(anchor="w", pady=(4, 0))

    def _build_behaviour(self, parent) -> None:
        NeonCheck(
            parent,
            "Preserve folder tree",
            self.preserve_tree,
            accent=Palette.MAGENTA,
            command=self._sync_dependent_state,
        ).pack(anchor="w")
        tk.Label(
            parent,
            text="unchecked → everything flattened into the destination root",
            bg=Palette.PANEL,
            fg=Palette.MUTED,
            font=ui_font(8),
        ).pack(anchor="w", padx=(24, 0), pady=(0, 8))

        self.convert_check = NeonCheck(
            parent,
            "Transform selected to GeoJSON (EPSG:4326)",
            self.convert_geojson,
            accent=Palette.LIME,
            command=self._sync_dependent_state,
        )
        self.convert_check.pack(anchor="w")
        if not self.geojson_ready:
            self.convert_check.set_enabled(False)
            tk.Label(
                parent,
                text="geopandas + pyogrio not importable in this interpreter",
                bg=Palette.PANEL,
                fg=Palette.RED,
                font=ui_font(8),
            ).pack(anchor="w", padx=(24, 0))

        self.keep_copies_check = NeonCheck(
            parent,
            "Keep original files (write .geojson alongside)",
            self.keep_originals,
            accent=Palette.LIME,
            command=self._sync_dependent_state,
        )
        self.keep_copies_check.pack(anchor="w", padx=(24, 0), pady=(2, 8))

        NeonCheck(parent, "Dry run — plan only, write nothing", self.dry_run, accent=Palette.AMBER).pack(anchor="w")

    def _build_log(self, parent) -> None:
        holder = tk.Frame(parent, bg=Palette.PANEL)
        holder.pack(fill=tk.BOTH, expand=True)
        self.log = tk.Text(
            holder,
            wrap=tk.WORD,
            font=mono_font(9),
            bg=Palette.BG_SOFT,
            fg=Palette.TEXT,
            insertbackground=Palette.CYAN,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=8,
            state=tk.DISABLED,
        )
        scroll = NeonScrollbar(holder, command=self.log.yview, accent=Palette.LIME)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        self.log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.log.tag_configure("stamp", foreground=mix(Palette.MUTED, Palette.BG, 0.3))
        self.log.tag_configure("info", foreground="#9fdcff")
        self.log.tag_configure("path", foreground="#c9a6ff")
        self.log.tag_configure("success", foreground=Palette.LIME)
        self.log.tag_configure("warning", foreground=Palette.AMBER)
        self.log.tag_configure("error", foreground=Palette.RED)
        self.log.tag_configure("header", foreground=Palette.MAGENTA, font=mono_font(9, "bold"))

    # -- helpers -----------------------------------------------------------

    def _bind_wheel(self, _event=None) -> None:
        if not self._wheel_bound:
            self.root.bind_all("<MouseWheel>", self._on_wheel)
            self._wheel_bound = True

    def _unbind_wheel(self, _event=None) -> None:
        x, y = self.root.winfo_pointerxy()
        widget = self.root.winfo_containing(x, y)
        inside = widget is not None and str(widget).startswith(str(self.formats_panel))
        if inside or not self._wheel_bound:
            return
        self.root.unbind_all("<MouseWheel>")
        self._wheel_bound = False

    def _on_wheel(self, event) -> None:
        direction = -1 if event.delta > 0 else 1
        self._formats_canvas.yview_scroll(direction, "units")

    def _append_log(self, message: str, level: str = "info") -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state=tk.NORMAL)
        if int(self.log.index("end-1c").split(".")[0]) > 4000:
            self.log.delete("1.0", "500.0")
        self.log.insert(tk.END, f"{stamp}  ", "stamp")
        self.log.insert(tk.END, f"{message}\n", level)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

    def _browse_source(self) -> None:
        folder = filedialog.askdirectory(title="Select the folder to scan")
        if not folder:
            return
        self.source_var.set(folder)
        if not self.dest_var.get().strip() or self.dest_var.get() == "_gis_everything":
            self.dest_var.set(os.path.join(folder, "_gis_everything"))

    def _browse_dest(self) -> None:
        folder = filedialog.askdirectory(title="Select the destination folder")
        if folder:
            self.dest_var.set(folder)

    @staticmethod
    def _parse_megabytes(raw: str, label: str) -> float:
        text = raw.strip().replace(",", ".")
        if not text:
            return 0.0
        try:
            value = float(text)
        except ValueError as exc:
            raise GiscoError(f"{label} size must be a number in MB (0 = no limit).") from exc
        if value < 0:
            raise GiscoError(f"{label} size cannot be negative.")
        return value

    def _sync_dependent_state(self) -> None:
        transform = self.convert_geojson.get() and self.geojson_ready
        if self.keep_copies_check is not None:
            self.keep_copies_check.set_enabled(transform)
        if self.separator_entry is not None:
            state = tk.DISABLED if self.preserve_tree.get() else tk.NORMAL
            self.separator_entry.configure(state=state)
        size_state = tk.NORMAL if self.size_filter_enabled.get() else tk.DISABLED
        for entry in (self.min_entry, self.max_entry):
            if entry is not None:
                entry.configure(state=size_state)

    def _collect_options(self) -> CopyOptions:
        extensions = {
            ext
            for key, variable in self.chip_vars.items()
            if variable.get()
            for ext in CHIP_EXTENSIONS.get(key, ())
        }

        extra = [
            token.strip().lstrip(".").lower()
            for token in self.extra_ext_var.get().split(",")
            if token.strip()
        ]
        extensions |= set(extra)

        keywords = [token.strip() for token in self.keywords_var.get().split(",") if token.strip()]

        min_mb = 0.0
        max_mb = 0.0
        if self.size_filter_enabled.get():
            min_mb = self._parse_megabytes(self.min_size_value.get(), "Min")
            max_mb = self._parse_megabytes(self.max_size_value.get(), "Max")
            if min_mb and max_mb and min_mb > max_mb:
                raise GiscoError("Min size must be lower than max size.")

        include_gdb = bool(self.chip_vars["gdb"].get()) if "gdb" in self.chip_vars else False
        if not extensions and not include_gdb:
            raise GiscoError("Select at least one GIS file type.")

        transform = self.convert_geojson.get()
        if transform and not self.geojson_ready:
            raise GiscoError(
                "GeoJSON transform is unavailable: geopandas and pyogrio must be importable."
            )

        return CopyOptions(
            source=self.source_var.get().strip().strip('"'),
            dest=self.dest_var.get().strip().strip('"'),
            extensions=extensions,
            include_gdb=include_gdb,
            keywords=keywords,
            min_size_mb=min_mb,
            max_size_mb=max_mb,
            preserve_tree=self.preserve_tree.get(),
            separator=self.separator_var.get() or "__",
            convert_geojson=transform,
            keep_originals=self.keep_originals.get(),
            dry_run=self.dry_run.get(),
        )

    # -- run lifecycle ------------------------------------------------------

    def _start(self) -> None:
        if self.running:
            return
        try:
            options = self._collect_options()
        except GiscoError as exc:
            messagebox.showwarning("GISCO", str(exc))
            return

        if not options.source:
            messagebox.showwarning("GISCO", "Choose a source folder.")
            return
        if not os.path.isdir(options.source):
            messagebox.showerror("GISCO", f"'{options.source}' is not a valid directory.")
            return
        if not options.dest:
            messagebox.showwarning("GISCO", "Choose a destination folder.")
            return

        self.stop_event.clear()
        self.progress.set(0)
        for label in self.counters.values():
            label.configure(text="0")
        self._set_running(True)
        self.state_var.set("SCANNING")
        self._append_log("─" * 58, "header")
        self._append_log(
            f"START — {'DRY RUN' if options.dry_run else 'COPY'} · "
            f"{'tree preserved' if options.preserve_tree else 'flattened'}"
            + (" · geojson transform" if options.convert_geojson else ""),
            "header",
        )

        self.worker = threading.Thread(target=self._run_worker, args=(options,), daemon=True)
        self.worker.start()

    def _run_worker(self, options: CopyOptions) -> None:
        def log(message: str, level: str = "info") -> None:
            self.messages.put(("log", message, level))

        def progress(done: int, total: int) -> None:
            self.messages.put(("progress", done, total))

        try:
            stats = run_job(
                options,
                on_log=log,
                on_progress=progress,
                should_stop=self.stop_event.is_set,
            )
        except GiscoError as exc:
            self.messages.put(("error", str(exc), "error"))
            return
        except Exception as exc:  # pragma: no cover - defensive
            self.messages.put(("error", f"Unexpected error: {exc}", "error"))
            return
        self.messages.put(("done", stats, "info"))

    def _stop(self) -> None:
        if not self.running:
            return
        self.stop_event.set()
        self.state_var.set("STOPPING")
        self._append_log("Stop requested — finishing the current dataset…", "warning")

    def _pump_messages(self) -> None:
        try:
            while True:
                kind, payload, extra = self.messages.get_nowait()
                # A UI hiccup must never kill the poller and leave the buttons locked
                try:
                    if kind == "log":
                        self._append_log(payload, extra)
                    elif kind == "progress":
                        done, total = payload, extra
                        self.progress.set(done / total if total else 0)
                        self.state_var.set(f"RUNNING {done}/{total}")
                    elif kind == "done":
                        stats: Stats = payload
                        stopped = self.stop_event.is_set()
                        self.counters["copied"].configure(text=str(stats.files + stats.gdbs))
                        self.counters["converted"].configure(text=str(stats.converted))
                        self.counters["skipped"].configure(text=str(stats.skipped))
                        self.counters["failed"].configure(text=str(stats.failed))
                        if not stopped:
                            self.progress.set(1)
                        self._set_running(False)
                        if stopped:
                            self.state_var.set("STOPPED")
                        else:
                            self.state_var.set("DONE" if stats.failed == 0 else "DONE WITH ERRORS")
                        self._append_log("─" * 58, "header")
                    elif kind == "error":
                        self._append_log(payload, "error")
                        self._set_running(False)
                        self.state_var.set("ERROR")
                except tk.TclError:
                    raise
                except Exception as exc:
                    try:
                        self._append_log(f"UI warning while handling '{kind}': {exc}", "error")
                    except tk.TclError:
                        raise
        except queue.Empty:
            pass
        except tk.TclError:
            return
        try:
            self.root.after(60, self._pump_messages)
        except tk.TclError:
            return

    def _set_running(self, running: bool) -> None:
        self.running = running
        self.start_button.set_enabled(not running)
        self.stop_button.set_enabled(running)

    def _on_close(self) -> None:
        self.stop_event.set()
        try:
            self.root.destroy()
        except tk.TclError:
            pass


def _prepare_fonts(root: tk.Tk) -> None:
    global UI_FONT, MONO_FONT
    families = set(tkfont.families(root))
    for candidate in ("Segoe UI Variable Text", "Segoe UI", "Tahoma"):
        if candidate in families:
            UI_FONT = candidate
            break
    for candidate in ("Cascadia Mono", "Cascadia Code", "Consolas", "Courier New"):
        if candidate in families:
            MONO_FONT = candidate
            break


def main() -> None:
    if os.name == "nt":
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    root = tk.Tk()
    _prepare_fonts(root)
    GiscoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

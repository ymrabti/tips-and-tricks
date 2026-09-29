import os
import shutil
import sys
import argparse

# Vector data + shapefile sidecar files
VECTOR_EXTENSIONS = {
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

# Extensions made of two parts; must be checked before os.path.splitext
COMPOUND_EXTENSIONS = (".shp.xml", ".aux.xml")


def make_long_path_safe(path):
    """Prepend the Windows extended path prefix to bypass the 260 char limit."""
    abs_path = os.path.abspath(path)
    if os.name == "nt" and not abs_path.startswith("\\\\?\\"):
        return "\\\\?\\" + abs_path
    return abs_path


def split_name(filename):
    """Split into (stem, extension-with-dot), handling compound extensions."""
    lower = filename.lower()
    for comp in COMPOUND_EXTENSIONS:
        if lower.endswith(comp):
            return filename[: -len(comp)], comp
    stem, ext = os.path.splitext(filename)
    return stem, ext.lower()


def build_breadcrumb_prefix(root, source_dir_abs, separator):
    rel = os.path.relpath(root, source_dir_abs)
    if rel == ".":
        return ""
    return separator.join(rel.split(os.sep)) + separator


def copy_gis_files(
    source_dir,
    dest_folder="_gis_everything",
    keywords=None,
    breadcrumb=False,
    separator="__",
    dry_run=False,
    include_rasters=False,
):
    if not os.path.exists(source_dir):
        print(f"Error: The source folder '{source_dir}' does not exist.")
        sys.exit(1)
    if not os.path.isdir(source_dir):
        print(f"Error: '{source_dir}' is not a directory.")
        sys.exit(1)

    allowed = set(VECTOR_EXTENSIONS) | set(PROJECT_EXTENSIONS)
    if include_rasters:
        allowed |= RASTER_EXTENSIONS

    keyword_set = [kw.lower() for kw in keywords] if keywords else []
    tag = "[DRY RUN] " if dry_run else ""

    source_dir_abs = os.path.abspath(source_dir)
    dest_abs = os.path.abspath(dest_folder)
    dest_safe = make_long_path_safe(dest_folder)

    if not os.path.exists(dest_safe):
        if dry_run:
            print(f"{tag}Would create destination folder: {dest_folder}")
        else:
            os.makedirs(dest_safe)
            print(f"Created destination folder: {dest_folder}")

    planned = set()
    stats = {"files": 0, "gdbs": 0, "failed": 0}

    def is_taken(name):
        full = os.path.join(dest_safe, name)
        return os.path.exists(full) or os.path.normcase(full) in planned

    def reserve(name):
        planned.add(os.path.normcase(os.path.join(dest_safe, name)))

    def keyword_ok(stem):
        if not keyword_set:
            return True
        s = stem.lower()
        return any(kw in s for kw in keyword_set)

    for root, dirs, files in os.walk(source_dir_abs):
        # Never walk into the destination folder (even if nested in the source)
        dirs[:] = [
            d for d in dirs if os.path.abspath(os.path.join(root, d)) != dest_abs
        ]

        prefix = (
            build_breadcrumb_prefix(root, source_dir_abs, separator)
            if breadcrumb
            else ""
        )

        # --- File geodatabases (.gdb folders) are copied whole ---
        for d in list(dirs):
            if not d.lower().endswith(".gdb"):
                continue
            dirs.remove(d)  # don't descend into internal .gdbtable etc.
            gdb_stem = d[:-4]
            if not keyword_ok(gdb_stem):
                continue
            counter = 0
            out_name = f"{prefix}{d}"
            while is_taken(out_name):
                counter += 1
                out_name = f"{prefix}{gdb_stem}_{counter}.gdb"
            reserve(out_name)
            src = os.path.join(root, d)
            shown = os.path.join(dest_folder, out_name)
            if dry_run:
                print(f"{tag}Would copy GDB: {src} -> {shown}")
                stats["gdbs"] += 1
                continue
            try:
                shutil.copytree(
                    make_long_path_safe(src), os.path.join(dest_safe, out_name)
                )
                print(f"Copied GDB: {src} -> {shown}")
                stats["gdbs"] += 1
            except Exception as e:
                print(f"Failed to copy GDB {d}: {e}")
                stats["failed"] += 1

        # --- Group files by stem so shapefile parts stay together ---
        groups = {}
        for f in files:
            stem, ext = split_name(f)
            if ext.lstrip(".") not in allowed:
                continue
            if not keyword_ok(stem):
                continue
            groups.setdefault(stem.lower(), []).append((f, stem, ext))

        for members in groups.values():
            # One suffix for the whole group so ro.shp/.shx/.dbf/.prj share a name
            counter = 0
            suffix = ""
            while any(
                is_taken(f"{prefix}{stem}{suffix}{ext}") for _, stem, ext in members
            ):
                counter += 1
                suffix = f"_{counter}"

            for f, stem, ext in members:
                out_name = f"{prefix}{stem}{suffix}{ext}"
                reserve(out_name)
                src = os.path.join(root, f)
                shown = os.path.join(dest_folder, out_name)
                if dry_run:
                    print(f"{tag}Would copy: {src} -> {shown}")
                    stats["files"] += 1
                    continue
                try:
                    shutil.copy2(
                        make_long_path_safe(src), os.path.join(dest_safe, out_name)
                    )
                    print(f"Copied: {src} -> {shown}")
                    stats["files"] += 1
                except Exception as e:
                    print(f"Failed to copy {f}: {e}")
                    stats["failed"] += 1

    verb = "would be copied" if dry_run else "copied"
    print(
        f"\n{tag}{stats['files']} file(s) and {stats['gdbs']} geodatabase(s) {verb}, "
        f"{stats['failed']} failed." + (" Nothing was changed." if dry_run else "")
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recursively copy only GIS files (shapefiles, dwg, gpkg, kml/kmz, "
        "lyr, sd, .gdb, ...) into a single folder."
    )
    parser.add_argument("input_folder", help="Path to the input folder to scan")
    parser.add_argument(
        "-o",
        "--dest",
        default="_gis_everything",
        help="Destination folder (default: _gis_everything)",
    )
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        default=[],
        help="Keywords to match in file names (optional)",
    )
    parser.add_argument(
        "--bread-cumb",
        "--breadcrumb",
        dest="breadcrumb",
        action="store_true",
        help="Prefix copied names with their relative folder path",
    )
    parser.add_argument(
        "--separator",
        default="__",
        help="Separator for the breadcrumb prefix (default: '__')",
    )
    parser.add_argument(
        "--include-rasters",
        action="store_true",
        help="Also copy rasters and point clouds (tif, img, ecw, jp2, las, ...)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without copying anything",
    )

    args = parser.parse_args()
    copy_gis_files(
        args.input_folder,
        dest_folder=args.dest,
        keywords=args.keywords,
        breadcrumb=args.breadcrumb,
        separator=args.separator,
        dry_run=args.dry_run,
        include_rasters=args.include_rasters,
    )

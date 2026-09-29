import os
import shutil
import sys
import argparse

# Define the set of allowed file extensions (lowercase for consistent matching)
ALLOWED_EXTENSIONS = {
    "pdf",
    "txt",
    "md",
    "docx",
    "csv",
    "pptx",
    "jp2",
    "png",
    "webp",
    "tif",
    "tiff",
    "heic",
    "heif",
    "jpeg",
    "jpg",
    "jpe",
    "xls",
    "ppt",
    "doc",
    "xlsx",
}


def make_long_path_safe(path):
    """
    Prepends the Windows extended path prefix if on Windows to bypass
    the 256 character path length restriction.
    """
    abs_path = os.path.abspath(path)
    if os.name == "nt" and not abs_path.startswith("\\\\?\\"):
        return "\\\\?\\" + abs_path
    return abs_path


def build_breadcrumb_prefix(root, source_dir_abs, separator):
    """
    Returns a prefix built from the folders between the input top folder
    and the current folder, e.g. 'sub1__sub2__'. Files directly inside the
    top folder get an empty prefix.
    """
    rel = os.path.relpath(root, source_dir_abs)
    if rel == ".":
        return ""
    return separator.join(rel.split(os.sep)) + separator


def copy_files_to_everything(
    source_dir,
    keywords=None,
    dest_folder="_everything",
    breadcrumb=False,
    separator="__",
    dry_run=False,
):
    """
    Iterates through the source folder, filters for supported file extensions,
    optionally matches keywords, and copies them into a single destination folder.
    If breadcrumb is True, each copied file name is prefixed with its relative
    folder path (from source_dir), joined by `separator`.
    If dry_run is True, nothing is created or copied; actions are only printed.
    """
    # Verify the source directory exists
    if not os.path.exists(source_dir):
        print(f"Error: The source folder '{source_dir}' does not exist.")
        sys.exit(1)

    if not os.path.isdir(source_dir):
        print(f"Error: '{source_dir}' is not a directory.")
        sys.exit(1)

    tag = "[DRY RUN] " if dry_run else ""

    # Convert keywords to lowercase for case-insensitive matching
    keyword_set = [kw.lower() for kw in keywords] if keywords else []

    # Get absolute paths and apply long path safe fixes
    source_dir_abs = os.path.abspath(source_dir)
    dest_folder_safe = make_long_path_safe(dest_folder)

    # Create the destination folder if it doesn't exist
    if not os.path.exists(dest_folder_safe):
        if dry_run:
            print(f"{tag}Would create destination folder: {dest_folder}")
        else:
            os.makedirs(dest_folder_safe)
            print(f"Created destination folder: {dest_folder}")

    # Destination paths already used (or planned, in dry-run mode)
    planned = set()
    copied_count = 0
    failed_count = 0

    def is_taken(path):
        return os.path.exists(path) or os.path.normcase(path) in planned

    # Walk through the source directory recursively
    for root, dirs, files in os.walk(source_dir_abs):
        # Skip the destination folder itself if it's nested inside the source directory
        if os.path.abspath(root) == os.path.abspath(dest_folder_safe).replace(
            "\\\\?\\", ""
        ):
            continue

        prefix = (
            build_breadcrumb_prefix(root, source_dir_abs, separator)
            if breadcrumb
            else ""
        )

        for file in files:
            # Extract the extension and check if it is supported
            _, ext = os.path.splitext(file)
            ext_lower = ext.lstrip(".").lower()

            if ext_lower not in ALLOWED_EXTENSIONS:
                continue  # Skip unsupported file types

            # Keyword filter (matches on the original file name only)
            if keyword_set:
                file_lower = file.lower()
                if not any(kw in file_lower for kw in keyword_set):
                    continue

            # Final destination name, with optional breadcrumb prefix
            out_name = prefix + file
            out_base, out_ext = os.path.splitext(out_name)

            source_path = make_long_path_safe(os.path.join(root, file))
            dest_path = make_long_path_safe(os.path.join(dest_folder_safe, out_name))

            # Handle duplicate file names by appending a suffix
            if is_taken(dest_path):
                counter = 1
                while is_taken(dest_path):
                    dest_path = make_long_path_safe(
                        os.path.join(dest_folder_safe, f"{out_base}_{counter}{out_ext}")
                    )
                    counter += 1

            planned.add(os.path.normcase(dest_path))
            shown_dest = os.path.join(dest_folder, os.path.basename(dest_path))

            if dry_run:
                print(f"{tag}Would copy: {os.path.join(root, file)} -> {shown_dest}")
                copied_count += 1
                continue

            try:
                shutil.copy2(source_path, dest_path)
                print(f"Copied: {os.path.join(root, file)} -> {shown_dest}")
                copied_count += 1
            except Exception as e:
                print(f"Failed to copy {file}: {e}")
                failed_count += 1

    # Summary
    if dry_run:
        print(f"\n{tag}{copied_count} file(s) would be copied. Nothing was changed.")
    else:
        print(f"\nDone: {copied_count} file(s) copied, {failed_count} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recursively copy specific file types into an _everything folder with optional keyword matching."
    )

    parser.add_argument("input_folder", help="Path to the input folder to scan")
    parser.add_argument(
        "-k",
        "--keywords",
        nargs="+",
        help="Keywords to search for in filenames (optional)",
        default=[],
    )
    parser.add_argument(
        "--bread-cumb",
        "--breadcrumb",
        dest="breadcrumb",
        action="store_true",
        help="Prefix copied file names with their relative folder path from the input folder",
    )
    parser.add_argument(
        "--separator",
        default="__",
        help="Separator used between folder names in the breadcrumb prefix (default: '__')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be copied without creating folders or copying files",
    )

    args = parser.parse_args()

    copy_files_to_everything(
        args.input_folder,
        keywords=args.keywords,
        breadcrumb=args.breadcrumb,
        separator=args.separator,
        dry_run=args.dry_run,
    )

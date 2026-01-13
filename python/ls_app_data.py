import os
from pathlib import Path

THRESHOLD_MB = 50
THRESHOLD_BYTES = THRESHOLD_MB * 1024 * 1024


def folder_size_recursive(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path, onerror=lambda e: None):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except (PermissionError, FileNotFoundError):
                pass
    return total


def format_size(bytes_size: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} PB"


def main():
    local_appdata = Path(os.environ["LOCALAPPDATA"])

    results = []
    large_folders_total = 0

    for entry in local_appdata.iterdir():
        if entry.is_dir():
            size = folder_size_recursive(entry)
            results.append((entry.name, size))

            if size >= THRESHOLD_BYTES:
                large_folders_total += size

    results.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Folder':40} {'Total Size':>15}")
    print("-" * 58)

    for name, size in results:
        print(f"{name:40} {format_size(size):>15}")

    print("\n" + "-" * 58)
    print(
        f"Sum of folders >= {THRESHOLD_MB} MB:" f" {format_size(large_folders_total)}"
    )


if __name__ == "__main__":
    main()

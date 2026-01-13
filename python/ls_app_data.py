import os
from pathlib import Path

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

    for entry in local_appdata.iterdir():
        if entry.is_dir():  # ONLY first-level folders
            size = folder_size_recursive(entry)
            results.append((entry.name, size))

    results.sort(key=lambda x: x[1], reverse=True)

    print(f"{'Folder':40} {'Total Size':>15}")
    print("-" * 58)

    for name, size in results:
        print(f"{name:40} {format_size(size):>15}")


if __name__ == "__main__":
    main()

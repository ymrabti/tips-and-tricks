"""dcf"""

from fnmatch import fnmatch
import os
import shutil

PROJECTS_DIRECTORY = "C:/Users/youmt/youmtinet"


def remove_node_modules(directory, dry_run=False):
    """shcdg"""
    dir_patterns = [
        "node_modules",
        ".vscode-test",
        ".dart_tool",
        "build",
        "Generated.xcconfig",
        "flutter_export_environment.sh",
        "ephemeral",
        ".flutter-plugins-dependencies",
        ".flutter-plugins",
        ".gradle",
        ".yarn",
        ".next",
        ".angular",
        "node_modules",
        "dist",
        "build",
        "coverage",
        ".cache",
        ".npm",
        ".yarn",
        ".nx",
        ".turbo",
        ".vite",
        ".parcel-cache",
        ".eslintcache",
        ".next",
        ".angular",
        ".dart_tool",
        ".pub-cache",
        ".packages",
        ".ephemeral",
        ".flutter-plugins",
        ".flutter-plugins-dependencies",
        "flutter_export_environment.sh",
        "Generated.xcconfig",
        ".ios",
        ".android",
        ".macos",
        ".linux",
        ".windows",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".gradle",
        "target",
        "out",
        "bin",
        "obj",
        ".vs",
        ".idea",
        ".vscode-test",
        "logs",
        "tmp",
        "temp",
        ".DS_Store",
        "Thumbs.db",
    ]
    file_patterns = [
        "*.aab",
        "*.apk",
        # ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        # "*.log",
        # "*.log.*",
        "npm-debug.log",
        "yarn-error.log",
        "pnpm-debug.log",
        "lerna-debug.log",
        ".eslintcache",
        ".stylelintcache",
        ".turbo.log",
        ".npmrc.tmp",
        ".cache.json",
        "tsconfig.tsbuildinfo",
        "*.tsbuildinfo",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".python-version",
        # "flutter_export_environment.sh",
        "Generated.xcconfig",
        "GeneratedPluginRegistrant.java",
        "GeneratedPluginRegistrant.m",
        "GeneratedPluginRegistrant.swift",
        "hs_err_pid*.log",
        "replay_pid*.log",
        "coverage-final.json",
        "lcov.info",
        "test-results.xml",
        "junit.xml",
        "*.swp",
        "*.swo",
        # "*.bak",
        "*.tmp",
        "*.orig",
        "*.rej",
    ]
    for root, dirs, files in os.walk(directory, topdown=True):

        # ---- Handle directories ----
        for d in list(dirs):
            for pattern in dir_patterns:
                if fnmatch(d, pattern):
                    path = os.path.join(root, d)
                    print(f"FOLDER  {path}")

                    if not dry_run:
                        shutil.rmtree(path, ignore_errors=True)

                    # Prevent os.walk from descending into deleted dir
                    dirs.remove(d)
                    break

        # ---- Handle files ----
        for f in files:
            for pattern in file_patterns:
                if fnmatch(f, pattern):
                    path = os.path.join(root, f)
                    print(f"FILE    {path}")

                    if not dry_run:
                        try:
                            os.remove(path)
                        except OSError as e:
                            print(f"FAILED  {path} ({e})")
                    break


def count_sizes_of_patterns(directory, patterns):
    """Count total size of files matching given patterns."""
    total_size = 0
    for root, dirs, files in os.walk(directory, topdown=True):
        for f in files:
            for pattern in patterns:
                if fnmatch(f, pattern):
                    path = os.path.join(root, f)
                    total_size += os.path.getsize(path)
                    print(path)
                    break
    return total_size

# Call the function to remove node_modules folders
remove_node_modules(PROJECTS_DIRECTORY)

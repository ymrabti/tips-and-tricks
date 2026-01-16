"""Desktop application for searching and deleting files/folders by pattern."""

import os
import shutil
import threading
import tkinter as tk
from fnmatch import fnmatch
from tkinter import filedialog, messagebox, ttk


class PatternCleanerApp:
    """Main application class for the pattern-based file cleaner."""

    DIR_PATTERNS = [
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
        "dist",
        "coverage",
        ".cache",
        ".npm",
        ".nx",
        ".turbo",
        ".vite",
        ".parcel-cache",
        ".eslintcache",
        ".pub-cache",
        ".packages",
        ".ephemeral",
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
        "target",
        "out",
        "bin",
        "obj",
        ".vs",
        ".idea",
        "logs",
        "tmp",
        "temp",
        ".DS_Store",
        "Thumbs.db",
    ]

    FILE_PATTERNS = [
        "*.aab",
        "*.apk",
        "Thumbs.db",
        "desktop.ini",
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
        "*.tmp",
        "*.orig",
        "*.rej",
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("Pattern-Based File Cleaner")
        self.root.geometry("900x650")
        self.root.minsize(700, 500)

        # Configure modern styling
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Variables
        self.folder_path = tk.StringVar()
        self.dry_run = tk.BooleanVar(value=True)
        self.is_running = False
        self.should_stop = False

        # Statistics
        self.folders_found = 0
        self.files_found = 0
        self.folders_deleted = 0
        self.files_deleted = 0

        self._create_widgets()

    def _create_widgets(self):
        """Create and arrange all GUI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ===== Header Section =====
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(
            header_frame,
            text="🧹 Pattern-Based File & Folder Cleaner",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(side=tk.LEFT)

        # ===== Folder Selection Section =====
        folder_frame = ttk.LabelFrame(main_frame, text="Select Folder", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))

        folder_entry = ttk.Entry(
            folder_frame, textvariable=self.folder_path, font=("Segoe UI", 10)
        )
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        browse_btn = ttk.Button(
            folder_frame, text="Browse...", command=self._browse_folder
        )
        browse_btn.pack(side=tk.RIGHT)

        # ===== Options Section =====
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))

        dry_run_check = ttk.Checkbutton(
            options_frame,
            text="Dry Run (preview only, no deletions)",
            variable=self.dry_run,
        )
        dry_run_check.pack(side=tk.LEFT)

        # ===== Action Buttons =====
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(
            button_frame,
            text="▶ Start Scan",
            command=self._start_scan,
            style="Accent.TButton",
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.stop_btn = ttk.Button(
            button_frame, text="⏹ Stop", command=self._stop_scan, state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.clear_btn = ttk.Button(
            button_frame, text="🗑 Clear Log", command=self._clear_log
        )
        self.clear_btn.pack(side=tk.LEFT)

        # ===== Statistics Section =====
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.stats_label = ttk.Label(
            stats_frame,
            text="Folders: 0 found, 0 deleted | Files: 0 found, 0 deleted",
            font=("Segoe UI", 9),
        )
        self.stats_label.pack(side=tk.LEFT)

        # ===== Progress Log Section =====
        log_frame = ttk.LabelFrame(main_frame, text="Progress Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Text widget with scrollbar
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#ffffff",
            yscrollcommand=log_scroll.set,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

        # Configure text tags for colored output
        self.log_text.tag_configure("info", foreground="#4fc3f7")
        self.log_text.tag_configure("folder", foreground="#ffb74d")
        self.log_text.tag_configure("file", foreground="#81c784")
        self.log_text.tag_configure("error", foreground="#ef5350")
        self.log_text.tag_configure("success", foreground="#69f0ae")
        self.log_text.tag_configure("warning", foreground="#ffd54f")

        # ===== Status Bar =====
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

    def _browse_folder(self):
        """Open folder selection dialog."""
        folder = filedialog.askdirectory(title="Select Folder to Scan")
        if folder:
            self.folder_path.set(folder)

    def _log(self, message, tag="info"):
        """Add a message to the log with the specified tag."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        """Clear all log messages."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self._reset_stats()

    def _reset_stats(self):
        """Reset all statistics counters."""
        self.folders_found = 0
        self.files_found = 0
        self.folders_deleted = 0
        self.files_deleted = 0
        self._update_stats()

    def _update_stats(self):
        """Update the statistics label."""
        self.stats_label.config(
            text=f"Folders: {self.folders_found} found, {self.folders_deleted} deleted | "
            f"Files: {self.files_found} found, {self.files_deleted} deleted"
        )

    def _start_scan(self):
        """Start the scanning process in a separate thread."""
        folder = self.folder_path.get().strip()
        if not folder:
            messagebox.showwarning("Warning", "Please select a folder first!")
            return

        if not os.path.isdir(folder):
            messagebox.showerror("Error", "The selected path is not a valid directory!")
            return

        self.is_running = True
        self.should_stop = False
        self._reset_stats()

        # Update UI state
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Scanning...")

        mode = "DRY RUN" if self.dry_run.get() else "DELETE MODE"
        self._log(f"═══════════════════════════════════════════════", "info")
        self._log(f"Starting scan: {folder}", "info")
        self._log(f"Mode: {mode}", "warning" if self.dry_run.get() else "error")
        self._log(f"═══════════════════════════════════════════════", "info")

        # Run in a separate thread to keep UI responsive
        thread = threading.Thread(target=self._scan_thread, args=(folder,), daemon=True)
        thread.start()

    def _stop_scan(self):
        """Stop the scanning process."""
        self.should_stop = True
        self._log("Stopping scan...", "warning")

    def _scan_thread(self, directory):
        """The actual scanning logic running in a separate thread."""
        dry_run = self.dry_run.get()

        try:
            for root_dir, dirs, files in os.walk(directory, topdown=True):
                if self.should_stop:
                    break

                # ---- Handle directories ----
                for d in list(dirs):
                    if self.should_stop:
                        break

                    for pattern in self.DIR_PATTERNS:
                        if fnmatch(d, pattern):
                            path = os.path.join(root_dir, d)
                            self.folders_found += 1
                            self.root.after(0, self._update_stats)

                            if dry_run:
                                self.root.after(
                                    0, lambda p=path: self._log(f"[FOLDER] {p}", "folder")
                                )
                            else:
                                try:
                                    shutil.rmtree(path, ignore_errors=True)
                                    self.folders_deleted += 1
                                    self.root.after(0, self._update_stats)
                                    self.root.after(
                                        0,
                                        lambda p=path: self._log(
                                            f"[DELETED FOLDER] {p}", "folder"
                                        ),
                                    )
                                except Exception as e:
                                    self.root.after(
                                        0,
                                        lambda p=path, e=e: self._log(
                                            f"[ERROR] {p}: {e}", "error"
                                        ),
                                    )

                            # Prevent os.walk from descending into deleted dir
                            dirs.remove(d)
                            break

                # ---- Handle files ----
                for f in files:
                    if self.should_stop:
                        break

                    for pattern in self.FILE_PATTERNS:
                        if fnmatch(f, pattern):
                            path = os.path.join(root_dir, f)
                            self.files_found += 1
                            self.root.after(0, self._update_stats)

                            if dry_run:
                                self.root.after(
                                    0, lambda p=path: self._log(f"[FILE] {p}", "file")
                                )
                            else:
                                try:
                                    os.remove(path)
                                    self.files_deleted += 1
                                    self.root.after(0, self._update_stats)
                                    self.root.after(
                                        0,
                                        lambda p=path: self._log(
                                            f"[DELETED FILE] {p}", "file"
                                        ),
                                    )
                                except OSError as e:
                                    self.root.after(
                                        0,
                                        lambda p=path, e=e: self._log(
                                            f"[ERROR] {p}: {e}", "error"
                                        ),
                                    )
                            break

        except Exception as e:
            self.root.after(0, lambda: self._log(f"[CRITICAL ERROR] {e}", "error"))

        # Scan complete
        self.root.after(0, self._scan_complete)

    def _scan_complete(self):
        """Called when scanning is complete."""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        if self.should_stop:
            self._log("═══════════════════════════════════════════════", "warning")
            self._log("Scan stopped by user.", "warning")
        else:
            self._log("═══════════════════════════════════════════════", "success")
            self._log("Scan complete!", "success")

        self._log(
            f"Summary: {self.folders_found} folders, {self.files_found} files found",
            "info",
        )
        if not self.dry_run.get():
            self._log(
                f"Deleted: {self.folders_deleted} folders, {self.files_deleted} files",
                "success",
            )

        self.status_var.set("Ready")


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Set app icon (optional, will work without it)
    try:
        root.iconbitmap(default="")
    except tk.TclError:
        pass

    app = PatternCleanerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

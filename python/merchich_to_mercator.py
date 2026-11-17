import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pyproj import Transformer


class GeoJsonConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("EPSG:26191 → GeoJSON Converter")
        self.root.geometry("760x580")
        self.root.minsize(680, 500)

        # Initialize transformer (EPSG:26191 Merchich / Nord Maroc -> WGS 84)
        self.transformer = Transformer.from_crs(
            "EPSG:26191", "EPSG:4326", always_xy=True
        )

        self._build_ui()
        self.convert_coordinates()  # Run initial conversion on startup

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        main_frame = ttk.Frame(self.root, padding=14)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Controls: Geometry Type & Output Format ---
        options_frame = ttk.LabelFrame(main_frame, text="Output Options", padding=10)
        options_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(options_frame, text="Geometry Type:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 6)
        )
        self.geom_type_var = tk.StringVar(value="Point")
        geom_combo = ttk.Combobox(
            options_frame,
            textvariable=self.geom_type_var,
            values=["Point", "LineString", "Polygon"],
            state="readonly",
            width=14,
        )
        geom_combo.grid(row=0, column=1, padx=(0, 20))
        geom_combo.bind("<<ComboboxSelected>>", lambda _: self.convert_coordinates())

        ttk.Label(options_frame, text="Structure:").grid(
            row=0, column=2, sticky=tk.W, padx=(0, 6)
        )
        self.structure_var = tk.StringVar(value="FeatureCollection")
        struct_combo = ttk.Combobox(
            options_frame,
            textvariable=self.structure_var,
            values=["FeatureCollection", "Geometry Only"],
            state="readonly",
            width=18,
        )
        struct_combo.grid(row=0, column=3, padx=(0, 20))
        struct_combo.bind("<<ComboboxSelected>>", lambda _: self.convert_coordinates())

        self.use_api_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Generate ArcGIS REST URL too",
            variable=self.use_api_var,
            command=self.convert_coordinates,
        ).grid(row=0, column=4, sticky=tk.W)

        # --- Middle Panes: Input (Left) & Output (Right) ---
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left Pane: EPSG:26191 Input
        left_frame = ttk.LabelFrame(
            paned, text="Input Coordinates (EPSG:26191: X, Y per line)", padding=8
        )
        paned.add(left_frame, weight=1)

        self.input_text = tk.Text(
            left_frame, font=("Consolas", 11), wrap=tk.NONE, width=30
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)
        # Pre-populate with your two coordinates
        self.input_text.insert("1.0", "818043 457664\n807488 449167")

        # Right Pane: GeoJSON Output
        right_frame = ttk.LabelFrame(
            paned, text="Generated GeoJSON (EPSG:4326)", padding=8
        )
        paned.add(right_frame, weight=2)

        self.output_text = tk.Text(
            right_frame, font=("Consolas", 10), wrap=tk.NONE, bg="#1e1e1e", fg="#d4d4d4"
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # --- Bottom Action Buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Convert →", command=self.convert_coordinates).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        ttk.Button(btn_frame, text="Copy GeoJSON", command=self.copy_to_clipboard).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        ttk.Button(btn_frame, text="Save .geojson...", command=self.save_geojson).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        ttk.Button(btn_frame, text="Clear", command=self.clear_all).pack(side=tk.RIGHT)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="#555").pack(
            anchor=tk.W, pady=(6, 0)
        )

    def _parse_input(self) -> list[tuple[float, float]]:
        raw = self.input_text.get("1.0", tk.END).strip()
        if not raw:
            return []

        coords = []
        for idx, line in enumerate(raw.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            # Support space, comma, semicolon, or tab delimiters
            cleaned = line.replace(",", " ").replace(";", " ").replace("\t", " ")
            parts = [p for p in cleaned.split(" ") if p]
            if len(parts) != 2:
                raise ValueError(f"Line {idx}: Expected 2 numbers (X Y), got '{line}'")
            x, y = float(parts[0]), float(parts[1])
            coords.append((x, y))
        return coords

    def convert_coordinates(self):
        try:
            pts_26191 = self._parse_input()
            if not pts_26191:
                self.output_text.delete("1.0", tk.END)
                self.status_var.set("Enter X Y coordinates on the left.")
                return

            # Reproject to [lng, lat] rounded to 8 decimal places (~1.1 mm precision)
            pts_4326 = []
            for x, y in pts_26191:
                lon, lat = self.transformer.transform(x, y)
                pts_4326.append([round(lon, 8), round(lat, 8)])

            geom_type = self.geom_type_var.get()
            structure = self.structure_var.get()

            if geom_type == "Point":
                if structure == "Geometry Only" and len(pts_4326) == 1:
                    result = {"type": "Point", "coordinates": pts_4326[0]}
                elif structure == "Geometry Only":
                    result = {"type": "MultiPoint", "coordinates": pts_4326}
                else:
                    result = {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "properties": {
                                    "source_x": pts_26191[i][0],
                                    "source_y": pts_26191[i][1],
                                    "crs": "EPSG:26191",
                                },
                                "geometry": {"type": "Point", "coordinates": pt},
                            }
                            for i, pt in enumerate(pts_4326)
                        ],
                    }

            elif geom_type == "LineString":
                if len(pts_4326) < 2:
                    raise ValueError("LineString requires at least 2 points.")
                geom = {"type": "LineString", "coordinates": pts_4326}
                result = (
                    geom
                    if structure == "Geometry Only"
                    else {
                        "type": "FeatureCollection",
                        "features": [
                            {"type": "Feature", "properties": {}, "geometry": geom}
                        ],
                    }
                )

            elif geom_type == "Polygon":
                if len(pts_4326) < 3:
                    raise ValueError("Polygon requires at least 3 points.")
                ring = list(pts_4326)
                if ring[0] != ring[-1]:
                    ring.append(ring[0])  # Auto-close polygon ring
                geom = {"type": "Polygon", "coordinates": [ring]}
                result = (
                    geom
                    if structure == "Geometry Only"
                    else {
                        "type": "FeatureCollection",
                        "features": [
                            {"type": "Feature", "properties": {}, "geometry": geom}
                        ],
                    }
                )

            output_str = json.dumps(result, indent=2)

            if self.use_api_var.get():
                import urllib.parse

                esri_geoms = json.dumps(
                    {
                        "geometryType": "esriGeometryPoint",
                        "geometries": [{"x": x, "y": y} for x, y in pts_26191],
                    },
                    separators=(",", ":"),
                )
                encoded = urllib.parse.quote(esri_geoms)
                api_url = (
                    "https://sampleserver6.arcgisonline.com/arcgis/rest/services/"
                    f"Utilities/Geometry/GeometryServer/project?inSR=26191&outSR=4326"
                    f"&geometries={encoded}&f=pjson"
                )
                output_str += f"\n\n// ArcGIS REST API URL:\n// {api_url}"

            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", output_str)
            self.status_var.set(
                f"Converted {len(pts_4326)} coordinate(s) successfully."
            )

        except Exception as e:
            self.status_var.set(f"Error: {e}")

    def copy_to_clipboard(self):
        content = self.output_text.get("1.0", tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_var.set("GeoJSON copied to clipboard.")

    def save_geojson(self):
        content = self.output_text.get("1.0", tk.END).strip()
        if not content:
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".geojson",
            filetypes=[("GeoJSON Files", "*.geojson"), ("JSON Files", "*.json")],
            initialfile="converted_26191.geojson",
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.status_var.set(f"Saved to {file_path}")

    def clear_all(self):
        self.input_text.delete("1.0", tk.END)
        self.output_text.delete("1.0", tk.END)
        self.status_var.set("Cleared.")


if __name__ == "__main__":
    root = tk.Tk()
    app = GeoJsonConverterApp(root)
    root.mainloop()

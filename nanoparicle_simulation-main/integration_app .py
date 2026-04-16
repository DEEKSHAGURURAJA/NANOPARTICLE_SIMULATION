import sys
import subprocess
from pathlib import Path
import pandas as pd
import folium
from folium.plugins import HeatMap
import webview

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DEPTH_SCRIPT = BASE_DIR / "depth_modified.py"
CSV_PATH = BASE_DIR / "Microplastics_Clean_Essential.csv"
HTML_PATH = BASE_DIR / "microplastics_map.html"

# --- Load industries data ---
INDUSTRY_CSV = BASE_DIR / "geocoded_500_successful.csv"
industries = pd.read_csv(INDUSTRY_CSV)

# Ensure columns are correct
lat_col = "latitude" if "latitude" in industries.columns else "lat"
lon_col = "longitude" if "longitude" in industries.columns else "lon"

# --- Load dataset ---
df = pd.read_csv(CSV_PATH)
df = df[df['is_land'] == False]

# --- Map center ---
avg_lat = df['Latitude_degree'].mean()
avg_lon = df['Longitudedegree'].mean()

# --- Create Map (tiles=None so we can add multiple basemaps) ---
m = folium.Map(location=[avg_lat, avg_lon], zoom_start=2, control_scale=True, tiles=None)

# --- Add base layers ---
folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)

# Stamen Toner
folium.TileLayer(
    tiles="https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png",
    name="Stamen Toner",
    attr="Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors"
).add_to(m)

# Stamen Terrain
folium.TileLayer(
    tiles="https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg",
    name="Stamen Terrain",
    attr="Map tiles by Stamen Design, CC BY 3.0 — Map data © OpenStreetMap contributors"
).add_to(m)

# Esri Satellite
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    name="Esri Satellite",
    attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community"
).add_to(m)

# Carto Dark Mode
folium.TileLayer(
    tiles="https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}{r}.png",
    name="Carto Dark",
    attr="© OpenStreetMap contributors © CARTO"
).add_to(m)

# --- Add industry markers as a FeatureGroup ---
industry_layer = folium.FeatureGroup(name="Industries", show=True).add_to(m)
for _, row in industries.iterrows():
    folium.Marker(
        location=[row[lat_col], row[lon_col]],
        icon=folium.Icon(color="cadetblue", icon="industry", prefix="fa", icon_color="white", shadow=False),
    ).add_to(industry_layer)

# --- Heatmaps by color ---
color_gradients = {
    'Red':   {'0.0': '#ffe6e6', '0.25': '#ffb3b3', '0.5': '#ff6666', '0.75': '#cc0000', '1.0': '#660000'},
    'Green': {'0.0': '#e6ffe6', '0.25': '#a8e6a1', '0.5': '#55c655', '0.75': '#1f8a1f', '1.0': '#0f4d0f'},
    'Blue':  {'0.0': '#e6f0ff', '0.25': '#b3ccff', '0.5': '#6699ff', '0.75': '#3366cc', '1.0': '#0b3d91'}
}

for color in df['Color'].dropna().unique():
    cdf = df[df['Color'] == color]
    heat_data = cdf[['Latitude_degree', 'Longitudedegree', 'Microplastics_measurement']].values.tolist()
    
    heatmap = HeatMap(
        heat_data, radius=15, blur=10, min_opacity=0.4, max_zoom=1,
        gradient=color_gradients.get(color)
    )
    
    fg = folium.FeatureGroup(name=f"{color} Microplastics", show=True)
    fg.add_child(heatmap)
    fg.add_to(m)

# --- Add Layer Control (both base maps + overlays) ---
folium.LayerControl(collapsed=False).add_to(m)

# --- Inject JS for click event (triggers PyWebview API) ---
click_js = """
(function() {
  function attachClick() {
    var mapRef = null;
    for (var key in window) {
      if (key.startsWith("map_")) {
        mapRef = window[key];
        break;
      }
    }
    if (!mapRef) {
      console.error("No Folium map variable found!");
      return;
    }

    // Remove existing listeners first (avoids double popups)
    mapRef.off('click');

    function onMapClick(e) {
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.run_simulation(e.latlng.lat, e.latlng.lng)
          .then(function(resp) { console.log(resp); })
          .catch(function(err) {
            console.error('API error:', err);
            alert('Failed to start simulation');
          });
      } else {
        console.error('pywebview.api not ready');
        alert('Backend not ready yet');
      }
    }

    mapRef.on('click', onMapClick);
    console.log('Click handler attached (only once)');
  }

  if (window.pywebview) {
    document.addEventListener('pywebviewready', attachClick);
  } else {
    window.addEventListener('load', attachClick);
  }
})();
"""
m.get_root().html.add_child(folium.Element(f"<script>{click_js}</script>"))

# --- Save HTML ---
m.save(str(HTML_PATH))

# --- PyWebview API bridge ---
class Api:
    def __init__(self, base_dir, depth_script):
        self.base_dir = Path(base_dir)
        self.depth_script = Path(depth_script)

    def run_simulation(self, lat, lon):
        # Basic validation & logging
        print(f"[INFO] Clicked at lat={lat}, lon={lon}")
        if not self.depth_script.exists():
            return f"[ERROR] depth script not found: {self.depth_script}"

        # Start pygame sim in a separate process using the SAME interpreter
        log_path = self.base_dir / "simulation_out.log"
        with open(log_path, "a", encoding="utf-8") as log:
            subprocess.Popen(
                [sys.executable, str(self.depth_script), str(lat), str(lon)],
                cwd=str(self.base_dir),  # ensures CSV relative paths work
                stdout=log,
                stderr=subprocess.STDOUT
            )
        return "Simulation launched"

api = Api(BASE_DIR, DEPTH_SCRIPT)

# --- Launch window (debug=True shows JS console in terminal) ---
window = webview.create_window("Microplastics Map", str(HTML_PATH), js_api=api)
webview.start(debug=True)

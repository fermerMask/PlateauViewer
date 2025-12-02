import json
import tempfile

import geopandas as gpd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="PLATEAU Simulator", layout="wide")
st.title("PLATEAU Simulation Viewer")


# ===========================
# 1) Load File
# ===========================

uploaded_file = st.file_uploader(
    "PLATEAU GeoJSON を選択してください (.geojson / .json)", type=["geojson", "json"]
)

if uploaded_file is None:
    st.info("左のボックスから PLATEAU GeoJSON ファイルを選択してください")
    st.stop()

# Save uploaded file
with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as tmp:
    tmp.write(uploaded_file.read())
    tmp_path = tmp.name

# Read GeoJSON
gdf = gpd.read_file(tmp_path).to_crs(epsg=4326)


# ===========================
# 2) Determine height column
# ===========================

height_key = None
for col in gdf.columns:
    if "height" in col.lower():
        height_key = col
        break

if height_key:
    gdf["height"] = gdf[height_key].fillna(10)
else:
    gdf["height"] = 10  # default


# ===========================
# 3) Simulation parameters
# ===========================

st.sidebar.header("Simulation Settings")

water_level = st.sidebar.slider(
    "水位 (m)",
    min_value=0.0,
    max_value=float(gdf["height"].max() + 10),
    value=2.0,
    step=0.5,
)

extrude = st.sidebar.checkbox("3D表示（押し出し）", value=True)


# ===========================
# 4) Simulation Logic
# ===========================

# flooded = 水位が建物高さの 50% 以上
gdf["flooded"] = gdf["height"].apply(lambda h: water_level >= 0.5 * h)


def get_color(flooded):
    return [200, 50, 50, 200] if flooded else [100, 160, 200, 150]


gdf["color"] = gdf["flooded"].apply(get_color)


# ===========================
# 5) Map Center
# ===========================

center = gdf.geometry.centroid
lon = center.x.mean()
lat = center.y.mean()


# ===========================
# 6) Pydeck Layer
# ===========================

layer = pdk.Layer(
    "GeoJsonLayer",
    gdf.__geo_interface__,
    stroked=True,
    filled=True,
    extruded=extrude,
    get_elevation="properties.height",
    get_fill_color="properties.color",
    get_line_color=[50, 50, 80],
    line_width_min_pixels=1,
    pickable=True,
)


view = pdk.ViewState(
    latitude=lat,
    longitude=lon,
    zoom=14,
    pitch=45 if extrude else 0,
)


deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip={"text": "height: {height} m\nflooded: {flooded}"},
    map_style="mapbox://styles/mapbox/light-v9",
)


# ===========================
# 7) Render
# ===========================

st.subheader("Simulation Result")
st.pydeck_chart(deck)


# ===========================
# 8) Summary
# ===========================

total = len(gdf)
flooded = gdf["flooded"].sum()

with st.expander("統計情報"):
    st.write(f"総建物数: {total}")
    st.write(f"浸水建物数: {flooded}")
    st.write(f"浸水率: {flooded / total * 100:.1f}%")
    st.dataframe(gdf.head())

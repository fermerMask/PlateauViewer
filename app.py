import geopandas as gpd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="PLATEAU Viewer", layout="wide")
st.title("PLATEAU Viewer (Streamlit + PyDeck)")

# -----------------------
# GeoJSON の読み込み
# -----------------------
geojson_path = "data/shibuya_buildings.geojson"

st.sidebar.write("PLATEAU データ読み込み中…")
gdf = gpd.read_file(geojson_path)
gdf = gdf.to_crs(epsg=4326)

# 中心位置を計算
center_lon = gdf.geometry.centroid.x.mean()
center_lat = gdf.geometry.centroid.y.mean()

# -----------------------
# 高さ属性を推定（あれば使用）
# -----------------------
height_key = None
for col in gdf.columns:
    if "height" in col.lower():
        height_key = col
        break

if height_key:
    gdf["height"] = gdf[height_key].fillna(15)
else:
    gdf["height"] = 15  # デフォルト高さ

# -----------------------
# 3D描画オン/オフ
# -----------------------
extrude = st.sidebar.checkbox("3D表示（押し出し）", value=False)

layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf.__geo_interface__,
    stroked=True,
    filled=True,
    extruded=extrude,
    get_elevation="properties.height",
    get_fill_color="[100, 160, 200]",
    get_line_color="[50, 50, 80]",
    line_width_min_pixels=1,
)

view_state = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=14,
    pitch=45 if extrude else 0,
)

# -----------------------
# 表示
# -----------------------
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v9",
    )
)

import geopandas as gpd
import pydeck as pdk

st.set_page_config(page_title="PLATEAU Viewer", layout="wide")
st.title("PLATEAU Viewer (Streamlit + PyDeck)")

# -----------------------
# GeoJSON の読み込み
# -----------------------
geojson_path = "data/shibuya_buildings.geojson"

st.sidebar.write("PLATEAU データ読み込み中…")
gdf = gpd.read_file(geojson_path)
gdf = gdf.to_crs(epsg=4326)

# 中心位置を計算
center_lon = gdf.geometry.centroid.x.mean()
center_lat = gdf.geometry.centroid.y.mean()

# -----------------------
# 高さ属性を推定（あれば使用）
# -----------------------
height_key = None
for col in gdf.columns:
    if "height" in col.lower():
        height_key = col
        break

if height_key:
    gdf["height"] = gdf[height_key].fillna(15)
else:
    gdf["height"] = 15  # デフォルト高さ

# -----------------------
# 3D描画オン/オフ
# -----------------------
extrude = st.sidebar.checkbox("3D表示（押し出し）", value=False)

layer = pdk.Layer(
    "GeoJsonLayer",
    data=gdf.__geo_interface__,
    stroked=True,
    filled=True,
    extruded=extrude,
    get_elevation="properties.height",
    get_fill_color="[100, 160, 200]",
    get_line_color="[50, 50, 80]",
    line_width_min_pixels=1,
)

view_state = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=14,
    pitch=45 if extrude else 0,
)

# -----------------------
# 表示
# -----------------------
st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/light-v9",
    )
)

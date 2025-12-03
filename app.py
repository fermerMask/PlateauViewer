import os
import tempfile

import geopandas as gpd
import numpy as np
import pydeck as pdk
import streamlit as st
from altair.utils.html import TemplateName

st.set_page_config(page_title="PLATEAU Multi-Hazard Simulator", layout="wide")
st.title("PLATEAU Multi-Hazard Simulator")
DATA_DIR = "./data"
files = [
    f for f in os.listdir(DATA_DIR) if f.endswith(".geojson") or f.endswith(".json")
]

if not files:
    st.error(f"No .geojson files in ./{DATA_DIR}/")
    st.stop()

filename = st.sidebar.selectbox("Select dataset", sorted(files))
filepath = os.path.join(DATA_DIR, filename)

st.sidebar.success(f"Loaded:{filename}")

# upload_file = st.file_uploader("Upload PLATEAU 3D GeoJSON", type=["geojson", "json"])

# if not upload_file:
#    st.info("Please upload a PLATEAU 3D GeoJSON file.")
#    st.stop()

# with tempfile.NamedTemporaryFile(delete=False, suffix=".geojson") as temp_file:
#    temp_file.write(upload_file.read())
#    path = temp_file.name

gdf = gpd.read_file(filepath)
gdf["geometry"] = gdf["geometry"].apply(
    lambda geom: geom.__class__([tuple(coord[:2] for coord in geom.exterior.coords)])
    if geom.geom_type == "Polygon"
    else geom
)

gdf = gdf.set_crs(epsg=4979, allow_override=True)
gdf = gdf.to_crs(epsg=4326)

height_key = next((c for c in gdf.columns if "height" in c.lower()), None)

# default height
if height_key:
    gdf["height"] = gdf[height_key].fillna(10)
else:
    gdf["height"] = 10

# sanitize
gdf.loc[gdf["height"] <= 0, "height"] = 10
gdf.loc[gdf["height"] > 200, "height"] = 50

# visualization height
gdf["vis_height"] = gdf["height"] * 2 + 5

if "floors" not in gdf.columns:
    gdf["floors"] = np.random.randint(1, 6, len(gdf))

if "year" not in gdf.columns:
    gdf["year"] = np.random.randint(1950, 2000, len(gdf))

hazard = st.sidebar.selectbox("hazard type", ["洪水", "地震", "火災", "土砂災害"])

extrude = st.sidebar.checkbox("3D View", value=True)


def calcurate_flood(df):
    water = st.sidebar.slider("水位(m)", 0.0, float(df["height"].max() + 10), 2.0, 0.5)
    df["risk"] = df["height"].apply(lambda h: water >= 0.5 * h)
    return df


def calcurate_fire(df):
    df["risk"] = (df["floors"] <= 2) | (df["year"] <= 1980)
    return df


def calcurate_earthquake(df):
    df["risk"] = df["floors"].apply(lambda f: f >= 4)
    return df


def calcurate_elevation(df):
    df["risk"] = (df["year"] <= 1981) & (df["floors"] <= 2)
    return df


def calcurate_landslide(df):
    df["risk"] = df["height"] <= 5
    return df


if hazard == "洪水":
    gdf = calcurate_flood(gdf)
elif hazard == "地震":
    gdf = calcurate_earthquake(gdf)
elif hazard == "火災":
    gdf = calcurate_fire(gdf)
elif hazard == "土砂災害":
    gdf = calcurate_landslide(gdf)


def get_color(risk):
    return [200, 50, 50, 200] if risk else [100, 150, 200, 150]


gdf["color"] = gdf["risk"].apply(get_color)


center = gdf.geometry.centroid
lat, lon = center.y.mean(), center.x.mean()

layer = pdk.Layer(
    "GeoJsonLayer",
    gdf.__geo_interface__,
    filled=True,
    stroked=False,
    extruded=extrude,
    get_elevation="properties.height",
    get_fill_color="properties.color",
    pickable=True,
)

view = pdk.ViewState(
    latitude=lat,
    longitude=lon,
    zoom=15,
    pitch=45 if extrude else 0,
    bearing=30,
)


deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    views=[pdk.View(type="OrbitView", controller=True)],
    tooltip={"text": "{risk}"},
    map_style="mapbox://styles/mapbox/light-v10",
)


st.pydeck_chart(deck)

total = len(gdf)
risk = gdf["risk"].sum()

st.write(f"### Hazard:{hazard}")
st.write(f"### Total buildings:{total}")
st.write(f"### Risk buildings:{risk}")
st.write(f"### Risk percentage:{risk / total * 100:.2f}%")
st.dataframe(gdf[["height", "floors", "year", "risk"]].head())

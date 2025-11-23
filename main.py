# app.py
import streamlit as st
import tempfile
from lxml import etree
import re
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, Point
from pyproj import Transformer
import pydeck as pdk

st.set_page_config(layout="wide", page_title="PLATEAU Simulator")

st.title("PLATEAU CityGML シミュレーション（簡易）")
st.markdown(
    "CityGMLファイルをアップロードして、建物の高さ情報を抽出し、スライダーで水位を変化させて簡易浸水シミュレーションを行います。"
)

with st.expander("説明（短く）"):
    st.write(
        """
- 本アプリは CityGML (Project PLATEAU で配布される形式) のうち建物ジオメトリと高さ情報を簡易抽出して可視化します。
- 正確な投影法や属性名はデータセットにより差があるため、抽出に失敗した場合は該当ファイルのメタデータ（srsNameなど）を確認してください。
"""
    )

# ファイルアップロード
uploaded = st.file_uploader("CityGMLファイルをアップロード（.xml / .gml）", type=["xml", "gml", "zip"])

if uploaded is None:
    st.info("サンプルデータが必要なら、PLATEAUポータルからCityGMLや3D Tilesをダウンロードしてください。 （例: G空間情報センター）")
    st.markdown("参考: PLATEAU公式ページ・オープンデータポータル。")
    st.write("（→ 国土交通省 PLATEAU）")
    st.stop()

# 一時ファイルに保存して解析
with tempfile.NamedTemporaryFile(delete=False, suffix=".gml") as tmp:
    tmp.write(uploaded.read())
    tmp_path = tmp.name

st.write("解析中... (大型ファイルでは時間がかかります)")

# 名前空間を柔軟に扱うためにXML読み込み
def parse_citygml_buildings(path, max_buildings=5000):
    tree = etree.parse(path)
    root = tree.getroot()
    nsmap = root.nsmap
    # collect possible building element names
    candidates = []
    for tag in root.iter():
        # tag is like {namespace}LocalName
        local = etree.QName(tag).localname
        if local.lower().startswith("building") or local.lower().startswith("bldg"):
            candidates.append(tag.tag)
    # prefer standard CityGML bldg:Building
    bldg_elems = root.findall('.//{*}Building') or root.findall('.//{*}building') or root.findall('.//{*}bldg:*', namespaces=nsmap)
    if len(bldg_elems) == 0:
        # fallback: find elements with 'boundedBy' children that contain polygons
        bldg_elems = []
        for elem in root.iter():
            if any(child.tag.endswith('boundedBy') for child in elem):
                bldg_elems.append(elem)
    geoms = []
    attrs = []
    count = 0
    for b in bldg_elems:
        if count >= max_buildings:
            break
        # try to find polygon coordinates inside this building
        poly_texts = b.findall('.//{*}posList') + b.findall('.//{*}coordinates') + b.findall('.//{*}pos')
        polys = []
        for p in poly_texts:
            text = (p.text or "").strip()
            if not text:
                continue
            # posList has numbers: x y z x y z ...
            nums = re.split(r'\s+', text)
            if len(nums) < 6:
                continue
            # group into tuples of length 2 or 3
            coords = []
            if len(nums) % 3 == 0:
                it = iter(nums)
                for x,y,z in zip(it, it, it):
                    coords.append((float(x), float(y), float(z)))
            elif len(nums) % 2 == 0:
                it = iter(nums)
                for x,y in zip(it, it):
                    coords.append((float(x), float(y)))
            else:
                # try comma separated (gml:coordinates)
                parts = [pt for pt in text.replace(',', ' ').split()]
                if len(parts) % 2 == 0:
                    it = iter(parts)
                    for x,y in zip(it, it):
                        coords.append((float(x), float(y)))
            if len(coords) >= 3:
                polys.append(coords)
        if not polys:
            continue
        # take the exterior ring (first polygon), drop Z if present for now
        exterior = polys[0]
        # determine height: try to find measuredHeight, height, or envelope Z difference
        height = None
        # search attributes
        h_elems = b.findall('.//{*}measuredHeight') + b.findall('.//{*}height') + b.findall('.//{*}roofHeight')
        for he in h_elems:
            try:
                height = float((he.text or "").strip())
                break
            except:
                pass
        # fallback: if coordinates have z, compute maxZ-minZ
        zs = [pt[2] for pt in exterior if len(pt) == 3]
        if zs and height is None:
            height = float(max(zs) - min(zs))
        # if still None, set default estimate (e.g. 10m)
        if height is None:
            height = 10.0
        # convert exterior to 2D polygon (drop Z)
        poly2d = Polygon([(p[0], p[1]) for p in exterior])
        if not poly2d.is_valid or poly2d.area == 0:
            continue
        geoms.append(poly2d)
        # extract some attrs like usage, year
        usage = None
        year = None
        usage_e = b.findall('.//{*}function') + b.findall('.//{*}usage')
        if usage_e:
            usage = (usage_e[0].text or "").strip()
        year_e = b.findall('.//{*}yearOfConstruction') + b.findall('.//{*}constructionYear')
        if year_e:
            try:
                year = int((year_e[0].text or "").strip())
            except:
                year = None
        attrs.append({"height_m": height, "usage": usage, "year": year})
        count += 1
    gdf = gpd.GeoDataFrame(attrs, geometry=geoms, crs=None)
    return gdf

try:
    gdf = parse_citygml_buildings(tmp_path, max_buildings=2000)
except Exception as e:
    st.error(f"CityGML解析中にエラー: {e}")
    st.stop()

if gdf.empty:
    st.error("建物データが抽出できませんでした。CityGMLの構造やsrsNameを確認してください。")
    st.stop()

st.success(f"抽出完了: 建物数 = {len(gdf)}（上限がある場合は設定を増やしてください）")

# 座標参照系が不明な場合はユーザーに入力させる
st.info("注意: CityGMLの座標参照系（CRS）が必ずしも含まれていないことがあります。正しいCRSを入力してください。")
crs_input = st.text_input("データのCRS（例: EPSG:4612, EPSG:6668, EPSG:4326）を入力（不明なら EPSG:4326 を試す）", "EPSG:4326")

try:
    gdf.set_crs(crs_input, allow_override=True, inplace=True)
    # 将来可視化のためにWebメルカトル(EPSG:3857)→Web地図やpydeckはlng/latが必要
    gdf_wgs = gdf.to_crs(epsg=4326)
except Exception as e:
    st.warning(f"CRS変換で警告: {e} -- CRSをそのまま使います。")
    gdf_wgs = gdf.copy()
    # try to ensure geometry coords look like lat/lon
    gdf_wgs["lon"] = gdf_wgs.geometry.centroid.x
    gdf_wgs["lat"] = gdf_wgs.geometry.centroid.y

# compute centroid & prepare dataframe for pydeck
gdf_wgs["centroid"] = gdf_wgs.geometry.centroid
gdf_wgs["lon"] = gdf_wgs.centroid.x
gdf_wgs["lat"] = gdf_wgs.centroid.y
gdf_wgs["height_m"] = gdf_wgs["height_m"].astype(float)

# UI: water level slider
water_level = st.slider("水位 (m)", min_value=0.0, max_value=float(max(50, gdf_wgs["height_m"].max() + 10)), value=2.0, step=0.5)

gdf_wgs["inundated"] = gdf_wgs["height_m"].apply(lambda h: water_level >= 0.5 * h)

# Prepare layer for pydeck extruded polygons
def polygon_to_deck_coords(poly):
    # pydeck expects list of [lng, lat]
    if poly.is_empty:
        return []
    x,y = poly.exterior.coords.xy
    return [[float(xi), float(yi)] for xi, yi in zip(x, y)]

gdf_wgs["deck_coords"] = gdf_wgs.geometry.apply(polygon_to_deck_coords)

# create dataframe for pydeck
df = pd.DataFrame({
    "lon": gdf_wgs["lon"],
    "lat": gdf_wgs["lat"],
    "height_m": gdf_wgs["height_m"],
    "inundated": gdf_wgs["inundated"],
    "deck_coords": gdf_wgs["deck_coords"]
})

# color function
def color_for_row(inundated):
    return [200, 30, 30, 180] if inundated else [80, 160, 200, 140]

df["color"] = df["inundated"].apply(color_for_row)
df["elevation"] = df["height_m"] * 3  # exaggeration factor for visibility

# center view
mid_lon = df["lon"].mean()
mid_lat = df["lat"].mean()

polygon_layer = pdk.Layer(
    "PolygonLayer",
    data=df,
    get_polygon="deck_coords",
    get_fill_color="color",
    get_line_color=[50,50,50],
    pickable=True,
    extruded=True,
    get_elevation="elevation",
    elevation_scale=1,
    auto_highlight=True,
)

view_state = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=15, pitch=45)

r = pdk.Deck(layers=[polygon_layer], initial_view_state=view_state, tooltip={"text": "高さ(m): {height_m}\n浸水: {inundated}"})

st.pydeck_chart(r)

# table & stats
col1, col2 = st.columns(2)
with col1:
    st.subheader("要約")
    st.write(f"総建物数: {len(df)}")
    st.write(f"浸水判定建物数: {int(df['inundated'].sum())}")
    st.write(f"平均建物高 (m): {df['height_m'].mean():.1f}")

with col2:
    st.subheader("建物一覧（先頭50件）")
    st.dataframe(df[["lon", "lat", "height_m", "inundated"]].head(50))

st.markdown("---")
st.write("注意事項：このシミュレーションは非常に簡易化しています。実運用では地盤高（DEM）、敷地ごとの基礎高、浸水流入解析などが必要です。")

st.markdown("### 次のステップ（オプション）")
st.markdown(
    """
- CityGMLのsrsNameを適切に読み取って正しい投影で表示する（CityGMLのメタデータ参照）。
- DEM（地形）を読み込み、建物の基底標高を計算して浸水判定を改良する。
- 3D Tilesを利用してCesiumで高品質な3D表示／アニメーションを行う（PLATEAU GIS ConverterでCityGML→3D Tiles変換）。
"""
)

st.markdown("### 参考・出典")
st.markdown(
    "- PLATEAU（Project PLATEAU） - 国土交通省公式情報、CityGMLベースの3D都市モデル。"
)

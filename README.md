# PLATEAU × Streamlit

2D（※3Dなし）地図可視化アプリ

このリポジトリは **PLATEAU（3D都市モデル）を Streamlit 上で
2D表示のみで可視化するサンプルアプリ**です。

3Dレンダリング（Cesium / three.js / pydeck の extruded 表示など）は使いません。
建物データ（GeoJSON / CityGML 変換済み）を Streamlit 上で
シンプルに地図へ描画します。

---

## ✨ 特徴

* Streamlitのみで動作
* Webブラウザで都市データを開ける
* PLATEAUのGeoJSONデータ対応

---

## 📁 ディレクトリ構成

```
project/
├── main.py
└── README.md
```

---

## 🚀 インストール

Python 3.9+ 推奨

```
pip install streamlit geopandas shapely pydeck
```

※ pydeckは deck.gl の Python API（今回は2D描画のみ）

---

## ▶ 実行方法

```
streamlit run app.py
```

自動的にブラウザが開きます：

```
http://localhost:8501
```

---

## 📌 使用データ

PLATEAU 建物データ（CityGML）を
GeoJSON に変換して利用します。

例：

```
data/shibuya_buildings.geojson
```

CityGML → GeoJSON への変換は
以下ソフトが使えます：

* QGIS
* GDAL
* FME
* PLATEAU-GIS-Converter
* plateau-tool

---

## 🧠 サンプルコード（app.py）

```python
import streamlit as st
import geopandas as gpd
import pydeck as pdk

st.set_page_config(page_title="PLATEAU Viewer", layout="wide")

st.title("PLATEAU GeoJSON 2D Viewer (Streamlit)")

# GeoJSON 読み込み
gdf = gpd.read_file("data/shibuya_buildings.geojson")

# 緯度経度の中心を推定
center_lon = gdf.geometry.centroid.x.mean()
center_lat = gdf.geometry.centroid.y.mean()

# pydeck 2D レイヤー
layer = pdk.Layer(
    "GeoJsonLayer",
    gdf,
    stroked=True,
    filled=True,
    get_fill_color=[100, 150, 200],
    line_width_min_pixels=1,
)

view = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lon,
    zoom=14,
    pitch=0,
    bearing=0
)

st.pydeck_chart(
    pdk.Deck(
        layers=[layer],
        initial_view_state=view,
        map_style="mapbox://styles/mapbox/light-v9"
    )
)
```

※ `extruded` を指定していないため **2D 表示**

---

## 🧩 データ加工について

PLATEAU の建物データには高さ情報も含まれます。
GeoJSON に変換時に属性を残しておけば：

* 用途別色分け
* 高さ区分ごとの分類
* 範囲フィルタリング

などが可能です。

---

## 🔖 ライセンス

* 本アプリ：MIT
* PLATEAU データ：
  国土交通省「3D都市モデル（PLATEAU）」の利用条件に従ってください

---

## 📣 関連リンク

* Streamlit
* pydeck / deck.gl
* PLATEAU（国土交通省）

シンプルに PLATEAU データを Streamlit で確認したい方向けの最低構成です。

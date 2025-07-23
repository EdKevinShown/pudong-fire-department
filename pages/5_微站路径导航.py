import streamlit as st
import requests
import pandas as pd
from streamlit_folium import st_folium
import folium
import math

st.set_page_config(page_title="🚗 微站-火警导航", layout="wide")
st.title("微站到火警点导航路径展示")

API_KEY = "89d2570099dca1c27439bfa3b9cda8d5"  # 替换成你的高德API Key

@st.cache_data
def load_station_data():
    df = pd.read_csv("data/微站地址_已地理编码.csv", encoding="utf-8")
    return df[['所属微站', '微站地址_纬度', '微站地址_经度']]

def gcj02_to_wgs84(lng, lat):
    # 坐标转换辅助函数
    def transformLat(x, y):
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
        return ret

    def transformLng(x, y):
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
        ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
        return ret

    def outOfChina(lng, lat):
        return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)

    if outOfChina(lng, lat):
        return lng, lat

    a = 6378245.0  # 长半轴
    ee = 0.00669342162296594323  # 偏心率平方
    dLat = transformLat(lng - 105.0, lat - 35.0)
    dLng = transformLng(lng - 105.0, lat - 35.0)
    radLat = lat / 180.0 * math.pi
    magic = math.sin(radLat)
    magic = 1 - ee * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * math.pi)
    dLng = (dLng * 180.0) / (a / sqrtMagic * math.cos(radLat) * math.pi)
    mgLat = lat + dLat
    mgLng = lng + dLng
    return lng * 2 - mgLng, lat * 2 - mgLat

stations = load_station_data()

st.markdown("请选择微站，并输入终点（火警点）坐标：")
station_name = st.selectbox("选择微站名称", stations['所属微站'].unique())
station_info = stations[stations['所属微站'] == station_name].iloc[0]
start_lat = float(station_info['微站地址_纬度'])
start_lng = float(station_info['微站地址_经度'])

col1, col2 = st.columns(2)
with col1:
    end_lng = st.text_input("终点经度（火警点）", value="121.4521")
with col2:
    end_lat = st.text_input("终点纬度（火警点）", value="31.2232")

if "route_points" not in st.session_state:
    st.session_state["route_points"] = None
if "route_info" not in st.session_state:
    st.session_state["route_info"] = None
if "route_debug" not in st.session_state:
    st.session_state["route_debug"] = None

if st.button("🚀 计算并显示路径"):
    route_url = (
        f"https://restapi.amap.com/v3/direction/driving?"
        f"origin={start_lng},{start_lat}&destination={end_lng},{end_lat}&key={API_KEY}"
    )
    res = requests.get(route_url).json()
    st.session_state["route_debug"] = res

    if res.get('status') == '1' and res.get('route', {}).get('paths'):
        steps = res['route']['paths'][0]['steps']
        distance = int(res['route']['paths'][0]['distance'])
        duration = int(res['route']['paths'][0]['duration']) // 60
        st.session_state["route_info"] = f"✔️ 路径成功：全程约 {distance} 米，预计 {duration} 分钟"

        all_points = []
        for step in steps:
            polyline = step.get('polyline', '')
            if polyline:
                for pair in polyline.split(';'):
                    try:
                        lng, lat = pair.split(',')
                        lng, lat = float(lng), float(lat)
                        wgs_lng, wgs_lat = gcj02_to_wgs84(lng, lat)
                        all_points.append([wgs_lat, wgs_lng])  # folium经纬度顺序是[纬度, 经度]
                    except:
                        continue
        st.session_state["route_points"] = all_points
    else:
        st.session_state["route_points"] = None
        st.session_state["route_info"] = "❌ 路径计算失败，请检查坐标或 API Key 是否正确。"

center_lng, center_lat = gcj02_to_wgs84((start_lng + float(end_lng)) / 2, (start_lat + float(end_lat)) / 2)
m = folium.Map(
    location=[center_lat, center_lng],
    zoom_start=13,
    control_scale=True
)

start_wgs_lng, start_wgs_lat = gcj02_to_wgs84(start_lng, start_lat)
folium.Marker([start_wgs_lat, start_wgs_lng], popup="起点（微站）", icon=folium.Icon(color='green')).add_to(m)

end_wgs_lng, end_wgs_lat = gcj02_to_wgs84(float(end_lng), float(end_lat))
folium.Marker([end_wgs_lat, end_wgs_lng], popup="终点（火警点）", icon=folium.Icon(color='red')).add_to(m)

if st.session_state["route_points"]:
    folium.PolyLine(st.session_state["route_points"], color="blue", weight=5, opacity=0.8, popup="导航路线").add_to(m)

st_folium(m, width=850, height=600)

if st.session_state["route_info"]:
    st.info(st.session_state["route_info"])

with st.expander("🔎 查看高德API返回数据（调试用）"):
    st.json(st.session_state["route_debug"])

st.caption("© 2025 导航 · OSM底图 · 路名整洁标签美观显示")

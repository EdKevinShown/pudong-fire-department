import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

# 中文字体设置
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

st.set_page_config(layout="wide")
st.title("浦东微站火警点空间分布与覆盖统计分析")

@st.cache_data
def load_data():
    stations = pd.read_csv(r'data\微站地址_已地理编码.csv', encoding='utf-8')
    fires = pd.read_csv(r'data\火警地址_已地理编码_已清洗.csv', encoding='utf-8')
    if stations.columns[0].startswith('\ufeff'):
        stations.columns = [c.replace('\ufeff','') for c in stations.columns]
    if fires.columns[0].startswith('\ufeff'):
        fires.columns = [c.replace('\ufeff','') for c in fires.columns]
    return stations, fires

stations, fires = load_data()
SERVICE_RADIUS = st.slider('选择微站服务半径（米）', 300, 5000, 2000, 100)

@st.cache_data
def prepare_gdf(stations, fires):
    st_gdf = gpd.GeoDataFrame(
        stations,
        geometry=gpd.points_from_xy(stations['微站地址_经度'], stations['微站地址_纬度']),
        crs='EPSG:4326'
    ).to_crs('EPSG:3857')
    fi_gdf = gpd.GeoDataFrame(
        fires,
        geometry=gpd.points_from_xy(fires['经度'], fires['纬度']),
        crs='EPSG:4326'
    ).to_crs('EPSG:3857')
    return st_gdf, fi_gdf

gdf_st, gdf_fi = prepare_gdf(stations, fires)
gdf_st_buffer = gdf_st.copy()
gdf_st_buffer['geometry'] = gdf_st_buffer.geometry.buffer(SERVICE_RADIUS)

# --- 空间分析：统计每站覆盖火警点数量和未覆盖火警点 ---
join_df = gpd.sjoin(gdf_fi, gdf_st_buffer[['geometry', '所属微站']], how='left', predicate='intersects')
fires['被覆盖'] = False
fires['覆盖微站'] = ''
fires.loc[join_df.index, '被覆盖'] = True
def join_station_names(x):
    return ';'.join(str(i) for i in set(x) if pd.notnull(i))
cover_station = join_df.groupby(join_df.index)['所属微站'].agg(join_station_names)
fires.loc[cover_station.index, '覆盖微站'] = cover_station
cover_count = fires['覆盖微站'].str.split(';').explode().value_counts()
cover_df = pd.DataFrame({
    '微站': gdf_st['所属微站'],
    f'服务半径{SERVICE_RADIUS}米_覆盖火警点数': gdf_st['所属微站'].map(cover_count).fillna(0).astype(int)
})

# --- 地图与静态图 ---
gdf_st_latlon = gdf_st.to_crs('EPSG:4326')
gdf_st_buffer_latlon = gdf_st_buffer.to_crs('EPSG:4326')
gdf_fi_latlon = gdf_fi.to_crs('EPSG:4326')

col1, col2 = st.columns([1.5, 2])

with col1:
    st.subheader("各微站覆盖火警点统计")
    st.dataframe(cover_df, use_container_width=True)
    st.write(f'服务半径{SERVICE_RADIUS}米下，未被任何微站覆盖的火警点数量：{(~fires["被覆盖"]).sum()}')
    st.download_button(
        '下载未覆盖火警点CSV',
        fires[~fires['被覆盖']][['立案时间','火警地址','纬度','经度']].to_csv(index=False, encoding='utf-8-sig'),
        file_name='未覆盖火警点.csv',
        mime='text/csv'
    )

    st.subheader("空间分布（静态图）")
    fig, ax = plt.subplots(figsize=(8, 7))
    # 服务区buffer多边形
    gdf_st_buffer_latlon.boundary.plot(ax=ax, color='blue', linewidth=1, alpha=0.3, label='服务区边界')
    # 微站点
    sc1 = ax.scatter(gdf_st_latlon.geometry.x, gdf_st_latlon.geometry.y, s=90, color='blue', marker='o',
               edgecolor='black', linewidth=1, label='微站', zorder=3, alpha=0.97)
    # 所有火警点（统一为红色小星）
    sc2 = ax.scatter(gdf_fi_latlon.geometry.x, gdf_fi_latlon.geometry.y, s=25, color='red', marker='*',
               edgecolor='none', linewidth=0.5, label='火警点', zorder=2, alpha=0.7)
    ax.set_xlabel("经度")
    ax.set_ylabel("纬度")
    ax.set_title(f'空间分布（服务半径{SERVICE_RADIUS}米，仅展示火警点与微站）', fontsize=15, fontweight='bold', pad=12)
    ax.grid(linestyle='--', alpha=0.25)
    # 图例合并，自动选择最佳位置
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='best', ncol=1, fontsize=11, frameon=True, borderpad=1)
    plt.tight_layout()
    st.pyplot(fig)

with col2:
    st.subheader("交互式地图（火警点聚合显示）")
    center_lat = stations['微站地址_纬度'].mean()
    center_lon = stations['微站地址_经度'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True)
    folium.TileLayer(
        tiles='http://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scl=1&style=7&x={x}&y={y}&z={z}',
        attr='高德地图',
        name='高德矢量',
        overlay=False,
        control=True
    ).add_to(m)
    # 服务区buffer多边形
    for idx, row in gdf_st_buffer_latlon.iterrows():
        folium.GeoJson(
            row['geometry'],
            style_function=lambda x: {"color": "blue", "weight": 2, "fillOpacity": 0.07}
        ).add_to(m)
    # 微站点
    for idx, row in gdf_st_latlon.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=8,
            color='blue',
            fill=True,
            fill_color='cyan',
            fill_opacity=0.8,
            popup=f"微站：{row['所属微站']}"
        ).add_to(m)
    # 火警点聚合
    marker_cluster = MarkerCluster(name='火警点聚合').add_to(m)
    for idx, row in fires.iterrows():
        folium.CircleMarker(
            location=[row['纬度'], row['经度']],
            radius=5,
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.7,
            popup=f"火警点：{row['火警地址']}"
        ).add_to(marker_cluster)
    folium.LayerControl().add_to(m)
    st_folium(m, width=700, height=560)
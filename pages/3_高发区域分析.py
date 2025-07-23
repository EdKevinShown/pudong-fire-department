import streamlit as st
import pandas as pd
from sklearn.cluster import KMeans
import plotly.express as px

# ========== 数据加载 ==========
@st.cache_data
def load_data():
    df = pd.read_csv(r"data\火警地址_已清洗.csv", encoding='utf-8')
    if df.columns[0].startswith('\ufeff'):
        df.columns = [col.replace('\ufeff', '') for col in df.columns]
    return df

df = load_data()

st.set_page_config("火警地址空间聚类", layout="wide")
st.title("火警地址KMeans空间聚类分析")

# ========== 选择聚类数 ==========
st.sidebar.markdown("## KMeans聚类参数")
n_clusters = st.sidebar.slider("选择聚类数量", min_value=2, max_value=10, value=4)

# ========== KMeans聚类 ==========
X = df[['纬度', '经度']]
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
df['聚类簇'] = kmeans.fit_predict(X)

# ========== 展示聚类结果地图 ==========
st.markdown(f"#### KMeans聚类结果（共{n_clusters}类）")
fig = px.scatter_mapbox(
    df,
    lat="纬度",
    lon="经度",
    color="聚类簇",
    hover_data=['火警地址', '立案时间'],
    zoom=10,
    height=700,
    mapbox_style="carto-positron"
)
st.plotly_chart(fig, use_container_width=True)

# ========== 展示聚类中心 ==========
centers = kmeans.cluster_centers_
st.markdown("#### 各聚类中心（纬度，经度）：")
for i, c in enumerate(centers):
    st.write(f"第{i+1}类中心: 纬度 {c[0]:.6f}, 经度 {c[1]:.6f}")

# ========== 各簇数量统计 ==========
st.markdown("#### 各簇数量统计：")
st.dataframe(df['聚类簇'].value_counts().sort_index().rename_axis('聚类簇').reset_index(name='数量'))

st.caption("© 2025 火警空间聚类分析 | 支持自定义类数 | 支持地图交互可视化")

# ========== 下载聚类结果 ==========
st.markdown("#### 下载聚类结果")
st.info("如下载后用Excel打开出现中文乱码，请用Excel的“数据”->“自文本/CSV”导入，编码选择UTF-8。")

# 保存一份到服务器本地
df.to_csv(r"data\火警地址_KMeans聚类结果.csv", index=False, encoding='utf-8-sig')
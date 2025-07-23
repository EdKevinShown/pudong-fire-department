import streamlit as st
import pandas as pd
import numpy as np
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import seaborn as sns

# 强制中文支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="浦东消防智能前端", layout="wide")
st.title("浦东消防智能前端大屏展示")

data_root = r'C:\Users\34713\Desktop\vscode\浦东消防\data'

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🌏 全部概率热力图", "📊 模型评估信息", "🔢 混淆矩阵", "⭐ 特征重要性", "📝 测试集预测结果", "📆 未来7天每日预测"
])

with tab1:
    st.subheader("未来7天累计火警概率热力图")
    # 读取预测数据
    future = pd.read_csv(f"{data_root}/fire_pred_next7days_cn.csv", encoding='utf-8-sig')
    # 全部点叠加
    heat_data = future[['纬度网格', '经度网格', '预测有火警概率']].values.tolist()
    center = [31.22, 121.55]
    m = folium.Map(location=center, zoom_start=10, tiles='cartodbpositron')
    HeatMap(
        heat_data, min_opacity=0.2, radius=18, blur=25, max_zoom=1
    ).add_to(m)
    # 可选加geojson边界: folium.GeoJson("shanghai_admin.geojson").add_to(m)
    st_folium(m, width=950, height=650)
    st.info("此图展示未来7天所有网格的预测概率累计热力分布，颜色越红概率越高。")

with tab2:
    st.subheader("模型评估信息")
    info = pd.read_csv(f"{data_root}/fire_model_info.csv", encoding='utf-8-sig')
    st.table(info.T)

with tab3:
    st.subheader("混淆矩阵")
    cmatrix = pd.read_csv(f"{data_root}/fire_confusion_matrix.csv", header=None)
    fig, ax = plt.subplots(figsize=(4,3))
    sns.heatmap(cmatrix, annot=True, fmt='d', cmap='Blues', cbar=False, ax=ax)
    ax.set_xlabel('预测标签')
    ax.set_ylabel('真实标签')
    st.pyplot(fig)

with tab4:
    st.subheader("特征重要性 Top 15")
    fi = pd.read_csv(f"{data_root}/fire_feature_importance.csv", index_col=0, encoding='utf-8-sig')
    fi = fi.sort_values(by=fi.columns[0], ascending=False)
    st.bar_chart(fi.head(15))
    with st.expander("显示全部特征重要性表格"):
        st.dataframe(fi, use_container_width=True)

with tab5:
    st.subheader("测试集预测结果（前100行）")
    result = pd.read_csv(f"{data_root}/fire_pred_result_cn.csv", encoding='utf-8-sig')
    st.dataframe(result.head(100), use_container_width=True)
    st.download_button("下载全部测试集预测结果", result.to_csv(index=False, encoding='utf-8-sig'), "fire_pred_result_cn.csv")

with tab6:
    st.subheader("未来7天每日概率表（可下载）")
    future = pd.read_csv(f"{data_root}/fire_pred_next7days_cn.csv", encoding='utf-8-sig')
    st.dataframe(future.head(100), use_container_width=True)
    st.download_button("下载未来7天每日预测", future.to_csv(index=False, encoding='utf-8-sig'), "fire_pred_next7days_cn.csv")
    # 如果需要按天可视化，去掉tab1的全部热力，写成日期下拉+热力渲染（参考上面历史回复）

st.markdown(
    "<div style='text-align:right;color:#aaa;font-size:13px;'>by ChatGPT & Shuke</div>",
    unsafe_allow_html=True
)

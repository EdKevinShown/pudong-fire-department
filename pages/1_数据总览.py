import streamlit as st
import pandas as pd
import plotly.express as px

# ===== 数据加载与预处理 =====
@st.cache_data
def load_data():
    df = pd.read_csv(r'data\每日火警详情.csv', encoding='utf-8')
    if df.columns[0].startswith('\ufeff'):  # 去除BOM
        df.columns = [col.replace('\ufeff', '') for col in df.columns]
    df['立案时间'] = pd.to_datetime(df['立案时间'])
    df['日期'] = df['立案时间'].dt.date
    df['小时'] = df['立案时间'].dt.hour
    return df

df = load_data()

st.set_page_config("每日火警数据分析", layout="wide")
st.title("每日火警数据分析看板")

##############################
# 1. 数据总览
##############################
with st.expander("📊 数据总览", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("警情总数", len(df))
    col2.metric("实警", (df['实/虚警']=='实警').sum())
    col3.metric("虚警", (df['实/虚警']=='虚警').sum())
    col4.metric("微站数量", df['微站'].nunique())

    st.markdown("#### 火警类型分布")
    fig_type = px.pie(df, names='火警类型', title="火警类型占比", hole=0.4)
    st.plotly_chart(fig_type, use_container_width=True)

##############################
# 2. 区域警情分布
##############################
with st.expander("🗺️ 警情区域分布"):
    area = st.selectbox("选择分组", ['所属街道','所属大队','所属队站'], key='area')
    area_count = df[area].value_counts().reset_index()
    area_count.columns = [area, '警情数']
    fig_area = px.bar(area_count.head(20), x=area, y='警情数', title=f"{area} 警情数Top20")
    st.plotly_chart(fig_area, use_container_width=True)

##############################
# 3. 时间趋势分析
##############################
with st.expander("⏰ 时间趋势分析"):
    tab1, tab2 = st.tabs(['按日期', '按小时'])
    date_count = df.groupby('日期').size()
    tab1.line_chart(date_count)
    hour_count = df.groupby('小时').size()
    tab2.bar_chart(hour_count)

##############################
# 4. 火警类型与处置
##############################
with st.expander("🔥 类型与处置分析"):
    col1, col2 = st.columns(2)
    type_top = df['火警类型'].value_counts().head(5)
    col1.markdown("#### 火警类型TOP5")
    col1.bar_chart(type_top)

    col2.markdown("#### 微站处置方式分布")
    if '微站处置' in df.columns:
        col2.bar_chart(df['微站处置'].fillna("无").value_counts())
    else:
        col2.info("无微站处置字段")

    st.markdown("#### 各类型对应处置方式")
    if '微站处置' in df.columns:
        cross = pd.crosstab(df['火警类型'], df['微站处置'])
        st.dataframe(cross)
    else:
        st.info("无微站处置字段")

##############################
# 5. 多维筛选与原始数据浏览
##############################
with st.expander("🔎 多条件筛选/原始数据浏览"):
    st.markdown("可按类型、街道、实/虚警等多条件筛选查看原始记录")
    col1, col2, col3 = st.columns(3)
    sel_type = col1.multiselect("火警类型", df['火警类型'].unique())
    sel_area = col2.multiselect("所属街道", df['所属街道'].unique())
    sel_real = col3.multiselect("实/虚警", df['实/虚警'].unique())

    mask = pd.Series([True] * len(df))
    if sel_type:
        mask &= df['火警类型'].isin(sel_type)
    if sel_area:
        mask &= df['所属街道'].isin(sel_area)
    if sel_real:
        mask &= df['实/虚警'].isin(sel_real)
    df_view = df[mask]

    st.dataframe(df_view, use_container_width=True, height=400)

##############################
# 6. 其他高级分析
##############################
with st.expander("📈 高级分析"):
    st.markdown("#### 微站出动用时分位数")
    if '微站出动用时' in df.columns:
        used = pd.to_numeric(df['微站出动用时'], errors='coerce')
        # 数据清洗：仅保留0到500分钟内的用时
        used_clean = used[(used >= 0) & (used <= 500)]
        desc = used_clean.describe(percentiles=[.25, .5, .75, .9, .95]).round(2)
        desc_table = pd.DataFrame(desc)
        desc_table.index = [
            "数据条数", "平均用时", "用时波动", "最短用时", "25%用时", "50%用时", 
            "75%用时", "90%用时", "95%用时", "最长用时"
        ]
        desc_table.columns = ["微站出动用时（分钟）"]
        st.dataframe(desc_table)

        # 中文解读
        st.markdown(f"""
- 微站出动用时数据共计 {int(desc['count'])} 条。
- 平均每次用时为 {desc['mean']} 分钟。
- 用时的波动范围为 {desc['std']} 分钟。
- 最短用时为 {desc['min']} 分钟，最长用时为 {desc['max']} 分钟。
- 其中，25%的用时低于 {desc['25%']} 分钟，50%的用时低于 {desc['50%']} 分钟，75%的用时低于 {desc['75%']} 分钟。
- 90%的用时低于 {desc['90%']} 分钟，95%的用时低于 {desc['95%']} 分钟。
        """)
    else:
        st.info("无微站出动用时字段")

    
st.markdown("---")
st.caption("© 2025 火警数据分析 | Streamlit前端交互可视化 | 建议用 streamlit run project.py 启动，无需任何自动打开浏览器代码")
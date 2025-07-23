import pandas as pd
import numpy as np
from datetime import timedelta, date
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, average_precision_score, roc_curve, precision_recall_curve
from imblearn.ensemble import BalancedRandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
import matplotlib.pyplot as plt

# 1. 读取数据
df = pd.read_csv(r'data\火警地址_KMeans聚类结果.csv', encoding='utf-8', parse_dates=['立案时间'])

# 2. 类别特征编码
for col in ['火警类型', '所属大队', '所属街道', '所属队站', '建筑物内/外']:
    df[col] = LabelEncoder().fit_transform(df[col].astype(str))

# 3. 时间特征
df['hour'] = df['立案时间'].dt.hour
df['month'] = df['立案时间'].dt.month
df['weekday'] = df['立案时间'].dt.weekday
df['is_weekend'] = (df['weekday'] >= 5).astype(int)

# 4. 文本高频词特征（自动发现top10）
vectorizer = CountVectorizer(max_features=10, token_pattern=r'[\u4e00-\u9fa5]{2,}')
tfidf = vectorizer.fit_transform(df['备注内容'].astype(str))
for i, word in enumerate(vectorizer.get_feature_names_out()):
    df[f'备注高频_{word}'] = tfidf[:, i].toarray()

# 5. 响应时间/空间特征
df['微站出动用时'] = pd.to_numeric(df['微站出动用时'], errors='coerce').fillna(0)
df['纬度网格'] = (df['纬度'] // 0.01) * 0.01
df['经度网格'] = (df['经度'] // 0.01) * 0.01
df['日期'] = df['立案时间'].dt.date

# 6. 空间聚类
kmeans = KMeans(n_clusters=8, random_state=0)
df['空间聚类'] = kmeans.fit_predict(df[['纬度', '经度']])

# 7. 历史累计特征
df['历史累计火警'] = df.groupby(['纬度网格', '经度网格']).cumcount()

# 8. 网格-日统计
grid_day = df.groupby(['纬度网格', '经度网格', '日期']).size().reset_index(name='火警次数')
all_dates = sorted(df['日期'].unique())
latlons = grid_day[['纬度网格', '经度网格']].drop_duplicates().values

def count_neighbor(grid_day, lat, lon, start_date, end_date):
    delta = 0.01
    neighbor_mask = (
        (grid_day['纬度网格'] >= lat - delta) & (grid_day['纬度网格'] <= lat + delta) &
        (grid_day['经度网格'] >= lon - delta) & (grid_day['经度网格'] <= lon + delta) &
        (grid_day['日期'] >= start_date) & (grid_day['日期'] < end_date)
    )
    return grid_day[neighbor_mask]['火警次数'].sum()

feature_list = []
for day in all_dates[7:]:
    day_dt = pd.to_datetime(day)
    for lat, lon in latlons:
        mask = (
            (grid_day['纬度网格'] == lat) &
            (grid_day['经度网格'] == lon) &
            (grid_day['日期'] >= (day_dt - timedelta(days=7)).date()) &
            (grid_day['日期'] < day_dt.date())
        )
        last7_cnt = grid_day[mask]['火警次数'].sum()
        neighbor_last7_cnt = count_neighbor(
            grid_day, lat, lon,
            (day_dt - timedelta(days=7)).date(), day_dt.date()
        )
        cur_cnt = grid_day[
            (grid_day['纬度网格'] == lat) &
            (grid_day['经度网格'] == lon) &
            (grid_day['日期'] == day_dt.date())
        ]['火警次数'].sum()
        feature_list.append({
            '纬度网格': lat,
            '经度网格': lon,
            '日期': day_dt.date(),
            '过去七天火警数': last7_cnt,
            '邻域过去七天火警数': neighbor_last7_cnt,
            '星期': day_dt.weekday(),
            '有无火警': 1 if cur_cnt > 0 else 0
        })
data = pd.DataFrame(feature_list)
df = pd.merge(df, data, how='left', on=['纬度网格', '经度网格', '日期'])

# 9. 构造特征集
feature_cols = (
    ['纬度网格', '经度网格', '过去七天火警数', '邻域过去七天火警数', 'hour', 'month', 'weekday', 'is_weekend',
     '火警类型', '所属大队', '所属街道', '所属队站', '建筑物内/外', '微站出动用时', '空间聚类', '历史累计火警']
    + [f'备注高频_{w}' for w in vectorizer.get_feature_names_out()]
)
X = df[feature_cols].fillna(0)
y = df['有无火警'].fillna(0).astype(int)

# 10. 划分训练/测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 11. 标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 12. BalancedRandomForestClassifier
model = BalancedRandomForestClassifier(
    n_estimators=100,
    max_depth=12,
    random_state=42,
    n_jobs=-1
)
model.fit(X_train_scaled, y_train)
y_proba = model.predict_proba(X_test_scaled)[:, 1]
threshold = 0.12  # 查全率优先，实际可调
y_pred = (y_proba > threshold).astype(int)

# 13. 评估
report = classification_report(y_test, y_pred, digits=4, output_dict=True)
rocauc = roc_auc_score(y_test, y_proba)
prauc = average_precision_score(y_test, y_proba)
cmatrix = confusion_matrix(y_test, y_pred)
print(classification_report(y_test, y_pred, digits=4))
print("ROC-AUC:", rocauc)
print("PR-AUC:", prauc)
print("混淆矩阵：\n", cmatrix)

# 保存模型评估信息
info = {
    "准确率": report["accuracy"],
    "查准率": report["1"]["precision"],
    "查全率": report["1"]["recall"],
    "F1分数": report["1"]["f1-score"],
    "ROC-AUC": rocauc,
    "PR-AUC": prauc
}
pd.DataFrame([info]).to_csv(r'data\fire_model_info.csv', index=False, encoding='utf-8-sig')
np.savetxt(r'data\fire_confusion_matrix.csv', cmatrix, delimiter=',', fmt='%d')

# 保存特征重要性（如果有）
if hasattr(model, 'feature_importances_'):
    fi = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
    fi.to_csv(r'data\fire_feature_importance.csv', encoding='utf-8-sig')

# 实时显示ROC/PR曲线，不再保存为文件
fpr, tpr, _ = roc_curve(y_test, y_proba)
plt.figure()
plt.plot(fpr, tpr, label='ROC曲线')
plt.xlabel('假阳性率')
plt.ylabel('真阳性率')
plt.title('ROC曲线')
plt.legend()
plt.show()

prec, recall, _ = precision_recall_curve(y_test, y_proba)
plt.figure()
plt.plot(recall, prec, label='PR曲线')
plt.xlabel('召回率')
plt.ylabel('查准率')
plt.title('PR曲线')
plt.legend()
plt.show()

# ------------- 输出全中文表头的结果CSV -------------
result_df = X_test.copy()
result_df['真实标签'] = y_test.values
result_df['预测概率'] = y_proba
result_df['预测标签'] = y_pred
for col in ['日期', 'hour', 'month', 'weekday', '空间聚类']:
    if col in df.columns and col not in result_df.columns:
        result_df[col] = df.loc[result_df.index, col]
rename_dict = {
    '日期': '日期', '经度网格': '经度网格', '纬度网格': '纬度网格',
    'hour': '小时', 'month': '月份', 'weekday': '星期几', '空间聚类': '空间聚类标签',
    '过去七天火警数': '过去七天火警数', '邻域过去七天火警数': '邻域过去七天火警数',
    '真实标签': '真实是否有火警', '预测概率': '预测有火警概率', '预测标签': '预测结果'
}
cols_to_save = [
    '日期', '经度网格', '纬度网格', '小时', '月份', '星期几',
    '空间聚类标签', '过去七天火警数', '邻域过去七天火警数',
    '真实是否有火警', '预测有火警概率', '预测结果'
]
result_df = result_df.rename(columns=rename_dict)
result_df = result_df[[c for c in cols_to_save if c in result_df.columns]]
result_df.to_csv(r'data\fire_pred_result_cn.csv', encoding='utf-8-sig', index=False)

print('已输出模型评估信息、混淆矩阵、特征重要性、ROC和PR曲线、全中文表头预测结果。')

# ------------- 未来7天预测 ----------------
future_days = [date.today() + timedelta(days=i) for i in range(1, 8)]
latlons = df[['纬度网格', '经度网格']].drop_duplicates().values
future_rows = []
for d in future_days:
    for lat, lon in latlons:
        recent = df[(df['纬度网格'] == lat) & (df['经度网格'] == lon)].sort_values('日期', ascending=False).head(1)
        if not recent.empty:
            row = recent.iloc[0].copy()
        else:
            row = pd.Series({k: 0 for k in feature_cols})
        row['纬度网格'] = lat
        row['经度网格'] = lon
        row['日期'] = d
        row['hour'] = 12
        row['month'] = d.month
        row['weekday'] = d.weekday()
        row['is_weekend'] = int(row['weekday'] >= 5)
        future_rows.append(row)
future_df = pd.DataFrame(future_rows)
X_future = future_df[feature_cols].fillna(0)
X_future_scaled = scaler.transform(X_future)
future_df['预测有火警概率'] = model.predict_proba(X_future_scaled)[:, 1]

future_out_cols = ['日期', '经度网格', '纬度网格', '预测有火警概率', 'hour', 'month', 'weekday']
future_rename_dict = {
    '日期': '日期', '经度网格': '经度网格', '纬度网格': '纬度网格',
    'hour': '小时', 'month': '月份', 'weekday': '星期几',
    '预测有火警概率': '预测有火警概率'
}
future_df = future_df.rename(columns=future_rename_dict)
future_df = future_df[[c for c in ['日期','经度网格','纬度网格','小时','月份','星期几','预测有火警概率'] if c in future_df.columns]]
future_df.to_csv(r'data\fire_pred_next7days_cn.csv', encoding='utf-8-sig', index=False)
print('已输出未来7天全网格火警概率预测：fire_pred_next7days_cn.csv')

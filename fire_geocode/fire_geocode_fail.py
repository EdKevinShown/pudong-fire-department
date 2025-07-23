import pandas as pd
import requests
import time
from tqdm import tqdm

# 读取文档
df = pd.read_csv(r"C:\Users\RAZER\OneDrive\桌面\vscode\浦东消防\data\地址试案\火警地址.csv")  # 替换为实际路径

df['立案时间'] = pd.to_datetime(df['立案时间'])
df['月份'] = df['立案时间'].dt.to_period('M')
grouped = df.groupby('月份')

api_key = "67be5dbd248dad17c40d09d83fef5537"  # 替换为你的高德key

def geocode_amap(address, api_key, city="上海", retries=3):
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {"key": api_key, "address": address, "city": city, "output": "json"}
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=10)
            js = r.json()
            if js["status"] == "1" and js["geocodes"]:
                lon, lat = js["geocodes"][0]["location"].split(",")
                return float(lat), float(lon), "成功"
            else:
                return None, None, f"失败: {js.get('info')}"
        except Exception as e:
            time.sleep(5)
    return None, None, "失败: 多次重试失败"

updated_rows = []
for month, group in grouped:
    print(f"\n处理月份: {month}")
    for idx, row in tqdm(group.iterrows(), total=len(group), desc=f"处理 {month} 批次"):
        row_dict = row.to_dict()
        if "失败" in str(row_dict.get('地理编码状态', '')):  # 只处理失败的
            address = row_dict['火警地址']
            lat, lon, status = geocode_amap(address, api_key)
            # 覆盖对应字段
            row_dict['纬度'] = lat if lat is not None else row_dict.get('纬度')
            row_dict['经度'] = lon if lon is not None else row_dict.get('经度')
            row_dict['地理编码状态'] = status
            time.sleep(1)
        # 追加全部字段（无论是否重试）
        updated_rows.append(row_dict)

updated_df = pd.DataFrame(updated_rows)

# 保存全部字段
updated_df.to_csv(r"C:\Users\RAZER\OneDrive\桌面\vscode\浦东消防\data\地址试案\火警地址(1).csv", index=False, encoding="utf-8-sig")
print("处理完成！更新文件已保存。")

# 失败日志
failures = updated_df[updated_df['地理编码状态'].astype(str).str.contains("失败", na=False)]
failures.to_csv(r"C:\Users\RAZER\OneDrive\桌面\vscode\浦东消防\data\地址试案\失败日志.csv", index=False, encoding="utf-8-sig")
print(f"仍有 {len(failures)} 条失败，已保存到失败日志.csv")
import pandas as pd
import requests
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 读取你的表格
df = pd.read_csv(r"C:\Users\RAZER\OneDrive\桌面\vscode\浦东消防\data\每日火警详情.csv")

# 定义清洗函数
def clean_address(address):
    if pd.isna(address):
        return address
    keywords = r'(误报|到场未处置|居民处置|其他社会力量处置|燃烧物质燃尽|消防处置|祭扫|驻防车出动|微站处置|专职队处置|单位自处|经核实无需消防处置|自动喷淋装置作用|燃烧物燃尽|车主处置|物业处置|祭祀|祭扫|EB|九小场所|自动喷淋装置作用|燃烧物质燃烬|可燃物质燃尽)'
    pattern = r'\s*\(' + keywords + r'\)\s*'
    cleaned = re.sub(pattern, '', str(address))
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

# 应用清洗
df["火警地址"] = df["火警地址"].apply(clean_address).str.strip()

# 删除“误报”地址
df = df[~df["火警地址"].astype(str).str.contains("误报", na=False)]

# 按立案时间降序
df['立案时间'] = pd.to_datetime(df['立案时间'])
df = df.sort_values(by='立案时间', ascending=False)

api_key = "21d4e687d2bf7268022e38fde34ca5b6"
geocode_cache = {}

def geocode_amap(address, api_key, city="上海"):
    if address in geocode_cache:
        return geocode_cache[address]
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": api_key,
        "address": address,
        "output": "json",
        "city": city
    }
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=5)
            r.raise_for_status()
            js = r.json()
            if js.get("status") == "1" and js.get("geocodes"):
                lon, lat = js["geocodes"][0]["location"].split(",")
                result = (float(lat), float(lon), "成功")
            else:
                result = (None, None, f"失败: {js.get('info')}")
            geocode_cache[address] = result
            return result
        except Exception as e:
            print(f"警告: 地址 '{address}' 调用失败 (尝试 {attempt+1}/3) - 原因: {e}")
            time.sleep(1)
    result = (None, None, f"错误: 多次重试失败 - {e}")
    geocode_cache[address] = result
    return result

def process_row(row):
    addr = row.get("火警地址")
    if pd.isna(addr) or not str(addr).strip():
        return {**row.to_dict(), "纬度": None, "经度": None, "地理编码状态": "地址为空"}
    try:
        lat, lon, status = geocode_amap(str(addr), api_key)
        time.sleep(0.2)
        return {**row.to_dict(), "纬度": lat, "经度": lon, "地理编码状态": status}
    except Exception as e:
        print(f"错误: 处理地址 '{addr}' 时异常 - {e}")
        return {**row.to_dict(), "纬度": None, "经度": None, "地理编码状态": f"异常: {e}"}

results = []
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(process_row, row) for _, row in df.iterrows()]
    for future in tqdm(as_completed(futures), total=len(futures), desc="处理进度"):
        results.append(future.result())

# 不过滤列，保留所有原始字段+新加的3列
out_df = pd.DataFrame(results)

# 保存
out_df.to_csv(r"C:\Users\RAZER\OneDrive\桌面\vscode\浦东消防\data\地址试案\火警地址.csv", index=False, encoding="utf-8-sig")
print("OK 已导出为 火警地址_已地理编码.csv")
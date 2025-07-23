# coding: utf-8
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pandas as pd
import os

def format_dt_no_leading_zero(ts):
    """把 Timestamp 转成 M/D/YYYY H:MM（去秒、去前导零）"""
    if pd.isna(ts):
        return ""
    return f"{ts.month}/{ts.day}/{ts.year} {ts.hour}:{ts.minute:02d}"

def main():
    # 1. 读取原始 XLSX 文件
    input_path = r'C:\Users\RAZER\OneDrive\桌面\vscode\浦东消防\data\每日火警详情.xlsx'
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到输入文件：{input_path}")
    df = pd.read_excel(input_path)

    # 2. 删除不需要的列
    columns_to_drop = ['中队出警用时', 'zzjly', 'ddjq', '中队到场用时']
    df = df.drop(columns=[col for col in columns_to_drop if col in df.columns])

    # 3. 重排列顺序以匹配目标 CSV
    desired_order = [
        '立案时间', '火警地址', '火警类型', '所属大队', '所属街道',
        '实/虚警', '所属队站', '备注内容', '微站',
        '微站调派时间', '微站出动时间', '微站到场时间', '微站出动用时',
        '中队到场时间', '微站出水情况', '微站处置', '建筑物内/外', '中队出动时间'
    ]
    missing = [col for col in desired_order if col not in df.columns]
    if missing:
        raise KeyError(f"以下列在原表中不存在，请检查列名：{missing}")
    df = df[desired_order]

    # 4. 删除关键列有空值的行
    required_cols = [
        '微站调派时间', '微站出动时间', '所属大队',
        '微站到场时间', '微站出动用时',
        '中队到场时间', '中队出动时间',
        '所属队站', '微站'
    ]
    df = df.dropna(subset=required_cols)

    # 5. 格式化所有的时间列（去掉秒数、去除前导零）
    time_cols = [
        '立案时间', '微站调派时间', '微站出动时间',
        '微站到场时间', '中队到场时间', '中队出动时间'
    ]
    for col in time_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
        df[col] = df[col].apply(format_dt_no_leading_zero)

    # 6. 微站处置归并（批量归并+侦查警戒复杂合并）
    if "微站处置" in df.columns:
        # 基础归并
        replace_dict = {
            # 警戒类
            '警戒管控': '警戒', '警戒监控': '警戒', '侦查警戒': '警戒', '周边警戒': '警戒',
            '周围警戒': '警戒', '外围警戒': '警戒', '现场警戒': '警戒', '到场警戒': '警戒', '查看警戒': '警戒',
            # 出水类
            '出水': '出水处置', '出水监护': '出水处置', '出水堵截': '出水处置', '出水降温': '出水处置',
            '到场出水': '出水处置', '破拆出水': '出水处置', '使用手台泵出水': '出水处置',
            # 排查类
            '周边排查': '排查', '现场排查': '排查', '上楼排查': '排查', '寻找火点': '排查', '上去查看': '排查',
            '周边寻找': '排查', '上楼查看': '排查', '寻找火源': '排查', '查看情况': '排查',
            # 监护类
            '现场监护': '监护',
            # 配合处置
            '配合中队警戒': '配合处置', '配合中队处置': '配合处置', '配合队站处置': '配合处置', '协助队站处置': '配合处置',
            '配合中队周围搜寻': '配合处置', '配合队站进行排查': '配合处置', '配合消防站处置': '配合处置',
            # 灭火器
            '使用1个灭火器': '使用灭火器', '使用灭火器处置': '使用灭火器',
            # 人员疏散
            '疏散人员': '人员疏散',
            # 堵截
            '控制堵截': '堵截',
        }
        df["微站处置"] = df["微站处置"].astype(str).str.strip().replace(replace_dict)

        # 侦查警戒相关复合项归并
        df['微站处置'] = df['微站处置'].replace('侦查警戒，出水处置', '侦查警戒,出水处置')
        df['微站处置'] = df['微站处置'].replace('侦查警戒疏散人员控控制堵截', '侦查警戒,人员疏散,堵截')
        df['微站处置'] = df['微站处置'].replace('侦查警戒、疏散人员', '侦查警戒,人员疏散')
        df['微站处置'] = df['微站处置'].replace('侦查警戒2', '侦查警戒')
        df['微站处置'] = df['微站处置'].replace('侦查警戒、人员疏散', '侦查警戒,人员疏散')
        df['微站处置'] = df['微站处置'].replace('控控制堵截', '堵截')

        # 复合项"侦查警戒"转"警戒"（如“侦查警戒,出水处置”等）
        def merge_jingjie(val):
            if pd.isna(val):
                return val
            s = str(val)
            parts = [p.strip() for p in s.split(',')]
            parts = ['警戒' if p == '侦查警戒' else p for p in parts]
            # 去重且保持顺序
            seen = set()
            parts_no_dup = []
            for x in parts:
                if x not in seen:
                    seen.add(x)
                    parts_no_dup.append(x)
            return ','.join(parts_no_dup)
        df['微站处置'] = df['微站处置'].apply(merge_jingjie)

    # 7. 保存为新的 CSV
    output_path = r'C:\Users\RAZER\OneDrive\桌面\vscode\浦东消防\data\每日火警详情.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n已导出清洗后 CSV：{output_path}\n")

    # 8. 控制台预览
    print("=== 清洗后数据预览（前 5 行） ===")
    print(df.head().to_string(index=False))
    if "微站处置" in df.columns:
        print("\n处理后的微站处置唯一值:")
        print(df["微站处置"].unique())
        print("\n处理后的微站处置统计:")
        print(df["微站处置"].value_counts())

if __name__ == "__main__":
    main()

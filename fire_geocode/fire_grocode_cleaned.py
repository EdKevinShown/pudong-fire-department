import pandas as pd

# 输入文件路径
input_file = r"data\地址试案\火警地址(1).csv"
# 输出文件路径
output_file = r"data\火警地址_已清洗.csv"

# 读取CSV，指定编码防止中文乱码
df = pd.read_csv(input_file, encoding='utf-8-sig')

# 只保留“地理编码状态”为“成功”的行，所有字段都会被保留
cleaned_df = df[df['地理编码状态'] == '成功']

# 删除“月份”列（如果有）
if '月份' in cleaned_df.columns:
    cleaned_df = cleaned_df.drop(columns=['月份'])

# 保存清洗后的新CSV，所有字段都在
cleaned_df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"清洗完成！已删除失败行并移除'月份'列。新文件保存为: {output_file}")
print(f"原始行数: {len(df)}, 清洗后行数: {len(cleaned_df)}")
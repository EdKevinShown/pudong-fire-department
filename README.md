# 浦东消防智能数据分析平台

## 项目介绍
本项目基于浦东消防火警数据，进行数据清洗、地理编码、聚类分析及火警风险预测，辅助消防管理与决策。

## 项目结构
- 预处理  
  - `data_clean.py`：数据清洗  
  - `generate_fire_predict.py`：火警预测模型生成  

- data  
  - 各类原始和中间数据文件，包含火警地址、编码结果、聚类结果等  

- fire_geocode  
  - 地理编码相关脚本  

- pages  多页面功能模块，包含以下脚本：  
  - `1_数据总览.py`：展示火警数据的整体情况与统计分析  
  - `2_点位分布地图.py`：展示火警点位的地理分布地图  
  - `3_高发区域分析.py`：分析火警高发区域及相关特征  
  - `4_风险趋势预测.py`：基于模型预测未来火警风险趋势  
  - `5_微站路径导航.py`：微站地址及路径导航功能  

- 首页导航.py  
  - Streamlit应用主入口脚本  

## 环境依赖
- Python 3.7+  
- pandas, numpy, scikit-learn, imbalanced-learn, matplotlib, streamlit等

安装依赖示例：
```bash
pip install -r requirements.txt
```
## 使用说明

1. 数据预处理  
   - 运行 `预处理/data_clean.py` 对原始数据进行清洗，包括缺失值处理、编码转换等。  
   - 运行 `预处理/generate_fire_predict.py` 基于清洗后的数据训练火警风险预测模型，并生成预测结果文件。

2. 地理编码  
   - 运行 `fire_geocode/fire_geocode_address.py` 对火警地址进行批量地理编码，获取经纬度信息。  
   - 若部分地址编码失败，使用 `fire_geocode/fire_geocode_fail.py` 进行补充编码处理。  
   - 运行 `fire_geocode/fire_grocode_cleaned.py` 清理并整合编码后的数据，保证数据完整性。

3. 启动多页面可视化平台  
   - 确认已安装所需依赖。  
   - 在项目根目录执行命令启动 Streamlit 应用：

     ```bash
     streamlit run 首页导航.py
     ```

   - 使用左侧导航栏浏览不同功能页面：  
     - 数据总览  
     - 点位分布地图  
     - 高发区域分析  
     - 风险趋势预测  
     - 微站路径导航

4. 其他  
   - 若需要调整数据路径或参数，请修改对应脚本中的配置项。  
   - 脚本中均有详细注释，便于理解和二次开发。

## 运营维护

本项目由张展（zhangzhan）负责运营维护，欢迎反馈问题与建议。

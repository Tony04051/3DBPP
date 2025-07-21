# config.py
# 存放所有可調整的參數
# --- 生成箱子參數 ---
# 物品尺寸和重量的範圍
NUM_ITEMS = 10  # 生成的物品數量
ITEM_DIMENSIONS_RANGE = {
    'length': (10, 100),  # 單位: cm
    'width': (1, 100),   # 單位: cm
    'height': (10, 100),   # 單位: cm
    'weight': (1, 30)  # 單位: kg
}
# --- 籠車參數 ---
# (長, 寬, 高)，單位: cm
CAGE_DIMENSIONS = (100, 100, 150) 
CAGE_WEIGHT_LIMIT = 300 # 單位: kg

# --- 演算法參數 ---
# 機器視覺的尺寸量測誤差，會加到每個物品的長寬高上
MEASUREMENT_ERROR = 3.0
# 暫存區最大容量 (暫時未使用)
TEMP_AREA_CAPACITY = 3
# 系統可往前看的貨物數量 (暫時未使用)
LOOKAHEAD_DEPTH = 3
# 穩定度因子：貨物底部需與支撐面接觸面積的最小比例
STABILITY_FACTOR = 0.7

# --- 評分函式權重 ---
W_Z_SCORE = 1.0
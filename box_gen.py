# 生成測試用item list

import csv 
import pandas as pd
import random
from bpp_solver.data_structures import Item
from config import NUM_ITEMS, ITEM_DIMENSIONS_RANGE 
conveyor_items = []
# 生成隨機物品
for i in range(NUM_ITEMS):
    item_id = i+1
    length = random.randint(*ITEM_DIMENSIONS_RANGE['length'])
    width = random.randint(*ITEM_DIMENSIONS_RANGE['width'])
    height = random.randint(*ITEM_DIMENSIONS_RANGE['height'])
    weight = random.randint(*ITEM_DIMENSIONS_RANGE['weight'])
    
    item = Item(
        id=item_id,
        base_dimensions=(length, width, height),
        position=None,  # 初始位置為 None
        allowed_rotations=list(range(6)),  # 允許所有旋轉方向
        weight=weight
    )
    conveyor_items.append(item)
    print(conveyor_items)
conveyor_items_df = pd.DataFrame([item.__dict__ for item in conveyor_items])
conveyor_items_df.to_csv('conveyor_items.csv', index=False, encoding='utf-8')

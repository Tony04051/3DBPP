# 生成測試用item list

import csv
import os 
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

    allowed_rotations = []
    # 隨機決定三種情形
    x1 = random.randint(0, 10)
    x2 = random.randint(0, 10)
    x3 = random.randint(0, 10)
    p1 = x1 / (x1 + x2 + x3)
    p2 = x2 / (x1 + x2 + x3)
    p3 = x3 / (x1 + x2 + x3)
    # 隨機決定三種情形
    # 1. 允許所有旋轉
    if max(p1, p2, p3) == p1:
        allowed_rotations = list(range(6))
    # 2. 不允許翻轉
    elif max(p1, p2, p3) == p2:
        allowed_rotations = [0, 1]  
    # 3. 不允許翻轉也不允許旋轉
    else:
        allowed_rotations = [0]

    item = Item(
        id=item_id,
        base_dimensions=(length, width, height),
        allowed_rotations=allowed_rotations,
        weight=weight,
        is_fragile=False  # 假設所有物品都不是易碎的
    )
    conveyor_items.append(item)
    print(conveyor_items)
conveyor_items_df = pd.DataFrame([item.__dict__ for item in conveyor_items])

if not os.path.exists('cases'):
    os.makedirs('cases')

i = 0
while i >= 0:
    print(i)
    if not os.path.exists(f'cases/conveyor_items_{i}.csv'): 
        conveyor_items_df.to_csv(f'cases/conveyor_items_{i}.csv', index=False, encoding='utf-8')
        break
    else:
        i += 1   

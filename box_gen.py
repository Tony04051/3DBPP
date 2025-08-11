# 生成測試用item list

import csv
import os 
import pandas as pd
import random
from bpp_solver.data_structures import Item
from config import NUM_ITEMS, ITEM_DIMENSIONS_RANGE, CAGE_DIMENSIONS, CAGE_WEIGHT_LIMIT
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
    # print(conveyor_items)
conveyor_items_df = pd.DataFrame([item.__dict__ for item in conveyor_items])

if not os.path.exists('cases'):
    os.makedirs('cases')

i = 0
while i >= 0:
    # print(i)
    if not os.path.exists(f'cases/conveyor_items_{i}.csv'): 
        conveyor_items_df.to_csv(f'cases/conveyor_items_{i}.csv', index=False, encoding='utf-8')
        break
    else:
        i += 1   
# 計算生成物體總體積與重量
total_volume = sum(item.calc_dimensions[0] * item.calc_dimensions[1] * item.calc_dimensions[2] for item in conveyor_items)
total_weight = sum(item.weight for item in conveyor_items)
print(f"總體積: {total_volume} cm³")
print(f"總重量: {total_weight} kg")
# 平均尺寸
average_dimensions = (
    sum(item.calc_dimensions[0] for item in conveyor_items) / NUM_ITEMS,
    sum(item.calc_dimensions[1] for item in conveyor_items) / NUM_ITEMS,
    sum(item.calc_dimensions[2] for item in conveyor_items) / NUM_ITEMS
)
print(f"平均尺寸: {average_dimensions[0]:.2f} cm x {average_dimensions[1]:.2f} cm x {average_dimensions[2]:.2f} cm")
# 平均重量
average_weight = total_weight / NUM_ITEMS
print(f"平均重量: {average_weight:.2f} kg")
# 籠車與物品的比例
cage_volume = CAGE_DIMENSIONS[0] * CAGE_DIMENSIONS[1] * CAGE_DIMENSIONS[2]
cage_weight_limit = CAGE_WEIGHT_LIMIT
print(f"籠車與所有貨物體積比例: {total_volume / cage_volume:.2f}")  

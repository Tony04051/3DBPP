# main.py(heuristic cp)
import argparse
import pandas as pd
import random
import csv
import time
import copy
# import numpy as np
from typing import cast
from ..data_structures import Item, CageTrolley
from ..CP.Heuristics.packer import Packer
from config import *

def load_items_from_csv(file_path: str):
    """從指定的 CSV 檔案路徑載入貨物列表。"""
    conveyor_items = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 確保維度資料是乾淨的
                dims_str = row['base_dimensions'].strip('() ')
                raw_dims = tuple(map(float, dims_str.split(',')))
                
                # 確保旋轉資料是乾淨的
                rotations_str = row['allowed_rotations'].strip('[]"\' ')
                if rotations_str:
                    allowed_rotations = [int(num) for num in rotations_str.split(',')]
                else:
                    allowed_rotations = []

                item = Item(
                    id=int(row['id']),
                    base_dimensions=cast(tuple[float, float, float], raw_dims),
                    weight=float(row['weight']),
                    allowed_rotations=allowed_rotations,
                    is_fragile=(row['is_fragile'].lower() == 'true')
                )
                conveyor_items.append(item)
    except FileNotFoundError:
        print(f"錯誤: 檔案不存在 {file_path}")
        return []
    except Exception as e:
        print(f"讀取 CSV '{file_path}' 時發生錯誤: {e}")
        return []
    return conveyor_items

def perform_single_simulation(initial_item_list: list[Item]):
    """
    執行一次完整的裝箱模擬。
    接收一個貨物列表，回傳一個包含結果的字典。
    """
    
    # --- 每次模擬都使用全新的籠車和 Packer ---
    cage = CageTrolley(
        id="C001(cp-heuristics)",
        dimensions=CAGE_DIMENSIONS,
        weight_limit=CAGE_WEIGHT_LIMIT
    )
    packer = Packer()
    
    # --- 狀態管理 ---
    # 使用傳入物品列表的深拷貝，以免影響原始列表
    conveyor_items = copy.deepcopy(initial_item_list)
    temp = []
    
    # --- 主迴圈 ---
    time_counter  = []
    while conveyor_items or temp:
        conveyor_lookahead = conveyor_items[:LOOKAHEAD_DEPTH]
        candidate_items_repo = temp + conveyor_lookahead
        candidate_items = candidate_items_repo[:4]

        if not candidate_items:
            break
        t0 = time.time()
        best_placement = packer.pack(cage, candidate_items)
        t1 = time.time()
        if best_placement:
            selected_item = best_placement['item']
            
            # 從暫存區或輸送帶移除已放置的物品
            item_found_and_removed = False
            for i, item in enumerate(temp):
                if item.id == selected_item.id:
                    temp.pop(i)
                    item_found_and_removed = True
                    break
            if not item_found_and_removed:
                 for i, item in enumerate(conveyor_items):
                    if item.id == selected_item.id:
                        conveyor_items.pop(i)
                        break
        else:
            # 異常處理
            if conveyor_items and len(temp) < TEMP_AREA_CAPACITY:
                item_to_move = conveyor_items.pop(0)
                temp.append(item_to_move)
                continue
            else:
                break
        time_counter.append(t1 - t0)
        
    
    
    # --- 計算結果 ---
    total_volume = 0
    for item in cage.packed_items:
        # 假設 Item 物件在放置後會有 calc_dimensions 屬性
        if hasattr(item, 'calc_dimensions'):
            dims = item.calc_dimensions
            total_volume += dims[0] * dims[1] * dims[2]
        else: # 備用計算
            dims = item.get_rotated_dimensions(item.rotation_type)
            total_volume += dims[0] * dims[1] * dims[2]

    cage_volume = CAGE_DIMENSIONS[0] * CAGE_DIMENSIONS[1] * CAGE_DIMENSIONS[2]
    utilization = (total_volume / cage_volume) * 100 if cage_volume > 0 else 0

    return {
        "packed_items_count": len(cage.packed_items),
        "final_weight": cage.current_weight,
        "utilization_percent": utilization,
        "average_packing_time": sum(time_counter)/ len(time_counter) if time_counter else 0
    }

def run_experiment(num_datasets: int, num_shuffles: int):
    """
    執行完整的隨機實驗並報告結果。
    """
    print("="*60)
    print(f"開始執行隨機順序實驗...")
    print(f"資料集數量: {num_datasets}, 每個資料集隨機模擬次數: {num_shuffles}")
    print("="*60)
    
    all_results = []

    for i in range(num_datasets):
        dataset_id = f"Dataset_{i+1}"
        file_path = f'./cases/conveyor_items_{i}.csv'
        
        print(f"\n--- 正在處理資料集: {dataset_id} ({file_path}) ---")
        
        original_items = load_items_from_csv(file_path)
        if not original_items:
            print(f"無法載入資料集 {dataset_id}，跳過。")
            continue
            
        dataset_results = []
        for j in range(num_shuffles):
            print(f"  -> 正在進行第 {j+1}/{num_shuffles} 次隨機模擬...")
            
            # 建立一個列表的副本並打亂順序
            shuffled_items = original_items[:]
            random.shuffle(shuffled_items)
            
            # 執行單次模擬
            result = perform_single_simulation(shuffled_items)
            result['dataset_id'] = dataset_id
            result['run_id'] = j + 1
            dataset_results.append(result)
        
        all_results.extend(dataset_results)

    if not all_results:
        print("沒有任何模擬成功執行，無法產生報告。")
        return

    # --- 步驟 4: 統計與報告 ---
    print("\n\n" + "="*60)
    print("實驗完成！結果統計報告：")
    print("="*60)
    
    # 使用 pandas 進行數據分析
    df = pd.DataFrame(all_results)
    
    # 設定顯示選項
    pd.set_option('display.precision', 2)
    
    # 按資料集分組並計算統計數據
    summary = df.groupby('dataset_id').agg(
        avg_packed_items=('packed_items_count', 'mean'),
        std_packed_items=('packed_items_count', 'std'),
        avg_utilization=('utilization_percent', 'mean'),
        std_utilization=('utilization_percent', 'std'),
        min_utilization=('utilization_percent', 'min'),
        max_utilization=('utilization_percent', 'max'),
        avg_time=('average_packing_time', 'mean')
    ).reset_index()

    print(summary.to_string(index=False))
    
    print("\n" + "-"*60)
    print("報告說明:")
    print("  - avg_packed_items: 平均放置物品數量")
    print("  - std_packed_items: 放置物品數量的標準差 (值越小代表演算法對順序變化的穩健度越高)")
    print("  - avg_utilization: 平均空間利用率 (%)")
    print("  - std_utilization: 空間利用率的標準差 (值越小代表穩健度越高)")
    print("  - min/max_utilization: 20 次隨機實驗中的最差與最佳表現")
    print("  - average_packing_time:    每次選擇最佳方案耗時 (秒)")
    print("="*60)
    
    # (可選) 將詳細結果儲存到 CSV
    df.to_csv("experiment_detailed_results.csv", index=False, encoding='utf-8-sig')
    print("\n詳細結果已儲存至 experiment_detailed_results.csv")


if __name__ == "__main__":
    # 您可以在這裡設定要運行的資料集數量和每個資料集的隨機次數
    NUM_DATASETS = 5
    NUM_SHUFFLES_PER_DATASET = 20
    run_experiment(NUM_DATASETS, NUM_SHUFFLES_PER_DATASET)

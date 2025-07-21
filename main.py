# main.py

import argparse
import csv
# import numpy as np
from typing import cast, Tuple
from bpp_solver.data_structures import Item, CageTrolley
from bpp_solver.surface_manager import SurfaceManager
from bpp_solver.packer import Packer
from config import *

def run_packing_simulation(args):

    # --- Phase 0: 系統初始化 ---
    print("="*40)
    print("系統初始化...")
    surface_manager = SurfaceManager(merge_surfaces=args.merge)
    cage = CageTrolley(
        id="C001", 
        dimensions=CAGE_DIMENSIONS, 
        weight_limit=CAGE_WEIGHT_LIMIT
    )
    packer = Packer(cage, surface_manager)
    print(f"籠車 {cage.id} 已準備好。")
    print("="*40)

    # --- 模擬輸送帶上的貨物 ---
    # 實際應用中，這會從 conveyor_interface 獲取
    # 示例中從 CSV 讀取
    conveyor_items = []
    try:
        with open('conveyor_items_val.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_dims = tuple(map(float, row['base_dimensions'].strip('()').split(',')))
                item = Item(
                        id=int(row['id']),
                        base_dimensions=cast(Tuple[float, float, float], raw_dims),
                        weight=float(row['weight']),
                        # 修正3: allowed_rotations 處理 (假設 CSV 中是 '0,1,2,3,4,5' 這種格式)
                        allowed_rotations=list(map(int, row['allowed_rotations'].strip('[]').split(','))),
                        # 修正4: is_fragile 處理 (將字串 'True'/'False' 轉為布林值)
                        is_fragile=(row['is_fragile'].lower() == 'true')
                    )
                conveyor_items.append(item)
    except FileNotFoundError:
        print("錯誤: 找不到 'conveyor_items.csv' 檔案。請確認檔案是否存在。")
        return # 找不到檔案就直接結束程式
    except Exception as e:
        print(f"讀取 CSV 時發生錯誤: {e}")
        return
    # 暫存區
    temp = []

    # --- 主迴圈 ---
    item_counter = 0
    while conveyor_items or temp:
        item_counter += 1
        print(f"\n--- 裝箱迴圈 #{item_counter} ---")
        
        # 步驟 1: 候選物品盤點 (這裡我們簡化為輸送帶上所有物品)
        conveyor_lookahead = conveyor_items[:LOOKAHEAD_DEPTH]
        # 合併兩個列表
        candidate_items = conveyor_lookahead + temp
        print(f"候選物品: {[item.id for item in candidate_items]}")

        if not candidate_items:
            break
        
        # 步驟 2: 尋找全局最佳放置方案
        print("正在尋找最佳放置方案...")
        best_placement = packer.pack(candidate_items)
        print(f"最佳放置方案: {best_placement}")
        # 步驟 3: 決策與執行
        if best_placement:
            selected_item = best_placement['item']
            print(f"決策: 選擇物品 {selected_item.id} 進行放置。")
            
            # 步驟 4: 狀態更新
            packer.execute_placement(best_placement)
            
            # 從暫存區移除已放置的物品
            if selected_item in temp:
                temp.remove(selected_item)
            else:
                # 如果不在暫存區，則從輸送帶中移除
                conveyor_items.remove(selected_item)
            
        else:
            # 步驟 3 (續): 異常處理
            print("\n!!! 警告: 找不到任何可行的放置方案。")
            # 嘗試將輸送帶最前端的物品移入暫存區
            if conveyor_items and len(temp) < TEMP_AREA_CAPACITY:
                item_to_move = conveyor_items.pop(0) # 從輸送帶移除最前端的
                temp.append(item_to_move)
                print(f"將物品 {item_to_move.id} 從輸送帶移入暫存區。")
                continue # 進入下一次迴圈，用新的候選物品組合再試一次
            else:
                if not conveyor_items:
                    print("輸送帶已空，且暫存區物品無法放置。")
                elif len(temp) >= TEMP_AREA_CAPACITY:
                    print("暫存區已滿，且無法放置任何物品。")
                
                print("模擬結束。")
                break
            
    print("\n" + "="*40)
    print("裝箱模擬結束。")
    print(f"總共放置了 {len(cage.packed_items)} 個物品。")
    print(f"最終籠車重量: {cage.current_weight:.2f}kg / {cage.weight_limit}kg")
    print("="*40)
    # 可視化結果
    from visualizer import plot_cage_plotly 
    plot_cage_plotly(cage, title="3D Bin Packing Result")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="3D Bin Packing Simulation")
    
    parser.add_argument(
        '--merge', 
        action='store_true', 
        help='啟用相鄰平面合併功能'
    )
    
    parsed_args = parser.parse_args()
    run_packing_simulation(parsed_args)
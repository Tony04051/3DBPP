# bpp_solver/packer.py

from typing import Dict, Any
import math

from .data_structures import Item, CageTrolley
from .surface_manager import SurfaceManager
from . import constraints as con
from .scoring import calculate_placement_score

class Packer:
    def __init__(self, cage: CageTrolley, surface_manager: SurfaceManager):
        self.cage = cage
        self.surface_manager = surface_manager

    def pack(self, candidate_items: list[Item]) -> Dict[str, Any] | None:
        """
        依分數選擇最佳放置物品與其方向
        return: 一個包含最佳放置方案的字典，如果找不到任何可行方案則返回 None。
        """
        best_placement = {
            'score': -math.inf, 
            'item': None, 
            'position': None, 
            'rotation_type': None
        }

        # 步驟 1: 遍歷所有候選物品
        for item in candidate_items:
            # 步驟 2.1: 遍歷所有旋轉下的l,w,h
            for rotation_type in item.allowed_rotations:
                item_dims = item.get_rotated_dimensions(rotation_type)
                
                # 步驟 2.2: 遍歷所有可用的支撐平面
                # 按照 Bottom-Left 策略對平面進行排序
                sorted_surfaces = sorted(
                    self.cage.support_surfaces, 
                    key=lambda s: (s.z, s.rect[1], s.rect[0]) # z -> y_min -> x_min
                )
                
                for surface in sorted_surfaces:
                    # 在該平面上，放置點就是其左下角
                    # (x_min, y_min, z)
                    placement_point = (surface.rect[0], surface.rect[1], surface.z)
                    
                    # 檢查此放置點是否能容納物品
                    # 平面必須足夠大
                    if surface.rect[2] - surface.rect[0] < item_dims[0] or \
                       surface.rect[3] - surface.rect[1] < item_dims[1]:
                        continue # 平面太小，跳到下一個平面

                    # 步驟 2.3: 約束檢查
                    is_valid = con.is_placement_valid(
                        cage=self.cage,
                        item=item,
                        position=placement_point,
                        rotation_type=rotation_type
                    )

                    if is_valid:
                        # 步驟 2.4: 如果放置有效，計算分數
                        score = calculate_placement_score(placement_point)
                        
                        # 步驟 2.5: 如果分數更高，則更新最佳方案
                        if score > best_placement['score']:
                            best_placement['score'] = score
                            best_placement['item'] = item
                            best_placement['position'] = placement_point
                            best_placement['rotation_type'] = rotation_type
                            
        # 迴圈結束後，檢查是否找到了可行的方案
        if best_placement['item'] is not None:
            return best_placement
        else:
            return None

    def execute_placement(self, placement: Dict[str, Any]):
        """
        執行一個放置方案並更新籠車狀態。
        """
        item = placement['item']
        position = placement['position']
        rotation_type = placement['rotation_type']
        
        # 1. 將物品正式加入籠車的 packed_items 列表
        self.cage.add_item(item, position, rotation_type)
        
        # 2. 調用 surface_manager 更新支撐平面
        self.cage.support_surfaces = self.surface_manager.update_support_surfaces(
            placed_item=item,
            all_surfaces=self.cage.support_surfaces,
        )
        
        # 3. (可選) 重新計算籠車重心等狀態 (目前已在 add_item 中隱含處理)
        #    如果 CageTrolley 有 center_of_gravity 屬性，可以在此處更新
        #    self.cage.recalculate_center_of_gravity()
        
        print(f"籠車狀態已更新。當前重量: {self.cage.current_weight:.2f}kg, "
              f"剩餘支撐平面: {len(self.cage.support_surfaces)}個。")
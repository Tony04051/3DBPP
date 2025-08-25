from typing import Dict, Any
import math
from ...data_structures import Item, CageTrolley
from ..surface_manager import SurfaceManager
from ..constraints import is_placement_valid
from ..scoring import calculate_placement_score

class Packer:
    def __init__(self):
        print("EMS Heuristic Packer 初始化:")
        self.surface_manager = SurfaceManager()

    def pack(self, cage: CageTrolley, candidate_items: list[Item]) -> Dict[str, Any] | None:
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
        # 按照 Bottom-Left 策略對平面進行排序
        sorted_surfaces = sorted(
                    cage.support_surfaces, 
                    key=lambda s: (s.z, s.rect[1], s.rect[0]) # z -> y_min -> x_min
                )
        # print(sorted_surfaces)
        for item in candidate_items:
            for rotation_type in item.allowed_rotations:
                for surface in sorted_surfaces:
                    # 在該平面上，放置點就是其左下角
                    # (x_min, y_min, z)
                    pos = (surface.rect[0], surface.rect[1], surface.z)
                    is_valid = is_placement_valid(
                        cage=cage,
                        item=item,
                        position=pos,
                        rotation_type=rotation_type
                    )

                    if is_valid:
                        # 步驟 2.4: 如果放置有效，計算分數
                        score = calculate_placement_score(pos)
                        
                        # 步驟 2.5: 如果分數更高，則更新最佳方案
                        if score > best_placement['score']:
                            best_placement['score'] = score
                            best_placement['item'] = item
                            best_placement['position'] = pos
                            best_placement['rotation_type'] = rotation_type
                            
        # 迴圈結束後，檢查是否找到了可行的方案
        if best_placement['item'] is not None:
            self.execute_placement(cage, best_placement)
            return best_placement
        else:
            return None

    def execute_placement(self, cage: CageTrolley, placement: Dict[str, Any]):
        """
        執行放置方案並更新籠車狀態
        """
        item = placement['item']
        position = placement['position']
        rotation_type = placement['rotation_type']
        
        # 1. 將物品正式加入籠車的 packed_items 列表
        cage.add_item(item, position, rotation_type)
        
        # 2. 調用 surface_manager 更新支撐平面
        new_surfaces = self.surface_manager.update_support_surfaces(
            placed_item=cage.packed_items[-1],
            all_surfaces=cage.support_surfaces
        )
        if new_surfaces is not None:
            cage.support_surfaces = new_surfaces
        
        print(f"籠車狀態已更新。當前重量: {cage.current_weight:.2f}kg, "
              f"EMS數量: {len(cage.support_surfaces)}個。")
        # print("剩餘支撐平面列表:"
        #       f"{[f'平面{idx}: z={s.z}, rect={s.rect}' for idx, s in enumerate(self.cage.support_surfaces)]}")
# bpp_solver/packer.py

from typing import Dict, Any, List, Tuple
import math
from config import *
from ...data_structures import Item, CageTrolley
from .. import constraints as con
from ..scoring import calculate_placement_score

TOLERANCE = 1e-6

class Packer:
    def pack(self, cage: CageTrolley, candidate_items: list[Item]) -> Dict[str, Any] | None:
        """
        遍歷所有 corner points，為所有候選物品尋找最佳放置方案。
        """
        best_placement = {
            'score': -math.inf, 
            'item': None, 
            'position': None, 
            'rotation_type': None
        }

        # 依 y, x, z 排序 corner points，實現 Bottom-Left 策略
        sorted_points = sorted(cage.corner_points, key=lambda p: (p[1], p[0], p[2]))

        for item in candidate_items:
            for rotation_type in item.allowed_rotations:
                # 遍歷所有可用的放置點
                for point in sorted_points:
                    placement_point = point
                    
                    # 約束檢查
                    is_valid = con.is_placement_valid(
                        cage=cage,
                        item=item,
                        position=placement_point,
                        rotation_type=rotation_type
                    )

                    if is_valid:
                        # 如果放置有效，計算分數
                        score = calculate_placement_score(placement_point)
                        
                        # 如果分數更高，則更新最佳方案
                        if score > best_placement['score']:
                            best_placement['score'] = score
                            best_placement['item'] = item
                            best_placement['position'] = placement_point
                            best_placement['rotation_type'] = rotation_type

        if best_placement['item'] is not None:
            """
            執行放置方案並更新籠車狀態
            """
            item = best_placement['item']
            position = best_placement['position']
            rotation_type = best_placement['rotation_type']
            
            # 1. 將物品正式加入籠車的 packed_items 列表
            cage.add_item(item, position, rotation_type)
            
            # 2. 更新 corner_points
            self._update_corner_points(cage, item)
            
            print(f"籠車狀態已更新。當前重量: {cage.current_weight:.2f}kg, "
                f"corner points: {len(cage.corner_points)}個。")
            return best_placement
        else:
            return None

    def _update_corner_points(self, cage: CageTrolley, placed_item: Item):
        """
        在放置一個新物品後，更新 corner_points 列表。
        1. 移除被佔用的點。
        2. 生成新物品的三個頂角作為新點。
        3. 移除所有現在位於某個物品內部的點。
        """
        if placed_item.position is None:
            return

        pos = placed_item.position
        dims = placed_item.get_rotated_dimensions(placed_item.rotation_type)
        
        px, py, pz = pos
        dx, dy, dz = dims

        # 新物品的邊界
        item_x_max, item_y_max, item_z_max = px + dx, py + dy, pz + dz

        # 1. 生成新物品的三個頂角作為新的潛在放置點
        new_points = [
            (px + dx, py, pz),
            (px, py + dy, pz),
            (px, py, pz + dz)
        ]
        
        # 2. 將新點加入現有列表，並移除被佔用的點
        updated_points = cage.corner_points
        
        # 移除剛才使用的放置點
        if pos in updated_points:
            updated_points.remove(pos)

        # 3. 遍歷所有點，移除位於任何已放置物品內部的點
        final_points: List[Tuple[float, float, float]] = []
        
        # 將新生成的點也加入待過濾列表
        all_potential_points = list(set(updated_points + new_points))

        for point in all_potential_points:
            # 檢查點是否在籠車邊界外
            if (point[0] >= CAGE_DIMENSIONS[0]- TOLERANCE or
                point[1] >= CAGE_DIMENSIONS[1] - TOLERANCE or
                point[2] >= CAGE_DIMENSIONS[2] - TOLERANCE):
                continue

            # 檢查點是否在任何已放置物品的內部
            is_inside = False
            for p_item in cage.packed_items:
                if p_item.position is None: continue
                p_dims = p_item.get_rotated_dimensions(p_item.rotation_type)
                p_pos = p_item.position
                
                # 檢查點是否嚴格位於物品內部（不含邊界）
                if (p_pos[0] - TOLERANCE < point[0] < p_pos[0] + p_dims[0] - TOLERANCE and
                    p_pos[1] - TOLERANCE < point[1] < p_pos[1] + p_dims[1] - TOLERANCE and
                    p_pos[2] - TOLERANCE < point[2] < p_pos[2] + p_dims[2] - TOLERANCE):
                    is_inside = True
                    break
            
            if not is_inside:
                final_points.append(point)

        # 去重後更新到籠車狀態
        cage.corner_points = sorted(list(set(final_points)))
# bpp_solver/surface_manager.py

from ..data_structures import Item, SupportSurface
from .geometry import Rect, get_intersection_area

class SurfaceManager:
    def update_support_surfaces(
        self,
        placed_item: Item,
        all_surfaces: list[SupportSurface]
    ):
        """
        核心函式：在成功放置一個物品後，更新支撐平面列表。
        1. 切割舊平面 
        2. 創建新平面
        3. 合併相鄰平面
        """
        item_dims = placed_item.get_rotated_dimensions(placed_item.rotation_type)
        if placed_item.position == None:
            raise ValueError(f"放置物品 {placed_item.id} 的位置未定義。請先確定物品已被正確放置。")
        item_footprint = (
            placed_item.position[0],
            placed_item.position[1],
            placed_item.position[0] + item_dims[0],  # d (length)
            placed_item.position[1] + item_dims[1],  # w (width)
        )
        
        item_z = placed_item.position[2]

        unaffected_surfaces = []
        affected_surfaces = []

        # 1. 將所有平面分為「受影響」和「未受影響」兩組
        for surface in all_surfaces:
            # 判斷條件：
            # a) 高度必須與物品底部一致
            # b) 在 XY 平面上必須與物品的足跡有交集
            is_at_correct_z = surface.z - item_z ==0
            intersection_area = get_intersection_area(surface.rect, item_footprint)
            
            if intersection_area > 0:
                affected_surfaces.append(surface)
            else:
                unaffected_surfaces.append(surface)

        # 2. 處理所有受影響的平面，計算它們被 "挖掉" 後的剩餘部分
        remaining_surfaces = []
        for surface in affected_surfaces:
            # 對於每一個受影響的平面，都用 item_footprint 去切割它
            # _cut_surface 函式會返回切割後剩餘的矩形列表
            remaining_parts = self._cut_surface(surface, item_footprint)
            remaining_surfaces.extend(remaining_parts)

        # 3. 在物品頂部創建一個新平面
        new_top_surface = SupportSurface(
            z=item_z + item_dims[2],
            rect=item_footprint,
            supporting_items=[str(placed_item.id)]
        )

        # 4. 組合最終的平面列表
        # (未受影響的 + 受影響的剩餘部分 + 新的頂部平面)
        final_surfaces = unaffected_surfaces + remaining_surfaces + [new_top_surface]

        # 5. 合併相鄰平面以簡化計算
        merge_surface = self._merge_surfaces(final_surfaces)
        return merge_surface
        
        
    def _cut_surface(self, surface: SupportSurface, cutter_rect: Rect) -> list[SupportSurface]:
        """
        從一個平面(surface)中，挖掉一個矩形區域(cutter_rect)。
        返回切割後剩餘的、有效的 SupportSurface 列表。
        這是一個健壯的切割算法。
        """
        remaining_rects = []
        s_xmin, s_ymin, s_xmax, s_ymax = surface.rect
        c_xmin, c_ymin, c_xmax, c_ymax = cutter_rect

        # 計算實際的交集，因為切割器可能比平面大
        inter_xmin = max(s_xmin, c_xmin)
        inter_ymin = max(s_ymin, c_ymin)
        inter_xmax = min(s_xmax, c_xmax)
        inter_ymax = min(s_ymax, c_ymax)

        # 根據交集矩形，產生四個可能的新平面
        # 1. 下方區域 (Below)
        if inter_ymin > s_ymin:
            remaining_rects.append((s_xmin, s_ymin, s_xmax, inter_ymin))
        # 2. 上方區域 (Above)
        if inter_ymax < s_ymax:
            remaining_rects.append((s_xmin, inter_ymax, s_xmax, s_ymax))
        # 3. 左方區域 (Left)
        if inter_xmin > s_xmin:
            remaining_rects.append((s_xmin, s_ymin, inter_xmin, s_ymax))
        # 4. 右方區域 (Right)
        if inter_xmax < s_xmax:
            remaining_rects.append((inter_xmax, s_ymin, s_xmax, s_ymax))

        # 將有效的矩形轉換為 SupportSurface 物件
        new_surfaces = []
        for rect in remaining_rects:
            if rect[0] < rect[2] and rect[1] < rect[3]:  # 確保是有效的矩形
                new_surfaces.append(SupportSurface(
                    z=surface.z,
                    rect=rect,
                    supporting_items=surface.supporting_items
                ))
        return new_surfaces

    def _merge_surfaces(self, surfaces: list[SupportSurface]) -> list[SupportSurface]:
            """
            合併所有高度相同且在XY平面上相鄰並有一邊完美對齊的平面
            """
            # 按 z 值分組
            surfaces_by_z = {}
            for s in surfaces:
                if s.z not in surfaces_by_z:
                    surfaces_by_z[s.z] = []
                surfaces_by_z[s.z].append(s)

            merged_surfaces = []
            for z, group in surfaces_by_z.items():
                # 只要該高度的平面多於一個，就嘗試合併
                while len(group) > 1:
                    merged_one_pair = False
                    # 暴力遍歷所有對，尋找可合併的
                    for i in range(len(group)):
                        for j in range(i + 1, len(group)):
                            s1, s2 = group[i], group[j]
                            merged_rect = self._try_merge_two_rects(s1.rect, s2.rect)
                            
                            if merged_rect:
                                # 成功合併，創建新平面，並從 group 中移除舊的兩個
                                new_supporting_items = list(set(s1.supporting_items + s2.supporting_items))
                                merged_s = SupportSurface(z, merged_rect, new_supporting_items)
                                
                                # 移除舊的平面 (注意從後往前刪除避免 index 錯亂)
                                group.pop(j)
                                group.pop(i)
                                
                                group.append(merged_s)
                                merged_one_pair = True
                                break # 跳出內層迴圈
                        if merged_one_pair:
                            break # 跳出外層迴圈
                    
                    # 如果遍歷完所有對都無法合併，則結束該高度的合併
                    if not merged_one_pair:
                        break
                
                # 將該高度處理完的平面加入最終列表
                merged_surfaces.extend(group)
                
            return merged_surfaces

    def _try_merge_two_rects(self, r1: Rect, r2: Rect) -> Rect | None:
        """嘗試合併兩個矩形，如果可以合併則返回新矩形，否則返回 None"""
        x_min1, y_min1, x_max1, y_max1 = r1
        x_min2, y_min2, x_max2, y_max2 = r2
        
        # 沿 X 軸合併 (左右相鄰)
        if x_max1 == x_min2 and y_min1 == y_min2 and y_max1 == y_max2:
            return (x_min1, y_min1, x_max2, y_max1)
        if x_max2 == x_min1 and y_min1 == y_min2 and y_max1 == y_max2:
            return (x_min2, y_min1, x_max1, y_max1)
            
        # 沿 Y 軸合併 (上下相鄰)
        if y_max1 == y_min2 and x_min1 == x_min2 and x_max1 == x_max2:
            return (x_min1, y_min1, x_max1, y_max2)
        if y_max2 == y_min1 and x_min1 == x_min2 and x_max1 == x_max2:
            return (x_min1, y_min2, x_max1, y_max1)
            
        return None
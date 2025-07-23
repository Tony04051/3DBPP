# bpp_solver/surface_manager.py

from .data_structures import Item, SupportSurface
from .geometry import Rect, is_rect_completely_contained

class SurfaceManager:
    def __init__(self, merge_surfaces: bool = True):
        # merge_surfaces: 平面合併
        self.merge_surfaces = merge_surfaces
        print(f"SurfaceManager 初始化，平面合併功能: {'啟用' if merge_surfaces else '停用'}")

    def update_support_surfaces(
        self,
        placed_item: Item,
        all_surfaces: list[SupportSurface]
    ) -> list[SupportSurface]:
        """
        核心函式：在成功放置一個物品後，更新支撐平面列表。
        1. 切割舊平面 
        2. 創建新平面
        3. (可選) 合併相鄰平面
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
        
        new_surfaces = []
        
        # --- 1. 切割與更新舊平面 ---
        for surface in all_surfaces:
            # 檢查物品是否在這個平面上
            if not (surface.z < placed_item.position[2] + 0.1 and \
                    is_rect_completely_contained(item_footprint, surface.rect)):
                # 如果物品不在這個平面上，或者平面在物品之上，則保留原平面
                new_surfaces.append(surface)
                continue

            # 如果物品在這個平面上，則對該平面進行切割
            # 根據 item_footprint 將 surface.rect 切割成最多四個新的矩形
            cut_surfaces = self._cut_surface(surface, item_footprint)
            new_surfaces.extend(cut_surfaces)

        # --- 2. 創建新平面 ---
        # 在 placed_item 的頂部創建一個新的 SupportSurface
        new_top_surface = SupportSurface(
            z=placed_item.position[2] + item_dims[2], # h (height)
            rect=item_footprint,
            supporting_items=[str(placed_item.id)]
        )
        new_surfaces.append(new_top_surface)

        # --- 3. (可選) 合併相鄰平面 ---
        if self.merge_surfaces:
            return self._merge_surfaces(new_surfaces)
        else:
            return new_surfaces

    def _cut_surface(self, surface: SupportSurface, item_footprint: Rect) -> list[SupportSurface]:
        """將一個平面根據物品佔據的區域切割成多個小平面"""
        cut_rects = []
        s_xmin, s_ymin, s_xmax, s_ymax = surface.rect
        i_xmin, i_ymin, i_xmax , i_ymax = item_footprint
        
        # 根據物品佔據的矩形，產生四個可能的剩餘矩形區域
        # 1. 下方區域 
        if i_ymin > s_ymin:
            cut_rects.append((s_xmin, s_ymin, s_xmax, i_ymin))
        # 2. 上方區域
        if i_ymax < s_ymax:
            cut_rects.append((s_xmin, i_ymax, s_xmax, s_ymax))
        # 3. 左方區域 
        if i_xmin > s_xmin:
            cut_rects.append((s_xmin, i_ymin, i_xmin, i_ymax))
        # 4. 右方區域 
        if i_xmax < s_xmax:
            cut_rects.append((i_xmax, i_ymin, s_xmax, i_ymax))
            
        # 將有效的矩形轉換為 SupportSurface 物件
        new_surfaces = []
        for rect in cut_rects:
            if rect[0] < rect[2] and rect[1] < rect[3]: # 確保是有效的矩形
                new_surfaces.append(SupportSurface(
                    z=surface.z,
                    rect=rect,
                    supporting_items=surface.supporting_items
                ))
        return new_surfaces

    def _merge_surfaces(self, surfaces: list[SupportSurface]) -> list[SupportSurface]:
        """
        合併所有高度相同且在XY平面上相鄰的平面。
        這是一個比較複雜的貪婪算法。
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
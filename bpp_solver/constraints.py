from .data_structures import Item, CageTrolley, SupportSurface
from .geometry import get_intersection_area
from config import STABILITY_FACTOR, MERGE_MARGIN

def is_placement_valid(
    cage: CageTrolley,
    item: Item,
    position: tuple[float, float, float],
    rotation_type: int
) -> bool:
    """
    調用所有constraints檢查一個放置方案是否有效
    check_weight_constraint: 是否超重
    check_stability_constraint: 物品堆疊穩不穩
    check_collision_constraint: 物品會不會與其他物品重疊
    check_center_of_gravity_constraint: 籠車會不會倒(需要籠車重量和重心，暫不啓用)
    """
    rotated_dims = item.get_rotated_dimensions(rotation_type)
    counter = 0
    if not check_boundary_constraint(cage, position, rotated_dims):
        counter +=1
    if not check_weight_constraint(cage, item):
        counter += 1 
    if not check_stackable_constraint(cage, item, position, rotated_dims):
        counter += 1
    if not check_collision_constraint(cage, position, rotated_dims):
        counter += 1
    # if not check_center_of_gravity_constraint(cage, item, position, rotation_type):
    #     counter += 1
    return counter == 0


def check_boundary_constraint(
    cage: CageTrolley, 
    pos: tuple[float, float, float], 
    dims: tuple[float, float, float]
) -> bool:
    """檢查物品是否超出籠車的邊界"""
    px, py, pz = pos
    dl, dw, dh = dims
    cl, cw, ch = cage.dimensions
    
    # 加上一個很小的容忍值避免浮點數精度問題
    TOLERANCE = 1e-6

    return (px + dl <= cl + TOLERANCE and
            py + dw <= cw + TOLERANCE and
            pz + dh <= ch + TOLERANCE)

def check_weight_constraint(cage: CageTrolley, item: Item) -> bool:
    """檢查是否超重"""
    return cage.current_weight + item.weight <= cage.weight_limit

def check_stackable_constraint(
    cage: CageTrolley, 
    item: Item,
    pos: tuple[float, float, float],
    dims: tuple[float, float, float]
) -> bool:
    """檢查支撐面積是否滿足穩定度因子, 75% 的底面積表示種心一定落在支撐平面上"""
    item_footprint = (pos[0], pos[1], pos[0] + dims[0], pos[1] + dims[1])
    item_bottom_area = dims[0] * dims[1]
    
    # 防呆
    if item_bottom_area == 0:
        return True 

    total_supported_area = 0.0
    for surface in cage.support_surfaces:
        # 只有當支撐平面 z 值與物品底部 z 值非常接近時才計算，把這個z平面所有跟物品有交集的平面都算進去
        if abs(surface.z - pos[2]) < MERGE_MARGIN:
            total_supported_area += get_intersection_area(item_footprint, surface.rect)
            
    required_area = item_bottom_area * STABILITY_FACTOR
            
    return total_supported_area >= required_area - 1e-6


def check_collision_constraint(
    cage: CageTrolley,
    pos: tuple[float, float, float],
    dims: tuple[float, float, float]
) -> bool:
    """
    1. 檢查新放置的物品是否會與籠車中的物品重疊
    2. 透過檢查特定方向的插入體積是否與已放置物品碰撞，解決實務操作上貨品只能從頂部或一側面插入的問題
    """
    # 插入新物品需要的空間
    # 1. 從頂部插入
    x1_min, y1_min, z1_min = pos
    x1_max_up = x1_min + dims[0]
    y1_max_up = y1_min + dims[1]
    z1_max_up = cage.dimensions[2] # 高度不變，從頂部插入
    # 2. 從一側面插入, 假設是x = (0, 100), y = 0
    x1_min, y1_min, z1_min = pos
    x1_max_s = x1_min + dims[0]
    y1_max_s = cage.dimensions[1]
    z1_max_s = z1_min + dims[2]

    # 遍歷所有已經放置的物品
    for packed_item in cage.packed_items:
        packed_pos = packed_item.position
        packed_dims = packed_item.get_rotated_dimensions(packed_item.rotation_type)

        # 已放置物品的邊界框 (box2)
        if packed_pos is None:
            continue
        x2_min, y2_min, z2_min = packed_pos
        x2_max = x2_min + packed_dims[0]
        y2_max = y2_min + packed_dims[1]
        z2_max = z2_min + packed_dims[2]

        # 判斷 box1 和 box2 是否重疊(三個軸上的投影都重疊)
        TOLERANCE = 1e-6
        
        x_overlap_up = (x1_min < x2_max - TOLERANCE) and (x1_max_up > x2_min + TOLERANCE)
        y_overlap_up = (y1_min < y2_max - TOLERANCE) and (y1_max_up > y2_min + TOLERANCE)
        z_overlap_up = (z1_min < z2_max - TOLERANCE) and (z1_max_up > z2_min + TOLERANCE)

        x_overlap_s = (x1_min < x2_max - TOLERANCE) and (x1_max_s > x2_min + TOLERANCE) 
        y_overlap_s = (y1_min < y2_max - TOLERANCE) and (y1_max_s > y2_min + TOLERANCE)
        z_overlap_s = (z1_min < z2_max - TOLERANCE) and (z1_max_s > z2_min + TOLERANCE) 

        if (x_overlap_up and y_overlap_up and z_overlap_up) and\
           (x_overlap_s and y_overlap_s and z_overlap_s):
            # 兩種插入方式都不可行
            # 但凡有一維重疊，就認為有碰撞
            return False
        
    return True
# 拆成是否重疊、夾取路徑是否通暢兩個函式
# 箱子只能從上方放入
# def check_collision_constraint(
#     cage: CageTrolley,
#     pos: tuple[float, float, float],
#     dims: tuple[float, float, float]
# ) -> bool:
#     """
#     檢查新放置的物品是否會與籠車中的物品重疊
#     """
#     # 1. 從頂部插入
    # x1_min, y1_min, z1_min = pos
    # x1_max_up = x1_min + dims[0]
    # y1_max_up = y1_min + dims[1]
    # z1_max_up = cage.dimensions[2] - z1_min  # 高度不變，從頂部插入

#     # 遍歷所有已經放置的物品
#     for packed_item in cage.packed_items:
#         packed_pos = packed_item.position
#         packed_dims = packed_item.get_rotated_dimensions(packed_item.rotation_type)
        
#         # 已放置物品的邊界框 (box2)
#         if packed_pos is None:
#             continue
#         x2_min, y2_min, z2_min = packed_pos
#         x2_max = x2_min + packed_dims[0]
#         y2_max = y2_min + packed_dims[1]
#         z2_max = z2_min + packed_dims[2]

#         # 判斷 box1 和 box2 是否重疊
#         # 兩個盒子重疊，若且唯若它們在三個軸上的投影都重疊
#         # 為了避免浮點數精度問題，在比較時加入一個小的容差
#         TOLERANCE = 1e-6
        
#         x_overlap = (x1_min < x2_max - TOLERANCE) and (x1_max > x2_min + TOLERANCE)
#         y_overlap = (y1_min < y2_max - TOLERANCE) and (y1_max > y2_min + TOLERANCE)
#         z_overlap = (z1_min < z2_max - TOLERANCE) and (z1_max > z2_min + TOLERANCE)

#         if x_overlap and y_overlap and z_overlap:
#             # 只要和任何一個已存在的物品碰撞，就立即返回 True (有碰撞)
#             return True

#     # 如果遍歷完所有已存在的物品都沒有碰撞，返回 False (無碰撞)
#     return False

def check_center_of_gravity_constraint(
    cage: CageTrolley, 
    item: Item,
    pos: tuple[float, float, float],
    rotation_type: int 
) -> bool:
    """計算放置物品後籠車的新重心，檢查其投影是否在籠車底板的安全區域內"""
    # 1. 計算籠車現有物品的總重量和加權位置 (Σ(m*p))
    total_weight = cage.current_weight
    sum_wx, sum_wy, sum_wz = 0, 0, 0
    for packed_item in cage.packed_items:
        item_dims = packed_item.get_rotated_dimensions(packed_item.rotation_type)
        item_pos = packed_item.position
        if item_pos is None:
            continue
        item_center = (
            item_pos[0] + item_dims[0] / 2,
            item_pos[1] + item_dims[1] / 2,
            item_pos[2] + item_dims[2] / 2
        )
        sum_wx += packed_item.weight * item_center[0]
        sum_wy += packed_item.weight * item_center[1]
        sum_wz += packed_item.weight * item_center[2]
        
    # 2. 加入新物品的資訊
    new_item_dims = item.get_rotated_dimensions(rotation_type)
    new_item_center = (
        pos[0] + new_item_dims[0] / 2,
        pos[1] + new_item_dims[1] / 2,
        pos[2] + new_item_dims[2] / 2
    )
    
    final_total_weight = total_weight + item.weight
    if final_total_weight == 0: return True
    
    final_sum_wx = sum_wx + item.weight * new_item_center[0]
    final_sum_wy = sum_wy + item.weight * new_item_center[1]
    
    # 3. 計算放置後的新重心投影 (CoG_x, CoG_y)
    new_cog_x = final_sum_wx / final_total_weight
    new_cog_y = final_sum_wy / final_total_weight
    
    # 4. 檢查新重心是否在安全區域內
    SAFETY_MARGIN_RATIO = 0.8
    cage_l, cage_w, _ = cage.dimensions
    
    safe_x_min = cage_l * (1 - SAFETY_MARGIN_RATIO) / 2
    safe_x_max = cage_l * (1 + SAFETY_MARGIN_RATIO) / 2
    safe_y_min = cage_w * (1 - SAFETY_MARGIN_RATIO) / 2
    safe_y_max = cage_w * (1 + SAFETY_MARGIN_RATIO) / 2
    
    return (safe_x_min <= new_cog_x <= safe_x_max and
            safe_y_min <= new_cog_y <= safe_y_max)


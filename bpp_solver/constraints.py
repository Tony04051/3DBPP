from .data_structures import Item, CageTrolley, SupportSurface
from .geometry import get_intersection_area
from config import STABILITY_FACTOR

def is_placement_valid(
    cage: CageTrolley,
    item: Item,
    position: tuple[float, float, float],
    rotation_type: int
) -> bool:
    """
    總檢查函式: 調用所有constraints檢查一個放置方案是否有效
    check_weight_constraint: 是否超重
    check_stability_constraint: 物品堆疊穩不穩
    check_center_of_gravity_constraint: 籠車會不會倒
    """
    rotated_dims = item.get_rotated_dimensions(rotation_type)

    if not check_boundary_constraint(cage, position, rotated_dims):
        print(f"放置物品 {item.id} 失敗: 超出籠車邊界。")
        return False
    
    if not check_weight_constraint(cage, item):
        print(f"放置物品 {item.id} 失敗: 超過籠車重量限制。")
        return False
        
    if not check_stability_constraint(cage, item, position, rotated_dims):
        print(f"放置物品 {item.id} 失敗: 支撐面積不足以確保穩定性。")
        return False
        
    # *** 修改點 1: 將 rotation_type 傳遞下去 ***
    if not check_center_of_gravity_constraint(cage, item, position, rotation_type):
        print(f"放置物品 {item.id} 失敗: 籠車重心不穩定。")
        return False
    
    return True

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

    return (px >= -TOLERANCE and
            py >= -TOLERANCE and
            pz >= -TOLERANCE and
            px + dl <= cl + TOLERANCE and
            py + dw <= cw + TOLERANCE and
            pz + dh <= ch + TOLERANCE)

def check_weight_constraint(cage: CageTrolley, item: Item) -> bool:
    """檢查是否超重"""
    return cage.current_weight + item.weight <= cage.weight_limit

def check_stability_constraint(
    cage: CageTrolley, 
    item: Item,
    pos: tuple[float, float, float],
    dims: tuple[float, float, float]
) -> bool:
    """檢查支撐面積是否滿足穩定度因子, 70% 的底面積表示種心一定落在支撐平面上"""
    item_footprint = (pos[0], pos[1], pos[0] + dims[0], pos[1] + dims[1])
    item_bottom_area = dims[0] * dims[1]
    
    # 防呆
    if item_bottom_area == 0:
        return True 

    total_supported_area = 0.0
    for surface in cage.support_surfaces:
        # 只有當支撐平面 z 值與物品底部 z 值非常接近時才計算
        if abs(surface.z - pos[2]) < 1e-6:
            total_supported_area += get_intersection_area(item_footprint, surface.rect)
            
    required_area = item_bottom_area * STABILITY_FACTOR
    
    return total_supported_area >= required_area - 1e-6

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
    # *** 修改點 3: 使用傳入的 rotation_type ***
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


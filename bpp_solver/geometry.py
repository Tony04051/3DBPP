# bpp_solver/geometry.py

Rect = tuple[float, float, float, float]  # (x_min, y_min, x_max, y_max)

def get_rect_area(rect: Rect) -> float:
    """計算矩形的面積"""
    x_min, y_min, x_max, y_max = rect
    if x_min >= x_max or y_min >= y_max:
        return 0.0
    return (x_max - x_min) * (y_max - y_min)

def get_intersection_area(rect1: Rect, rect2: Rect) -> float:
    """計算兩個矩形的交集面積"""
    x_min1, y_min1, x_max1, y_max1 = rect1
    x_min2, y_min2, x_max2, y_max2 = rect2

    # 計算交集矩形的邊界
    inter_x_min = max(x_min1, x_min2)
    inter_y_min = max(y_min1, y_min2)
    inter_x_max = min(x_max1, x_max2)
    inter_y_max = min(y_max1, y_max2)

    # 如果沒有交集，寬度或高度會是負數或零
    if inter_x_min >= inter_x_max or inter_y_min >= inter_y_max:
        return 0.0
    
    return (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)

def is_rect_completely_contained(inner_rect: Rect, outer_rect: Rect) -> bool:
    """檢查 inner_rect 是否完全被 outer_rect 包含"""
    x_min_in, y_min_in, x_max_in, y_max_in = inner_rect
    x_min_out, y_min_out, x_max_out, y_max_out = outer_rect
    
    return (x_min_in >= x_min_out and
            y_min_in >= y_min_out and
            x_max_in <= x_max_out and
            y_max_in <= y_max_out)
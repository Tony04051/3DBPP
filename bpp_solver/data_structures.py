# bpp_solver/data_structures.py

from dataclasses import dataclass, field, asdict
from config import MEASUREMENT_ERROR
from typing import Any
# --- Phase 0: Data Structures ---

@dataclass
class Item:
    """
    id(int), base_dimensions(貨物實際大小), weight,position: 貨物左下角座標, 
    allowed_rotations(list[rotation_type]), 
    rotation_type: 0: (l, w, h), 1: (w, l, h), 2: (l, h, w), 3: (h, l, w), 4: (w, h, l), 5: (h, w, l)
    is_fragile(bool)是否易碎
    calc_dimensions(貨物+量測預估誤差)
    get_rotated_dimensions(): 根據旋轉類型返回計算後的貨物尺寸 (d, w, h)
    """
    id: int
    # 原始尺寸
    base_dimensions: tuple[float, float, float]  # (長, 寬, 高)
    weight: float
    # 放置後的資訊 (在被裝箱後才會被賦值)
    position: tuple[float, float, float] | None= None  # (x, y, z) in the cage
    # 允許的旋轉方向列表 [0-5]
    # 0: (l, w, h), 1: (w, l, h), 2: (l, h, w), 3: (h, l, w), 4: (w, h, l), 5: (h, w, l)
    allowed_rotations: list[int] = field(default_factory=lambda: list(range(6)))
    rotation_type: int = 0  # 使用了哪個旋轉方向
    is_fragile: bool = False
    
    # 用於計算的尺寸，已加上誤差
    # 這個屬性將在初始化後計算
    calc_dimensions: tuple[float, float, float] = field(init=False)

    def __post_init__(self):
        """在物件初始化後，自動加上量測誤差到尺寸上。"""
        # 假設誤差是一個固定的值，我們之後會從 config.py 讀取
        self.calc_dimensions = (
            self.base_dimensions[0] + MEASUREMENT_ERROR,
            self.base_dimensions[1] + MEASUREMENT_ERROR,
            self.base_dimensions[2] + MEASUREMENT_ERROR,
        )

    def get_rotated_dimensions(self, rotation_type: int) -> tuple[float, float, float]:
        """根據旋轉類型返回計算後的貨物尺寸 (l, w, h)"""
        l, w, h = self.calc_dimensions
        if rotation_type == 0:   # (l, w, h)
            return l, w, h
        elif rotation_type == 1: # (w, l, h)
            return w, l, h
        elif rotation_type == 2: # (l, h, w)
            return l, h, w
        elif rotation_type == 3: # (h, l, w)
            return h, l, w
        elif rotation_type == 4: # (w, h, l)
            return w, h, l
        elif rotation_type == 5: # (h, w, l)
            return h, w, l
        else:
            raise ValueError(f"不合法的旋轉類型: {rotation_type}")

    def to_dict(self) -> dict[str, Any]:
        """將 Item 物件轉換為可序列化為 JSON 的字典。"""
        # asdict 會自動將 dataclass 轉換為字典
        return asdict(self)

@dataclass
class SupportSurface:
    """可以放置物品的支撐平面
    z(平面高度),
    rect(平面座標),
    supporting_items(支撐此平面的物品ID列表),
    area()(返回該平面的面積)
    """
    z: float  # 該平面的高度
    # 平面的二維邊界 (x_min, y_min, x_max, y_max)
    rect: tuple[float, float, float, float]
    # 支撐此平面的物品ID列表，'floor' 代表籠車底板
    supporting_items: list[str]

    @property
    # 讓area() 成為一個屬性
    def area(self) -> float:
        """計算並返回該平面的面積"""
        x_min, y_min, x_max, y_max = self.rect
        return (x_max - x_min) * (y_max - y_min)


@dataclass
class CageTrolley:
    """id(str),
    dimensions(長, 寬, 高),
    weight_limit,
    packed_items,
    support_surfaces,
    corner_points
    """
    id: str
    # 籠車內部可用尺寸 (長, 寬, 高)
    dimensions: tuple[float, float, float]
    weight_limit: float
    
    # 籠車狀態
    packed_items: list[Item] = field(default_factory=list)
    support_surfaces: list[SupportSurface] = field(default_factory=list)
    corner_points: list[tuple[float, float, float]] = field(default_factory=lambda: [(0.0, 0.0, 0.0)])
    
    # 初始化
    def __post_init__(self):
        """初始化籠車，建立第一個支撐平面(底板)。"""
        if not self.support_surfaces:
            # 建立籠車底板作為初始支撐平面
            cage_length, cage_width, _ = self.dimensions
            initial_surface = SupportSurface(
                z=0.0,
                rect=(0.0, 0.0, cage_length, cage_width),
                supporting_items=['floor']
            )
            self.support_surfaces.append(initial_surface)

    @property
    def current_weight(self) -> float:
        """計算當前總重量。"""
        return sum(item.weight for item in self.packed_items)

    def add_item(self, item: Item, position: tuple[float, float, float], rotation_type: int):
        """將一個物品加入籠車。"""
        item.position = position
        item.rotation_type = rotation_type
        self.packed_items.append(item)
        # 注意：更新 support_surfaces 的邏輯會比較複雜，我們稍後在 surface_manager.py 中實現
        # print(f"成功將物品 {item.id} 放置在 {position}，旋轉類型 {rotation_type}") 
    
    def to_dict(self) -> dict[str, Any]:
        """將 CageTrolley 物件轉換為字典。"""
        return asdict(self)
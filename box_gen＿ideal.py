import random
from typing import List, Tuple, Optional
from .bpp_solver.data_structures import Item

# 論文設定（AAAI-21）
BIN_L = BIN_W = BIN_H = 10  # L=W=H=10
BIN_VOL = BIN_L * BIN_W * BIN_H

# 這裡用 {1,2,3,4}^3 恰好 64 種，皆 <= 5 (<= L/2)
CATALOG_64: List[Tuple[int, int, int]] = [(x, y, z) for x in (1,2,3,4)
                                          for y in (1,2,3,4)
                                          for z in (1,2,3,4)]

# ---- 你的專案的 Item 類別（請按需調整 new_item 的對應）----
# from ...data_structures import Item

def new_item(idx: int, dims: Tuple[int,int,int], allow_rotations: bool = True):
    """
    依你的 Item 介面做最小假設：
    - id: 字串
    - dimensions: (l,w,h)
    - allowed_rotations: e.g. [0..5] 若支援 6 面取向；不支援就給 [0]
    其他欄位（重量/易碎）RS 基準不強制，需要再加可自己擴充。
    """
    allowed = list(range(6)) if allow_rotations else [0]
    weight = random.randint(1, 20)
    return Item(
        id=idx,
        base_dimensions=(float(dims[0]), float(dims[1]), float(dims[2])),
        allowed_rotations=allowed,
        weight=weight  # RS 基準不強制
    )

def gen_one_rs_sequence(seed: Optional[int] = None,
                        allow_rotations: bool = True) -> List['Item']:
    """
    產生一條 RS 序列：從 64 型別中隨機抽樣（可重複），
    直到累計體積 >= bin 體積（論文 RS 的做法）。
    """
    if seed is not None:
        random.seed(seed)

    seq: List['Item'] = []
    total_vol = 0
    idx = 1
    while total_vol < BIN_VOL:
        l, w, h = random.choice(CATALOG_64)
        seq.append(new_item(idx, (l, w, h), allow_rotations=allow_rotations))
        total_vol += l * w * h
        idx += 1
    return seq

def gen_rs_dataset(num_sequences: int,
                   seed: Optional[int] = None,
                   allow_rotations: bool = True) -> List[List['Item']]:
    """
    產生多條 RS 序列。論文測試用 2,000 條，你可傳 2000。
    """
    if seed is not None:
        random.seed(seed)
    dataset: List[List['Item']] = []
    for s in range(num_sequences):
        # 為了可重現，也可對每條序列再加一個局部種子：seed+s
        seq = gen_one_rs_sequence(seed=None, allow_rotations=allow_rotations)
        dataset.append(seq)
    return dataset

if __name__ == "__main__":
    # 測試用
    rs_data = gen_rs_dataset(5, seed=1234)
    for i, seq in enumerate(rs_data):
        print(f"--- RS 序列 #{i+1} (共 {len(seq)} 件) ---")
        for item in seq:
            print(f"  {item.id}: {item.base_dimensions}, 允許旋轉: {item.allowed_rotations}")
        total_vol = sum(item.calc_dimensions[0] * item.calc_dimensions[1] * item.calc_dimensions[2] for item in seq)
        print(f"  總體積: {total_vol} (箱子體積: {BIN_VOL})\n")

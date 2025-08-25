from config import W_Z_SCORE # 暫時只用 Z_Score

def calculate_placement_score(
    position: tuple[float, float, float]
) -> float:
    """
    計算一個放置方案的分數。分數越高代表放置越優。
    目前只實現 Z_Score。
    
    :param position: 物品放置的 (x, y, z) 座標。
    :return: 該放置方案的分數。
    """
    
    # Z_Score (高度分數): 優先填滿較低窪的空間。z 越低，分數越高。
    # 加 1 是為了避免 z=0 時分母為零。
    z_score = 1.0 / (1.0 + position[2])
    
    # 根據您的演算法，未來可以在這裡加入 Stability_Score 和 CoG_Shift_Score
    placement_score = (W_Z_SCORE * z_score)
    
    return placement_score
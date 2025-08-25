from __future__ import annotations
import math
from typing import Optional, List, Dict

class MCTSNode:
    def __init__(self, parent: Optional['MCTSNode'], action: Optional[Dict] = None):
        self.parent = parent
        self.action = action  # 導致這個狀態的動作
        self.children: List['MCTSNode'] = []
        
        self.w = 0.0  # 總得分 (Win count)
        self.n = 0    # 訪問次數 (Visit count)
        
        # 這個節點下所有可能的動作，在第一次擴展時計算
        self.possible_actions: Optional[List[Dict]] = None

    def is_fully_expanded(self) -> bool:
        return self.possible_actions is not None and len(self.children) == len(self.possible_actions)

    def select_best_child(self, C: float = 1.41) -> 'MCTSNode':
        """使用標準的 UCT 公式選擇最佳子節點"""
        best_score = -float('inf')
        best_child = None
        for child in self.children:
            if child.n == 0:
                # 優先探索未被訪問過的節點
                uct_score = float('inf')
            else:
                exploit_term = child.w / child.n  # 平均得分
                explore_term = C * math.sqrt(math.log(self.n) / child.n)
                uct_score = exploit_term + explore_term
            
            if uct_score > best_score:
                best_score = uct_score
                best_child = child
        return best_child
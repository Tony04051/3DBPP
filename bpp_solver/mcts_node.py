# bpp_solver/mcts_node.py (這可以是一個新檔案，或放在 packer.py 內部)
from __future__ import annotations
import math
from dataclasses import dataclass, field
from .data_structures import CageTrolley
from typing import Optional, List, Dict, Any

@dataclass
class MCTS_Node:
    """代表 MCTS 搜尋樹中的一個節點"""
    # 節點狀態
    state: CageTrolley # 該節點代表的籠車狀態
    parent: Optional[MCTS_Node] = None
    children: List[MCTS_Node] = field(default_factory=list)
    
    # 導致這個狀態的動作
    action: Optional[Dict[str, Any]] = None 
    
    # MCTS 統計數據
    visits: int = 0
    score: float = 0.0 # 在我們的例子中，可以是放置物品的總體積

    def is_fully_expanded(self, num_possible_actions: int) -> bool:
        return len(self.children) == num_possible_actions

    def best_child(self, C: float = 1.41) -> MCTS_Node:
        """使用 UCT 公式選擇最佳子節點"""
        best_score = -math.inf
        best_child_node = None
        for child in self.children:
            if child.visits == 0:
                uct_score = math.inf # 優先探索未訪問過的節點
            else:
                exploit_term = child.score / child.visits
                explore_term = C * math.sqrt(math.log(self.visits) / child.visits)
                uct_score = exploit_term + explore_term
            
            if uct_score > best_score:
                best_score = uct_score
                best_child_node = child
        return best_child_node
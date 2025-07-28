# 蒙地卡羅
# bpp_solver/packer_mcts.py (建議使用一個新檔案以示區別)

import math
import random
import copy
from typing import List, Dict, Any

from .data_structures import Item, CageTrolley
from .surface_manager import SurfaceManager
from .mcts_node import MCTS_Node # 假設您創建了新檔案
from . import constraints as con

class MCTS_Packer:
    def __init__(self, cage: CageTrolley, surface_manager: SurfaceManager, num_simulations: int = 100):
        self.num_simulations = num_simulations
        self.cage = cage
        self.surface_manager = surface_manager
        print(f"MCTS Packer 初始化，模擬次數: {self.num_simulations}")

    def pack(self, initial_cage_state: CageTrolley, candidate_items: list[Item]) -> Dict[str, Any] | None:
        """
        使用 MCTS 尋找最佳的下一步放置方案。
        """
        root = MCTS_Node(state=initial_cage_state)
        
        # 啟動 MCTS 主迴圈
        for _ in range(self.num_simulations):
            # 複製狀態以避免修改原始樹
            sim_candidate_items = candidate_items[:]
            
            # 1. Selection - 選擇一個有前途的葉節點
            leaf_node = self._select(root)
            
            # 2. Expansion - 如果節點未完全擴展，則擴展它
            possible_actions = self._get_possible_actions(leaf_node.state, sim_candidate_items)
            if not leaf_node.is_fully_expanded(len(possible_actions)):
                leaf_node = self._expand(leaf_node, possible_actions, sim_candidate_items)

            # 3. Simulation (Rollout) - 從葉節點開始快速模擬到結束
            # 這裡的 "結束" 指的是 lookahead item 都被處理完
            simulation_result = self._simulate(leaf_node.state, sim_candidate_items)
            
            # 4. Backpropagation - 將模擬結果反向傳播回根節點
            self._backpropagate(leaf_node, simulation_result)

        # 所有模擬結束後，從根節點的子節點中選擇最佳動作
        if not root.children:
            return None # 沒有任何可行的放置方案
        
        # 選擇被訪問次數最多的子節點作為最穩健的選擇
        best_next_node = max(root.children, key=lambda c: c.visits)
        return best_next_node.action

    def _select(self, node: MCTS_Node) -> MCTS_Node:
        while node.children: # 只要不是葉節點
            possible_actions = self._get_possible_actions(node.state, []) # 傳入空 item 列表以獲取計數
            if not node.is_fully_expanded(len(possible_actions)):
                return node # 如果未完全擴展，就選擇它自己進行擴展
            node = node.best_child()
        return node
    
    def _expand(self, node: MCTS_Node, possible_actions: List[Dict], candidate_items: list[Item]) -> MCTS_Node:
        # 從未被嘗試過的動作中隨機選一個
        tried_actions = {child.action['item'].id for child in node.children}
        untried_actions = [action for action in possible_actions if action['item'].id not in tried_actions]
        
        if not untried_actions:
            return node

        action_to_expand = random.choice(untried_actions)
        
        # 執行該動作，創建新狀態
        new_state = self._apply_action(node.state, action_to_expand)
        
        # 創建新節點並加入樹中
        new_node = MCTS_Node(state=new_state, parent=node, action=action_to_expand)
        node.children.append(new_node)
        return new_node

    def _simulate(self, start_state: CageTrolley, remaining_items: list[Item]) -> float:
        """
        快速模擬 (Rollout)。
        使用一個簡單、快速的策略來放置剩餘的物品。
        返回最終放置物品的總體積作為評分。
        """
        current_state = copy.deepcopy(start_state)
        items_to_place = remaining_items[:]
        placed_volume = 0
        
        # 啟發式剪枝：在模擬中，我們採用一個非常簡單的貪婪策略
        while items_to_place:
            item = items_to_place.pop(0) # 順序處理
            # 尋找第一個可行的放置點 (這就是一個快速的策略)
            best_action = self._find_first_valid_action(current_state, item)
            
            if best_action:
                current_state = self._apply_action(current_state, best_action)
                dims = item.get_rotated_dimensions(best_action['rotation_type'])
                placed_volume += dims[0] * dims[1] * dims[2]

        return placed_volume

    def _backpropagate(self, node: MCTS_Node, result_score: float):
        while node is not None:
            node.visits += 1
            node.score += result_score
            node = node.parent

    # --- 輔助函式 (啟發式剪枝和動作生成) ---
    def _get_possible_actions(self, cage: CageTrolley, candidate_items: list[Item]) -> List[Dict]:
        """
        這就是啟發式剪枝的地方。它只生成有效的放置方案。
        這個函式與您舊的 `pack` 方法非常相似。
        """
        possible_actions = []
        for item in candidate_items:
            for rotation_type in item.allowed_rotations:
                item_dims = item.get_rotated_dimensions(rotation_type)
                # 使用簡化的 Bottom-Left 策略生成候選點
                sorted_surfaces = sorted(cage.support_surfaces, key=lambda s: (s.z, s.rect[1], s.rect[0]))
                for surface in sorted_surfaces:
                    placement_point = (surface.rect[0], surface.rect[1], surface.z)
                    if con.is_placement_valid(cage, item, placement_point, rotation_type):
                        possible_actions.append({
                            'item': item,
                            'position': placement_point,
                            'rotation_type': rotation_type
                        })
                        # 為了效率，可以只為每個物品找幾個最好的點，而不是全部
                        break 
        return possible_actions

    def _find_first_valid_action(self, cage: CageTrolley, item: Item) -> Dict | None:
        # Rollout 用的快速版，找到第一個就行
        for rotation_type in item.allowed_rotations:
            sorted_surfaces = sorted(cage.support_surfaces, key=lambda s: (s.z, s.rect[1], s.rect[0]))
            for surface in sorted_surfaces:
                placement_point = (surface.rect[0], surface.rect[1], surface.z)
                if con.is_placement_valid(cage, item, placement_point, rotation_type):
                    return {'item': item, 'position': placement_point, 'rotation_type': rotation_type}
        return None

    def _apply_action(self, cage_state: CageTrolley, action: Dict) -> CageTrolley:
        # 注意：必須深度複製，以防修改原始狀態
        new_cage = copy.deepcopy(cage_state)
        # 這裡需要一個簡化版的 surface_manager 更新邏輯，或者傳入 surface_manager 實例
        # (為簡化，此處省略了 surface manager 的更新，但在實際代碼中必須實現)
        # new_cage.add_item(...)
        # new_cage.support_surfaces = surface_manager.update(...)
        return new_cage
    
    def execute_placement(self, placement: Dict[str, Any]):
        """
        執行一個放置方案並更新籠車狀態。
        """
        item = placement['item']
        position = placement['position']
        rotation_type = placement['rotation_type']
        
        # 1. 將物品正式加入籠車的 packed_items 列表
        self.cage.add_item(item, position, rotation_type)
        
        # 2. 調用 surface_manager 更新支撐平面
        self.cage.support_surfaces = self.surface_manager.update_support_surfaces(
            placed_item=item,
            all_surfaces=self.cage.support_surfaces,
        )
        
        # 3. (可選) 重新計算籠車重心等狀態 (目前已在 add_item 中隱含處理)
        #    如果 CageTrolley 有 center_of_gravity 屬性，可以在此處更新
        #    self.cage.recalculate_center_of_gravity()
        
        print(f"籠車狀態已更新。當前重量: {self.cage.current_weight:.2f}kg, "
              f"剩餘支撐平面: {len(self.cage.support_surfaces)}個。")
        # print("剩餘支撐平面列表:"
        #       f"{[f'平面{idx}: z={s.z}, rect={s.rect}' for idx, s in enumerate(self.cage.support_surfaces)]}")
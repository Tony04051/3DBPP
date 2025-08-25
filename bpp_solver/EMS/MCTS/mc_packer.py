import time
import random
import copy
from typing import List, Dict, Any, Tuple, Set

from ...data_structures import Item, CageTrolley, SupportSurface
from ..surface_manager import SurfaceManager
from .mcts_node import MCTSNode
from .. import constraints as con
from config import *

class MCTS_Packer:
    def __init__(self, num_simulations: int = 100, rollout_depth: int = TEMP_AREA_CAPACITY +1):
        self.surface_manager = SurfaceManager()
        self.num_simulations = num_simulations
        self.rollout_depth = rollout_depth
        print(f"MCTS Packer (EMS) 初始化，模擬次數: {self.num_simulations}, 模擬深度: {self.rollout_depth}")

    def pack(self, cage: CageTrolley, candidate_items: list[Item]) -> Dict[str, Any] | None:
        """
        使用 MCTS 和角落點法尋找最佳的下一步放置方案。
        使用shallow copy，執行後 cage 狀態不會被永久改變。
        """
        if not candidate_items:
            return None
            
        root = MCTSNode(parent=None)
        start_time = time.time()

        for _ in range(self.num_simulations):
            # 每次模擬都從一個乾淨的cage 
            sim_cage = CageTrolley(
                id=cage.id,
                packed_items=[copy.copy(i) for i in cage.packed_items],
                dimensions=cage.dimensions,
                weight_limit=cage.weight_limit,
                support_surfaces=[copy.copy(s) for s in cage.support_surfaces]
            )
            
            # 1. Selection
            node, path, remaining_items = self._select(root, sim_cage, candidate_items[:])
            
            # 2. Expansion
            # _expand 會直接修改傳入的 sim_cage
            if not node.is_fully_expanded():
                expanded_node = self._expand(node, sim_cage, remaining_items)
                if expanded_node is not node:
                    path.append(expanded_node)
                    node = expanded_node
            
            # 3. Simulation (Rollout)

            items_on_path = {p.action['item'].id for p in path if p.action}
            rollout_items = [i for i in candidate_items if i.id not in items_on_path]
            simulation_result = self._simulate(sim_cage, rollout_items)
            
            # 4. Backpropagation
            self._backpropagate(path, simulation_result)

        if not root.children:
            return None
        
        best_node = max(root.children, key=lambda c: c.n)
        print(f"MCTS 決策耗時: {time.time() - start_time:.2f}s, 最佳動作訪問次數: {best_node.n}")
        best_item_id = best_node.action['item'].id
        original_best_item = next(i for i in candidate_items if i.id == best_item_id)
        
        self.execute_placement(cage, {'item': original_best_item,
            'position': best_node.action['position'],
            'rotation_type': best_node.action['rotation_type']
        })

        return {
            'item': original_best_item,
            'position': best_node.action['position'],
            'rotation_type': best_node.action['rotation_type']
        }

    def _select(self, root: MCTSNode, cage: CageTrolley, items: List[Item]) -> Tuple[MCTSNode, List[MCTSNode], List[Item]]:
        node = root
        path = [root]
        remaining_items = items[:]
        
        while node.is_fully_expanded() and node.children:
            node = node.select_best_child()
            path.append(node)
            
            selected_item_action = node.action['item']
            item_to_remove = next((i for i in remaining_items if i.id == selected_item_action.id), None)
            
            if item_to_remove:
                remaining_items.remove(item_to_remove)
                cage.add_item(item_to_remove, node.action['position'], node.action['rotation_type'])
            else:
                # 如果找不到，說明 MCTS 樹的狀態與 `items` 列表不同步，這是一個潛在的錯誤
                # 但在淺拷貝模式下，這通常不應該發生
                pass

        return node, path, remaining_items



    def _expand(self, node: MCTSNode, cage: CageTrolley, items: List[Item]) -> MCTSNode:
        """在 sim_cage 上進行擴展。"""
        if node.possible_actions is None:
            node.possible_actions = self._get_possible_actions(items, cage)

        tried_item_ids = {child.action['item'].id for child in node.children}
        
        for action in node.possible_actions:
            if action['item'].id not in tried_item_ids:
                item = action['item']
                cage.add_item(item, action['position'], action['rotation_type'])
                new_node = MCTSNode(parent=node, action=action)
                node.children.append(new_node)
                return new_node
                
        return node
    def _simulate(self, cage: CageTrolley, items: List[Item]) -> float:
        """快速隨機模擬，返回最終放置物品的總體積作為評分"""
        # 建立一個專屬於這次模擬的籠車副本
        sim_cage = CageTrolley(
            id=cage.id,
            dimensions=cage.dimensions,
            weight_limit=cage.weight_limit
        )
        sim_cage.packed_items = [copy.copy(i) for i in cage.packed_items]
        sim_cage.support_surfaces = [copy.copy(s) for s in cage.support_surfaces]
        
        items_in_cage_ids = {i.id for i in sim_cage.packed_items}
        items_to_place = [i for i in items if i.id not in items_in_cage_ids]
        random.shuffle(items_to_place)
        
        placed_volume = 0
        
        for _ in range(self.rollout_depth):
            if not items_to_place: break
            item = items_to_place.pop(0)
            
            # 先找到一個有效的放置動作
            action = self._find_first_valid_action(item, sim_cage)
            
            if action:
                # 只有在找到放置方案後，才執行放置並更新平面
                # 1. 執行放置
                item = action['item']
                position = action['position']
                rotation_type = action['rotation_type']
                
                sim_cage.add_item(item, position, rotation_type)
                
                new_surfaces = self.surface_manager.update_support_surfaces(
                    placed_item=item,
                    all_surfaces=cage.support_surfaces
                )
                sim_cage.support_surfaces = new_surfaces
                
                # 2. 計算體積
                dims = item.get_rotated_dimensions(action['rotation_type'])
                placed_volume += dims[0] * dims[1] * dims[2]
        
        return placed_volume
    
    def _backpropagate(self, path: List[MCTSNode], score: float):
        for node in reversed(path):
            node.n += 1
            node.w += score

    def _get_possible_actions(self, items: list, cage: CageTrolley) -> List[Dict]:
        actions = []
        sorted_surfaces = sorted(
            cage.support_surfaces,
            key=lambda s: (s.z, s.rect[1], s.rect[0])  # 先按 z 排，再按 y 排，再按 x 排
        )

        for item in items:
            for rot in item.allowed_rotations:
                for s in sorted_surfaces:
                    pos = (s.rect[0], s.rect[1], s.z)  # 在該平面上，放置點就是其左下角
                    if con.is_placement_valid(cage, item, pos, rot):
                        actions.append({'item': item, 'position': pos, 'rotation_type': rot})
                        break 
        return actions
    
    def _find_first_valid_action(self, item: Item, cage: CageTrolley) -> Dict | None:
        sorted_surfaces = sorted(
            cage.support_surfaces,
            key=lambda s: (s.z, s.rect[1], s.rect[0])  # 先按 z 排，再按 y 排，再按 x 排
        )
        
        for rot in item.allowed_rotations:
            for pos in [(s.rect[0], s.rect[1], s.z) for s in sorted_surfaces]:
                if con.is_placement_valid(cage, item, pos, rot):
                    return {'item': item, 'position': pos, 'rotation_type': rot}
        return None
    
    def execute_placement(self, cage: CageTrolley, placement: Dict[str, Any]):
        """
        執行放置方案並更新籠車狀態
        """
        if placement is None:
            print("沒有放置方案可執行。")
            return

        item = placement['item']
        position = placement['position']
        rotation_type = placement['rotation_type']
        
        cage.add_item(item, position, rotation_type)
        
        new_surfaces = self.surface_manager.update_support_surfaces(
            placed_item=item,
            all_surfaces=cage.support_surfaces
        )
        cage.support_surfaces = new_surfaces

        print(f"籠車狀態已更新。當前重量: {cage.current_weight:.2f}kg, ")
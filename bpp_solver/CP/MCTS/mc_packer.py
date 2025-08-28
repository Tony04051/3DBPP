import math
import time
import random
import copy
from typing import List, Dict, Any, Tuple, Set

from ...data_structures import Item, CageTrolley
from .. import constraints as con
from config import *

class _OrderNode:
    __slots__ = ("parent", "children", "w", "n", "remaining", "sim_cage", "action", "added")
    def __init__(self, parent, remaining: List[Item], sim_cage: CageTrolley,
                 action: Dict[str, Any] | None = None, added: float = 0.0):
        self.parent = parent
        self.children: List["_OrderNode"] = []
        self.w: float = 0.0              # 累積回傳分數（新增體積）
        self.n: int = 0                  # 訪問次數
        self.remaining = remaining[:]    # 尚未放入的 items（視窗內）
        self.sim_cage = sim_cage         # 走到此節點後的模擬籠車（淺拷貝世界）
        self.action = action             # 抵達此節點用的動作（root 的孩子 = 第一手）
        self.added = added               # 路徑至此的新增體積總和


class MCTS_Packer:
    """
    BPP-k + MCTS lookahead（open-loop 序列層 MCTS）
    - 每次決策在當前最多 4 件候選中選擇「第一步」，並同時選定角點與旋轉
    - 複雜度約 O(k · num_simulations)，k ≤ 4
    - pack() 會直接更新傳入的 cage
    """
    def __init__(self, num_simulations: int = 100, rollout_depth: int = TEMP_AREA_CAPACITY + 1,
                 uct_c: float = 0.9):
        self.num_simulations = num_simulations
        self.rollout_depth = rollout_depth
        self.uct_c = uct_c
        print(f"MCTS Packer (k-lookahead) 初始化，模擬次數: {self.num_simulations}, "
              f"rollout深度: {self.rollout_depth}, UCT_C: {self.uct_c}")

    # ========================= Public API =========================
    def pack(self, cage: CageTrolley, candidate_items: List[Item]) -> Dict[str, Any] | None:
        """
        在當前候選（最多4件）中，用序列層 MCTS 選出最佳第一步，並直接落地更新 cage。
        回傳 {'item', 'position', 'rotation_type'} 或 None（若完全無法放）。
        """
        if not candidate_items:
            return None

        start = time.time()
        best = self._order_mcts_first_action(
            cage, candidate_items, iters=self.num_simulations, k=4, C=self.uct_c
        )
        if not best:
            return None

        # 更新cage
        chosen_item = next(i for i in candidate_items if i.id == best['item'].id)
        cage.add_item(chosen_item, best['position'], best['rotation_type'])

        print(f"MCTS 決策耗時: {time.time() - start:.3f}s")
        return {
            'item': chosen_item,
            'position': best['position'],
            'rotation_type': best['rotation_type'],
        }

    # ====================== 序列層 MCTS 主流程 ======================
    def _order_mcts_first_action(self, cage: CageTrolley, candidates: List[Item],
                                 iters: int, k: int = 4, C: float = 0.9) -> Dict[str, Any] | None:
        """
        在視窗中（k ≤ 4）用 open-loop MCTS 選出最佳第一步（item + corner point + rotation）。
        """
        pool = candidates[:k] if k > 0 else candidates[:4]
        if not pool:
            return None

        root = _OrderNode(
            parent=None,
            remaining=pool,
            sim_cage=CageTrolley(
                id=cage.id,
                packed_items=[copy.copy(i) for i in cage.packed_items],
                dimensions=cage.dimensions,
                weight_limit=cage.weight_limit
            )
        )

        def uct(parent_n: int, child: _OrderNode) -> float:
            if child.n == 0:
                return float("inf")
            return (child.w / child.n) + C * math.sqrt(math.log(max(1, parent_n)) / child.n)

        for _ in range(max(1, iters)):
            # --- Selection ---
            node = root
            path = [node]
            while node.children and node.remaining:
                node = max(node.children, key=lambda ch: uct(node.n, ch))
                path.append(node)

            # --- Expansion ---
            if node.remaining:
                expanded = False
                rem = node.remaining[:]
                random.shuffle(rem)  # 打散避免固定偏壓
                for item in rem:
                    best_act = self._best_valid_action(node.sim_cage, item)
                    if best_act is None:
                        continue  # 這件目前放不下，換下一件

                    sim_next = CageTrolley(
                        id=node.sim_cage.id,
                        packed_items=[copy.copy(i) for i in node.sim_cage.packed_items],
                        dimensions=node.sim_cage.dimensions,
                        weight_limit=node.sim_cage.weight_limit
                    )
                    sim_next.add_item(item, best_act['position'], best_act['rotation_type'])
                    dx, dy, dz = item.get_rotated_dimensions(best_act['rotation_type'])
                    child = _OrderNode(
                        parent=node,
                        remaining=[it for it in node.remaining if it.id != item.id],
                        sim_cage=sim_next,
                        action=best_act,
                        added=node.added + dx * dy * dz
                    )
                    node.children.append(child)
                    node = child
                    path.append(node)
                    expanded = True
                    break
                # 若所有剩餘 item 都放不下，則不擴展，直接 rollout

            # --- Rollout ---
            total = node.added
            if node.remaining:
                total += self._rollout_order(node.sim_cage, node.remaining)

            # --- Backprop ---
            for nd in path:
                nd.n += 1
                nd.w += total

        if not root.children:
            return None
        # 以 exploitation（平均分數）選第一步；也可改用 visits
        best_child = max(root.children, key=lambda ch: (ch.w / ch.n))
        return best_child.action

    # ====================== 放置評分與 Rollout ======================
    def _best_valid_action(self, cage: CageTrolley, item: Item) -> Dict[str, Any] | None:
        """
        在當前 cage 上，對 item 遍歷所有 (corner point × 允許旋轉)，
        取「新增體積」最大者；若同分，偏好較低 z、較小 y、較小 x（左下角法慣例）。
        """
        points = self._generate_candidate_points(cage)
        if not points:
            return None
        pts = sorted(points, key=lambda p: (p[2], p[1], p[0]))  # z→y→x

        best = None
        best_key = None  # (added, -z, -y, -x)
        for rot in item.allowed_rotations:
            for pos in pts:
                if con.is_placement_valid(cage, item, pos, rot):
                    dx, dy, dz = item.get_rotated_dimensions(rot)
                    key = (dx * dy * dz, -pos[2], -pos[1], -pos[0])
                    if best_key is None or key > best_key:
                        best_key = key
                        best = {'item': item, 'position': pos, 'rotation_type': rot}
        return best

    def _rollout_order(self, cage: CageTrolley, remaining: List[Item]) -> float:
        """
        對剩餘 items 做快速貪婪 rollout：
        - 順序先打散，避免系統性偏壓
        - 每件用 _best_valid_action 放入
        - 回傳新增體積總和
        """
        sim = CageTrolley(
            id=cage.id,
            packed_items=[copy.copy(i) for i in cage.packed_items],
            dimensions=cage.dimensions,
            weight_limit=cage.weight_limit
        )
        total = 0.0
        rem = remaining[:]
        random.shuffle(rem)
        for it in rem:
            act = self._best_valid_action(sim, it)
            if not act:
                continue
            sim.add_item(it, act['position'], act['rotation_type'])
            dx, dy, dz = it.get_rotated_dimensions(act['rotation_type'])
            total += dx * dy * dz
        return total

    # ====================== Corner Points 產生 ======================
    def _generate_candidate_points(self, cage: CageTrolley) -> List[Tuple[float, float, float]]:
        """
        以目前 packed_items 生成候選 corner points（左下角法基礎版：x+/y+/（非易碎才）z+）。
        已過濾越界與「落在任何物品體積內部」的點；允許落在面/邊界上。
        回傳 list[tuple[x, y, z]]。
        """
        def point_in_item(point: Tuple[float, float, float], packed_item: Item, tol: float = 1e-7) -> bool:
            if packed_item.position is None:
                return False
            ix, iy, iz = packed_item.position
            dx, dy, dz = packed_item.get_rotated_dimensions(packed_item.rotation_type)
            px, py, pz = point
            return (ix + tol < px < ix + dx - tol and
                    iy + tol < py < iy + dy - tol and
                    iz + tol < pz < iz + dz - tol)

        def point_not_in_any_item(point: Tuple[float, float, float], packed_items: List[Item]) -> bool:
            for it in packed_items:
                if point_in_item(point, it):
                    return False
            return True

        points: Set[Tuple[float, float, float]] = {(0.0, 0.0, 0.0)}
        for it in cage.packed_items:
            pos = it.position
            dx, dy, dz = it.get_rotated_dimensions(it.rotation_type)

            candidates = [
                (pos[0] + dx, pos[1],       pos[2]),  # x+
                (pos[0],      pos[1] + dy,  pos[2]),  # y+
            ]
            if not getattr(it, "is_fragile", False):
                candidates.append((pos[0], pos[1], pos[2] + dz))  # z+

            for p in candidates:
                if point_not_in_any_item(p, cage.packed_items):
                    points.add((float(p[0]), float(p[1]), float(p[2])))

        # 邊界過濾
        l, w, h = cage.dimensions if hasattr(cage, "dimensions") else CAGE_DIMENSIONS
        TOL = 1e-6
        valid = [p for p in points if p[0] < l - TOL and p[1] < w - TOL and p[2] < h - TOL]
        return valid

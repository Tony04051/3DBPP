# app.py
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple, Optional
import traceback
from threading import Lock

# --- 從您的專案中導入真實的模組 ---
from bpp_solver.data_structures import Item, CageTrolley
from bpp_solver.CP.Heuristics.packer import Packer as CP_HeuristicsPacker
from bpp_solver.CP.MCTS.mc_packer import MCTS_Packer as CP_MCTS_Packer
from bpp_solver.EMS.Heuristics.packer import Packer as EMS_HeuristicsPacker
from bpp_solver.EMS.MCTS.mc_packer import MCTS_Packer as EMS_MCTS_Packer

# --- 應用程式初始化 ---
app = FastAPI(
    title="3D Bin Packing API",
    description="一個用於解決線上3D裝箱問題的 API，支援多種求解策略。",
    version="1.0"
)

# --- 1. 定義 API 的請求和回應模型 (使用 Pydantic) ---
# 這將為我們提供免費的數據驗證和 API 文件

class ItemModel(BaseModel):
    id: int
    base_dimensions: Tuple[float, float, float]
    weight: float
    allowed_rotations: List[int] = Field(default_factory=lambda: list(range(6)))
    is_fragile: bool = False

class CageModel(BaseModel):
    id: str
    dimensions: Tuple[float, float, float]
    weight_limit: float
    packed_items: List[ItemModel] = []
    current_weight: Optional[float] = None

class StartPackingRequest(BaseModel):
    id: str = "C001"
    dimensions: Tuple[float, float, float] = (120, 100, 180)
    weight_limit: float = 800

class DecideMoveRequest(BaseModel):
    strategy: str = Field(..., description="策略類型: 'cp' (角落點法) 或 'ems' (最大空間法)")
    algorithm: str = Field(..., description="演算法類型: 'heuristics' 或 'mcts'")
    candidate_items: List[ItemModel]
    num_simu: int = Field(500, description="MCTS 的模擬次數")

class PlacementDecision(BaseModel):
    item: ItemModel
    position: Tuple[float, float, float]
    rotation_type: int

class SuccessResponse(BaseModel):
    status: str = "success"
    message: Optional[str] = None
    cage_state: Optional[CageModel] = None
    decision: Optional[PlacementDecision] = None

class NoMoveResponse(BaseModel):
    status: str = "no_move_possible"
    decision: Any = None
    message: str

class UniversalResponse(BaseModel):
    status: str # "success" or "no_move_possible"
    message: Optional[str] = None
    cage_state: Optional[CageModel] = None
    decision: Optional[PlacementDecision] = None

# --- 2. 伺服器狀態管理 ---

# 初始化所有的 Packer 實例
PACKER_INSTANCES = {
    ('cp', 'heuristics'): CP_HeuristicsPacker(),
    ('cp', 'mcts'): CP_MCTS_Packer(),
    ('ems', 'heuristics'): EMS_HeuristicsPacker(),
    ('ems', 'mcts'): EMS_MCTS_Packer(),
}

# 使用一個字典來管理狀態，這樣更容易擴展
class AppState:
    def __init__(self):
        self.cage: Optional[CageTrolley] = None
        self.lock = Lock()

app_state = AppState()

# --- 3. API 端點 (Endpoint) ---

@app.post("/start_packing", 
          response_model=SuccessResponse, 
          summary="初始化或重置裝箱流程")
def start_packing(request: StartPackingRequest):
    """
    建立一個新的空籠車，開始一個新的裝箱任務。
    這將會覆蓋任何正在進行中的任務。
    """
    with app_state.lock:
        app_state.cage = CageTrolley(
            id=request.id,
            dimensions=request.dimensions,
            weight_limit=request.weight_limit,
            packed_items=[]
        )
        print(f"[API] /start_packing: 新的裝箱流程已啟動。籠車 ID: {app_state.cage.id}")
        return SuccessResponse(
            message="裝箱流程已成功初始化。",
            cage_state=CageModel(**app_state.cage.to_dict())
        )

@app.get("/get_cage_state", 
         response_model=SuccessResponse, 
         summary="獲取當前籠車狀態")
def get_cage_state():
    """獲取伺服器上當前籠車的完整狀態，包括已放置的物品。"""
    with app_state.lock:
        if app_state.cage is None:
            raise HTTPException(status_code=404, detail="裝箱流程尚未開始。請先呼叫 /start_packing。")
        
        print(f"[API] /get_cage_state: 獲取籠車 {app_state.cage.id} 的狀態。")
        return SuccessResponse(
            cage_state=CageModel(**app_state.cage.to_dict())
        )

@app.post("/decide_next_move", 
          response_model=UniversalResponse, # 只定義一個統一的回應模型
          summary="決定並執行下一步動作")
def decide_next_move(request: DecideMoveRequest):
    """
    接收候選物品列表和求解策略，計算最佳放置方案，
    並在伺服器端【自動更新】籠車狀態。
    """
    with app_state.lock:
        if app_state.cage is None:
            raise HTTPException(status_code=404, detail="裝箱流程尚未開始。請先呼叫 /start_packing。")

        print(f"[API] /decide_next_move: 收到 {len(request.candidate_items)} 個候選物品。")

        try:
            candidate_items = [Item(**d.dict()) for d in request.candidate_items]

            packer_key = (request.strategy.lower(), request.algorithm.lower())
            packer_instance = PACKER_INSTANCES.get(packer_key)

            if not packer_instance:
                raise HTTPException(status_code=400, detail=f"無效的策略組合: {request.strategy}+{request.algorithm}")

            if isinstance(packer_instance, CP_MCTS_Packer):
                packer_instance.num_simulations = request.num_simu

            # 呼叫 Packer 的 pack 方法
            best_placement = packer_instance.pack(app_state.cage, candidate_items)
            print(f" [伺服器日誌] Packer 返回的放置方案: {best_placement}")
            
            if best_placement:
                item_to_place = best_placement['item']
                position = best_placement['position']
                rotation_type = best_placement['rotation_type']
                
                # 永久更新伺服器端的籠車狀態
                # 注意：pack 方法可能返回了一個 Item 副本，我們要用 ID 在原始列表中找到它
                original_item = next(i for i in candidate_items if i.id == item_to_place.id)
                print(f" [伺服器日誌] 狀態已更新。放置物品 ID: {original_item.id}")

                return UniversalResponse(
                    status="success",
                    decision=PlacementDecision(
                        item=ItemModel(**original_item.to_dict()),
                        position=position,
                        rotation_type=rotation_type
                    )
                )
            else:
                print("  [伺服器日誌] 找不到可行的放置方案。")
                # 同样返回 200 OK，但 status 字段不同，且 decision 为 None
                return UniversalResponse(
                    status="no_move_possible",
                    message="在當前狀態下，找不到任何可行的放置方案。"
                )

        except Exception:
            # 捕捉並回傳詳細的錯誤堆疊，方便除錯
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"執行時發生內部錯誤: {traceback.format_exc()}")

# --- 啟動伺服器 (用於直接運行此檔案) ---
if __name__ == '__main__':
    import uvicorn
    # 運行伺服器，host='0.0.0.0' 允許從外部網路訪問
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
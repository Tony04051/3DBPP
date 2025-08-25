# main.py (API 客戶端版本)

import requests
import json
import csv
import time
# --- 讀取 CSV 檔案，將物品轉換為字典列表 ---
conveyor_items_data = []
try:
    with open('./cases/conveyor_items_4.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 將 CSV 行轉換為符合 API 要求的字典
            item_dict = {
                "id": int(row['id']),
                "base_dimensions": tuple(map(float, row['base_dimensions'].strip('()').split(','))),
                "weight": float(row['weight']),
                "allowed_rotations": list(map(int, row['allowed_rotations'].strip('[]').split(','))),
                "is_fragile": (row['is_fragile'].lower() == 'true')
            }
            conveyor_items_data.append(item_dict)
except FileNotFoundError:
    print("錯誤: 找不到 CSV 檔案。")
    exit()

# --- 初始化流程 ---
print("--- 步驟 1: 初始化遠端裝箱流程 ---")
start_payload = {
    "id": "C001",
    "dimensions": [100, 100, 150], # 與您的 config.py 保持一致
    "weight_limit": 300
}
try:
    response = requests.post("http://127.0.0.1:5000/start_packing", json=start_payload)
    response.raise_for_status() # 如果狀態碼不是 2xx，則拋出異常
    current_cage_state = response.json().get('cage_state')
    print("伺服器端籠車已成功初始化。")
except requests.exceptions.RequestException as e:
    print(f"錯誤: 無法連接到 API 伺服器或初始化失敗: {e}")
    exit()

# --- 狀態管理 ---
temp_area_data = [] # 暫存區也只儲存字典
TEMP_AREA_CAPACITY = 3 
LOOKAHEAD_DEPTH = TEMP_AREA_CAPACITY + 1 

# --- 主迴圈 ---
while conveyor_items_data or temp_area_data:
    
    # 1. 準備候選物品 (字典列表)
    lookahead = conveyor_items_data[:LOOKAHEAD_DEPTH]
    candidates_data = temp_area_data + lookahead
    
    # 2. 準備 API 請求的資料
    # 注意：API 的 request body 中不再需要傳遞 cage_state
    # 因為伺服器自己維護著這個狀態
    api_payload = {
        "strategy": "cp",
        "algorithm": "mcts", # 您可以在這裡切換策略
        "num_simu": 500, # 調整模擬次數
        "candidate_items": candidates_data
    }
    
    # 3. 呼叫 API 進行決策
    print(f"\n--- 正在請求決策 (候選物品IDs: {[item['id'] for item in candidates_data]}) ---")
    try:
        response = requests.post("http://127.0.0.1:5000/decide_next_move", json=api_payload)
        response.raise_for_status()
        response_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"錯誤: API 決策請求失敗: {e}")
        break

    # 4. 根據 API 的回覆來更新本地狀態
    if response_data.get('status') == 'success':
        decision = response_data['decision']
        selected_item_dict = decision['item']
        selected_item_id = selected_item_dict['id']
        
        print(f"✅ 決策結果：放置物品 {selected_item_id} 到 {decision['position']}")
        
        # 從輸送帶或暫存區移除被選中的物品 (基於 id)
        removed = False
        # 先嘗試從暫存區移除
        for i, item in enumerate(temp_area_data):
            if item['id'] == selected_item_id:
                temp_area_data.pop(i)
                removed = True
                break
        # 如果不在暫存區，就從輸送帶移除
        if not removed:
            for i, item in enumerate(conveyor_items_data):
                if item['id'] == selected_item_id:
                    conveyor_items_data.pop(i)
                    break
        
    elif response_data.get('status') == 'no_move_possible':
        print("⚠️ 警告：伺服器找不到可行的放置方案。")
        # 處理暫存區邏輯
        if conveyor_items_data and len(temp_area_data) < TEMP_AREA_CAPACITY:
            item_to_move = conveyor_items_data.pop(0)
            temp_area_data.append(item_to_move)
            print(f"  -> 將物品 {item_to_move['id']} 從輸送帶移入暫存區。")
        else:
            print("  -> 無法移入暫存區 (輸送帶已空或暫存區已滿)。模擬結束。")
            break
    else:
        print(f"錯誤: 收到未知的 API 回應: {response_data}")
        break

    # 為了看到進展，可以選擇性地獲取更新後的籠車狀態
    # response = requests.get("http://127.0.0.1:5000/get_cage_state")
    # print(f"  當前籠車物品數量: {len(response.json()['cage_state']['packed_items'])}")
    time.sleep(1) # 模擬機器人操作延遲


# 迴圈結束後，從伺服器獲取最終的籠車狀態
print("\n--- 模擬結束，正在從伺服器獲取最終籠車狀態 ---")
try:
    response = requests.get("http://127.0.0.1:5000/get_cage_state")
    response.raise_for_status()
    final_cage_state = response.json().get('cage_state')
    
    print("\n📦 最終籠車狀態:")
    print(json.dumps(final_cage_state, indent=2, ensure_ascii=False))
except requests.exceptions.RequestException as e:
    print(f"錯誤: 無法獲取最終籠車狀態: {e}")
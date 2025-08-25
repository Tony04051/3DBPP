import plotly.graph_objects as go
from .data_structures import CageTrolley
from config import CAGE_DIMENSIONS

def plot_cage_plotly(cage: CageTrolley, title="3D Bin Packing Animation"):
    """使用 Plotly 和 `visible` 屬性創建一個健壯的 3D 動畫。"""
    
    packed_items = cage.packed_items
    l, w, h = CAGE_DIMENSIONS
    
    if not packed_items:
        # ... (處理空籠車的程式碼保持不變) ...
        return

    # --- 1. 顏色和幾何定義 ---
    color_palette = [
        '#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', 
        '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52'
    ]
    item_colors = {item.id: color_palette[i % len(color_palette)] for i, item in enumerate(packed_items)}
    
    vertex_indices_i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    vertex_indices_j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    vertex_indices_k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]

    # --- 2. 一次性創建所有的 Mesh3d traces ---
    # 我們先把所有會被放置的箱子都創建好，但先不把它們加到 Figure 中
    all_traces = []
    for item in packed_items:
        if item.position is None:
            continue
        x, y, z = item.position
        dl, dw, dh = item.get_rotated_dimensions(item.rotation_type)
        trace = go.Mesh3d(
            x=[x, x, x + dl, x + dl, x, x, x + dl, x + dl],
            y=[y, y + dw, y + dw, y, y, y + dw, y + dw, y],
            z=[z, z, z, z, z + dh, z + dh, z + dh, z + dh],
            i=vertex_indices_i, j=vertex_indices_j, k=vertex_indices_k,
            opacity=0.8,
            color=item_colors.get(item.id, 'grey'),
            name=f"Item {item.id}",
            visible=False # **關鍵：預設所有箱子都是不可見的**
        )
        all_traces.append(trace)

    # --- 3. 創建 Frames ---
    # 每一幀的任務不再是提供數據，而是告訴 Figure 哪些 trace 應該被設為 `visible=True`
    frames = []
    for k in range(len(packed_items) + 1):
        # 創建一個布林值列表，長度等於總物品數
        # 第 k 幀時，前 k 個物品應該可見
        visibility_list = [True] * k + [False] * (len(packed_items) - k)
        
        frame = go.Frame(
            name=f"Step {k}",
            # `data` 現在是描述如何 "更新" 已存在的 trace
            data=[go.Mesh3d(visible=v) for v in visibility_list]
        )
        frames.append(frame)

    # --- 4. 創建 Figure 並添加所有 Traces ---
    # 我們把所有箱子的 trace 一次性全部加入 Figure
    fig = go.Figure(data=all_traces, frames=frames)

    # 設置初始狀態 (第 0 幀)：所有箱子都不可見
    # `fig.update_traces` 會更新所有已存在的 trace
    fig.update_traces(visible=False, selector=dict(type='mesh3d'))
    # 如果你想讓第一個箱子在初始時就可見，可以只更新第一個
    # if len(all_traces) > 0:
    #     fig.data[0].visible = True
    
    # --- 5. 創建控制器 (Sliders 和 Buttons) ---
    sliders = [{
        "active": 0,
        "steps": [
            {
                "label": f"Step {k}", 
                "method": "restyle", # **方法改變：使用 restyle**
                "args": ["visible", [True] * k + [False] * (len(packed_items) - k)]
            } for k in range(len(packed_items) + 1)
        ],
        "pad": {"t": 50, "b": 10}, "x": 0.1, "len": 0.7, "xanchor": "left"
    }]
    
    updatemenus = [{
        "type": "buttons",
        "showactive": False,
        "buttons": [
            {"label": "Play", "method": "animate", "args": [None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True, "transition": {"duration": 0}}]},
            {"label": "Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]}
        ],
        "x": 0.1,         # X 座標。
        "y": 1.1,         # Y 座標。設為大於 1 的值可以將按鈕放在圖表標題的上方。
        "xanchor": "left",# X 軸錨點。
        "yanchor": "top", # Y 軸錨點。
    }]

    # --- 6. 設定最終佈局 ---
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis=dict(title='Length (X)', range=[0, l]),
            yaxis=dict(title='Width (Y)', range=[0, w]),
            zaxis=dict(title='Height (Z)', range=[0, h]),
            aspectmode='data'
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        sliders=sliders,
        updatemenus=updatemenus
    )

    fig.show(renderer="browser")

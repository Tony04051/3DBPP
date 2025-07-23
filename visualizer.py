import plotly.graph_objects as go
from bpp_solver.data_structures import CageTrolley

def plot_cage_plotly(cage: CageTrolley, title="3D Bin Packing Result (Plotly)"):
    """使用 Plotly 將籠車和內部物品可視化"""
    fig = go.Figure()

    # 1. 繪製已放置的物品
    for i, item in enumerate(cage.packed_items):
        if item.position is None:
            continue
        x, y, z = item.position
        dl, dw, dh = item.get_rotated_dimensions(item.rotation_type)
        
        fig.add_trace(go.Mesh3d(
            # 立方體的8個頂點
            x=[x, x, x+dl, x+dl, x, x, x+dl, x+dl],
            y=[y, y+dw, y+dw, y, y, y+dw, y+dw, y],
            z=[z, z, z, z, z+dh, z+dh, z+dh, z+dh],
            # 頂點如何連接成面
            # 解釋：每個面由4個頂點組成，這裡的 i, j, k 分別代表頂點索引
            i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2],
            j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3],
            k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
            opacity=0.8,
            name=f"Item {item.id}",
            text=f"ID: {item.id}<br>Pos: ({x:.1f}, {y:.1f}, {z:.1f})<br>Dims: ({dl:.1f}, {dw:.1f}, {dh:.1f})",
            hoverinfo='text'
        ))

    # 2. 設定佈局和籠車邊界
    l, w, h = cage.dimensions
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis=dict(title='Length (X)', range=[0, l]),
            yaxis=dict(title='Width (Y)', range=[0, w]),
            zaxis=dict(title='Height (Z)', range=[0, h]),
            aspectmode='data' # 保持長寬高比例
        ),
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    fig.show()
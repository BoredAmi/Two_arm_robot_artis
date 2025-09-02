import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle

def animate_points(ax, paths, colors=None, interval=1, on_frame=None, show_left_forbidden=True, forbidden_rect=(0, 0, 130, 40), invert_y=True, arm_roles=None):
    """
    Animate drawing of all points in all paths, N points at a time (very fast).
    - ax: matplotlib Axes
    - paths: list of list of (x, y) points
    - colors: list of colors for each path
    - interval: ms between frames (default 1ms for speed)
    - on_frame: callback(frame) for integration with Tkinter
    - points_per_frame: how many points to draw per frame (default 10)
    - invert_y: whether to invert y-axis so (0,0) is at top-left (default True)
    - arm_roles: list of 'left' or 'right' for each path (for dual-arm mode)
    Returns: FuncAnimation object
    """
    points_per_frame = 10  # You can change this value for more/less speed
    if colors is None:
        if arm_roles is not None:
            # Professional/Industrial color scheme - standardized safety colors
            colors = []
            for role in arm_roles:
                if role == 'right':
                    colors.append('#004E89')  # Deep Blue - professional, reliable
                elif role == 'left':
                    colors.append('#FF6B35')  # Safety Orange - industrial safety standard
                else:
                    colors.append('#9E9E9E')  # Gray - fallback for unknown roles
        else:
            colors = [plt.cm.tab20(i % 20) for i in range(len(paths))]
    
    # Apply y-axis inversion if requested and not already inverted
    if invert_y and not ax.yaxis_inverted():
        ax.invert_yaxis()
    
    lines = []
    for i in range(len(paths)):
        line, = ax.plot([], [], '-', color=colors[i], linewidth=1)
        lines.append(line)
    # Flatten all points with path index
    point_indices = []
    for path_idx, path in enumerate(paths):
        for pt_idx in range(1, len(path)+1):
            point_indices.append((path_idx, pt_idx))
    total_frames = (len(point_indices) + points_per_frame - 1) // points_per_frame
    def init():
        for line in lines:
            line.set_data([], [])
        # Draw left-arm forbidden rectangle (if requested)
        if show_left_forbidden:
            try:
                x0, y0, w, h = forbidden_rect
                # Industrial safety red fill for the forbidden area
                forb_fill = Rectangle((x0, y0), w, h, facecolor='#FFCDD2', alpha=0.7, edgecolor='#FF1744', linewidth=2, linestyle='--')
                ax.add_patch(forb_fill)
                # Add text label to identify the forbidden area
                ax.text(x0 + w/2, y0 + h/2, 'Left\nForbidden\n(0,0)-(130,40)', 
                       ha='center', va='center', fontsize=8, color='#C62828', weight='bold')
            except Exception as e:
                print(f"Error adding forbidden rectangle: {e}")
        return lines
    def update(frame):
        last_idx = min((frame+1)*points_per_frame, len(point_indices))
        # Find up to which path/point to draw
        drawn = point_indices[:last_idx]
        # For each path, find max pt_idx to draw
        max_pts = {}
        for path_idx, pt_idx in drawn:
            max_pts[path_idx] = max(max_pts.get(path_idx, 0), pt_idx)
        for i, line in enumerate(lines):
            if i in max_pts:
                xs = [p[0] for p in paths[i][:max_pts[i]]]
                ys = [p[1] for p in paths[i][:max_pts[i]]]
                line.set_data(xs, ys)
            else:
                line.set_data([], [])
        if on_frame:
            on_frame(frame)
        return lines
    anim = FuncAnimation(
        ax.figure, update, frames=total_frames, init_func=init,
        interval=1, blit=False, repeat=False
    
    )
    
    return anim

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

def animate_points(ax, paths, colors=None, interval=1, on_frame=None):
    """
    Animate drawing of all points in all paths, N points at a time (very fast).
    - ax: matplotlib Axes
    - paths: list of list of (x, y) points
    - colors: list of colors for each path
    - interval: ms between frames (default 1ms for speed)
    - on_frame: callback(frame) for integration with Tkinter
    - points_per_frame: how many points to draw per frame (default 10)
    Returns: FuncAnimation object
    """
    points_per_frame = 10  # You can change this value for more/less speed
    if colors is None:
        colors = [plt.cm.tab20(i % 20) for i in range(len(paths))]
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

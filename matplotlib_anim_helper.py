# Matplotlib animation helper for path-by-path drawing
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle


def animate_paths(ax, paths, colors=None, interval=50, on_frame=None, show_left_forbidden=False, forbidden_rect=(0, 0, 130, 40)):
    """
    Animate drawing of paths on the given axes, one path at a time.
    - ax: matplotlib Axes
    - paths: list of list of (x, y) points
    - colors: list of colors for each path
    - interval: ms between frames
    - on_frame: callback(frame) for integration with Tkinter
    Returns: FuncAnimation object
    """
    if colors is None:
        colors = [plt.cm.tab20(i % 20) for i in range(len(paths))]
    lines = []
    for i in range(len(paths)):
        line, = ax.plot([], [], '-', color=colors[i], linewidth=1)
        lines.append(line)

    def init():
        for line in lines:
            line.set_data([], [])
        # Draw left-arm forbidden rectangle once (if requested)
        if show_left_forbidden:
            try:
                x0, y0, w, h = forbidden_rect
                # Semi-transparent red with hatch to indicate forbidden area
                forb = Rectangle((x0, y0), w, h, facecolor='red', alpha=0.12, edgecolor='red', hatch='//')
                # Add as a non-updating artist so it stays visible throughout the animation
                ax.add_patch(forb)
            except Exception:
                pass
        return lines

    def update(frame):
        for i, line in enumerate(lines):
            if i <= frame:
                xs = [p[0] for p in paths[i]]
                ys = [p[1] for p in paths[i]]
                line.set_data(xs, ys)
            else:
                line.set_data([], [])
        if on_frame:
            on_frame(frame)
        return lines

    anim = FuncAnimation(
        ax.figure, update, frames=len(paths), init_func=init,
        interval=200, blit=False, repeat=False
    )
    return anim

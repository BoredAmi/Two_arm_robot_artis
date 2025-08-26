# Matplotlib animation helper for path-by-path drawing
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def animate_paths(ax, paths, colors=None, interval=50, on_frame=None):
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

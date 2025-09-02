# Matplotlib animation helper for path-by-path drawing
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle


def animate_paths(ax, paths, colors=None, interval=50, on_frame=None, show_left_forbidden=False, forbidden_rect=(0, 0, 130, 40), invert_y=True, arm_roles=None):
    """
    Animate drawing of paths on the given axes, one path at a time.
    - ax: matplotlib Axes
    - paths: list of list of (x, y) points
    - colors: list of colors for each path
    - interval: ms between frames
    - on_frame: callback(frame) for integration with Tkinter
    - invert_y: whether to invert y-axis so (0,0) is at top-left (default True)
    - arm_roles: list of 'left' or 'right' for each path (for dual-arm mode)
    Returns: FuncAnimation object
    """
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
    
    # Transform paths to mirror them vertically if invert_y is True
    transformed_paths = []
    if invert_y:
        # Get workspace height for transformation (assuming 210mm standard)
        workspace_height = 210
        for path in paths:
            if path:
                transformed_path = [(x, workspace_height - y) for x, y in path]
                transformed_paths.append(transformed_path)
            else:
                transformed_paths.append(path)
    else:
        transformed_paths = paths
    
    lines = []
    for i in range(len(transformed_paths)):
        line, = ax.plot([], [], '-', color=colors[i], linewidth=1)
        lines.append(line)

    def init():
        for line in lines:
            line.set_data([], [])
        # Draw left-arm forbidden rectangle once (if requested)
        if show_left_forbidden:
            try:
                x0, y0, w, h = forbidden_rect
                # Transform forbidden rectangle if we're inverting
                if invert_y:
                    workspace_height = 210
                    y0_transformed = workspace_height - y0 - h  # Flip the rectangle too
                    forb_fill = Rectangle((x0, y0_transformed), w, h, facecolor='#FFCDD2', alpha=0.7, edgecolor='#FF1744', linewidth=2, linestyle='--')
                else:
                    forb_fill = Rectangle((x0, y0), w, h, facecolor='#FFCDD2', alpha=0.7, edgecolor='#FF1744', linewidth=2, linestyle='--')
                ax.add_patch(forb_fill)
                # Add text label to identify the forbidden area
                if invert_y:
                    ax.text(x0 + w/2, y0_transformed + h/2, 'Left\nForbidden\n(0,0)-(130,40)', 
                           ha='center', va='center', fontsize=8, color='#C62828', weight='bold')
                else:
                    ax.text(x0 + w/2, y0 + h/2, 'Left\nForbidden\n(0,0)-(130,40)', 
                           ha='center', va='center', fontsize=8, color='#C62828', weight='bold')
            except Exception as e:
                print(f"Error adding forbidden rectangle: {e}")
        return lines

    def update(frame):
        for i, line in enumerate(lines):
            if i <= frame:
                xs = [p[0] for p in transformed_paths[i]]
                ys = [p[1] for p in transformed_paths[i]]
                line.set_data(xs, ys)
            else:
                line.set_data([], [])
        if on_frame:
            on_frame(frame)
        return lines

    anim = FuncAnimation(
        ax.figure, update, frames=len(transformed_paths), init_func=init,
        interval=200, blit=False, repeat=False
    )
    return anim

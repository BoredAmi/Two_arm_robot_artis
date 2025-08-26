"""
Animated visualization of dual-arm assignment and forbidden zones for each step.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
from coordinate_transformer import master_slave_assign_contours
from robot_drawer import RobotDrawer

# --- Helper for animation ---
def animate_dual_assignment(contours, xlim=(-150, 150), ylim=(-120, 120)):
    steps = []
    remaining = contours[:]
    master_role = 'right'
    while remaining:
        # buffer_x/buffer_y are ignored, forbidden area is always 30mm radius from every point
        result = master_slave_assign_contours(remaining, master=master_role)
        if len(result) == 5:
            master, slave, rest, unassigned, forbidden_poly = result
        else:
            master, slave, rest, unassigned = result
            forbidden_poly = None
        steps.append((remaining[:], master_role, master, slave, forbidden_poly))
        remaining = rest
        master_role = 'left' if master_role == 'right' else 'right'
    # --- Animation setup ---
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')
    ax.set_title('Dual-arm assignment animation')
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
    legend_handles = [
        mpatches.Patch(color='red', alpha=0.15, label='Forbidden zone', hatch='//'),
        mpatches.Patch(color='red', label='Master'),
        mpatches.Patch(color='blue', label='Slave'),
    ]
    def plot_contour(ax, contour, color, lw=2, alpha=1.0, zorder=1):
        xs, ys = zip(*contour)
        xs = list(xs) + [xs[0]]
        ys = list(ys) + [ys[0]]
        ax.plot(xs, ys, color=color, lw=lw, alpha=alpha, zorder=zorder)
    def update(frame):
        ax.clear()
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect('equal')
        ax.set_title(f'Step {frame+1} / {len(steps)}')
        ax.legend(handles=legend_handles)
        remaining, master_role, master, slave, forbidden_poly = steps[frame]
        # Plot all remaining contours
        for i, c in enumerate(remaining):
            plot_contour(ax, c, color=colors[i%len(colors)], lw=1, alpha=0.5, zorder=1)
        # Plot forbidden area
        if forbidden_poly is not None:
            if forbidden_poly.geom_type == 'Polygon':
                polys = [forbidden_poly]
            else:
                polys = list(forbidden_poly.geoms)
            for poly in polys:
                x_f, y_f = poly.exterior.xy
                ax.fill(x_f, y_f, color='red', alpha=0.15, zorder=2, hatch='//')
        # Plot master
        if master:
            plot_contour(ax, master, color='red', lw=3, alpha=1.0, zorder=3)
        # Plot slave
        if slave:
            plot_contour(ax, slave, color='blue', lw=3, alpha=1.0, zorder=3)
    ani = FuncAnimation(fig, update, frames=len(steps), interval=1200, repeat=False)
    plt.show()

if __name__ == "__main__":
    import tkinter as tk
    from tkinter import filedialog
    # File dialog to choose image
    root = tk.Tk()
    root.withdraw()
    image_path = filedialog.askopenfilename(
        title="Select image for dual-arm animation",
        filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")]
    )
    if not image_path:
        print("No image selected. Exiting.")
        exit(1)
    drawer = RobotDrawer()
    if not drawer.load_image(image_path, precision="high", detection_method="threshold"):
        print("Failed to load/process image.")
        exit(1)
    animate_dual_assignment(drawer.drawing_points)

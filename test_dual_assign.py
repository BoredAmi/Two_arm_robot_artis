from shapely.geometry import box
import matplotlib.pyplot as plt
from coordinate_transformer import master_slave_assign_contours, get_contour_bounds
def make_rect_contour(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def make_triangle_contour(x0, y0, x1, y1, x2, y2):
    return [(x0, y0), (x1, y1), (x2, y2)]

def make_circle_contour(cx, cy, r, n=20):
    import math
    return [
        (cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]

def make_polygon_contour(cx, cy, r, sides=5):
    import math
    return [
        (cx + r * math.cos(2 * math.pi * i / sides), cy + r * math.sin(2 * math.pi * i / sides))
        for i in range(sides)
    ]

    import math
    return [
        (cx + r * math.cos(2 * math.pi * i / sides), cy + r * math.sin(2 * math.pi * i / sides))
        for i in range(sides)
    ]


def plot_contour(ax, contour, color, label=None, alpha=1.0, lw=2, zorder=1):
    xs, ys = zip(*contour)
    xs = list(xs) + [xs[0]]
    ys = list(ys) + [ys[0]]
    ax.plot(xs, ys, color=color, label=label, alpha=alpha, lw=lw, zorder=zorder)

def plot_bounds(ax, bounds, color, label=None, alpha=0.2, zorder=0):
    min_x, max_x, min_y, max_y = bounds
    rect = plt.Rectangle((min_x, min_y), max_x-min_x, max_y-min_y, color=color, alpha=alpha, label=label, zorder=zorder)
    ax.add_patch(rect)

def comprehensive_dual_assign_viz():
    # Many test contours, some overlapping, some far, some touching
    contours = [
        # Rectangles
        make_rect_contour(-120, -60, -80, 60),   # far left
        make_rect_contour(-60, -30, -20, 30),    # left
        make_rect_contour(20, -30, 60, 30),      # right
        make_rect_contour(80, -60, 120, 60),     # far right
        make_rect_contour(-10, 40, 10, 80),      # center top
        make_rect_contour(-10, -80, 10, -40),    # center bottom
        make_rect_contour(-15, -15, 15, 15),     # center
        make_rect_contour(-100, 70, -60, 100),   # far left top
        make_rect_contour(60, 70, 100, 100),     # far right top
        # Triangles
        make_triangle_contour(-130, -100, -110, -80, -120, -40), # far far left triangle
        make_triangle_contour(130, 100, 110, 80, 120, 40), # far far right triangle
        make_triangle_contour(0, 0, 20, 40, -20, 40), # center triangle
        # Circles
        make_circle_contour(-80, 0, 15), # left circle
        make_circle_contour(80, 0, 15),  # right circle
        make_circle_contour(0, 90, 10),  # top center circle
        # Polygons
        make_polygon_contour(-40, -90, 12, sides=5), # left pentagon
        make_polygon_contour(40, -90, 12, sides=6),  # right hexagon
        make_polygon_contour(0, 0, 25, sides=7),     # center heptagon
        # Odd shapes
        [(0, -100), (10, -110), (20, -100), (10, -90)], # diamond bottom
        [(-50, 50), (-40, 60), (-30, 50), (-40, 40)],   # diamond left top
    ]
    buffer_x = 10
    buffer_y = 35
    master_role = 'right'
    step = 0
    remaining = contours[:]
    colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
    figs = []
    while remaining:
        print(f"\nStep {step+1} (master: {master_role})")
        # Now returns master, slave, rest, unassigned, forbidden_poly
        result = master_slave_assign_contours(remaining, master=master_role, buffer_x=buffer_x, buffer_y=buffer_y)
        if len(result) == 5:
            master, slave, rest, unassigned, forbidden_poly = result
        else:
            master, slave, rest, unassigned = result
            forbidden_poly = None
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        # Plot all remaining contours
        for i, c in enumerate(remaining):
            plot_contour(ax, c, color=colors[i%len(colors)], label=f'contour {i}', alpha=0.5, lw=1, zorder=1)
        # Plot master
        if master:
            plot_contour(ax, master, color='red', label='master', alpha=1.0, lw=3, zorder=3)
        # Draw forbidden area as a polygon (shapely)
        if forbidden_poly is not None:
            if forbidden_poly.geom_type == 'Polygon':
                polys = [forbidden_poly]
            else:
                polys = list(forbidden_poly.geoms)
            for poly in polys:
                x_f, y_f = poly.exterior.xy
                ax.fill(x_f, y_f, color='red', alpha=0.15, label='forbidden area', zorder=2, hatch='//')
        # Plot slave
        if slave:
            plot_contour(ax, slave, color='blue', label='slave', alpha=1.0, lw=3, zorder=3)
        # Legend and limits
        ax.legend()
        ax.set_title(f'Step {step+1}: master={master_role}\nRed=master, Blue=slave, shaded=forbidden')
        ax.set_aspect('equal')
        ax.set_xlim(-150, 150)
        ax.set_ylim(-120, 120)
        figs.append(fig)
        print(f"Master: {master}\nSlave: {slave}\nRemaining: {len(rest)}")
        # Prepare for next step
        remaining = rest
        master_role = 'left' if master_role == 'right' else 'right'
        step += 1
    # Show all figures at the end
    for fig in figs:
        fig.show()

if __name__ == "__main__":
    comprehensive_dual_assign_viz()
    plt.show()
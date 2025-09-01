"""
Debug test for animate_paths to see what's happening with y-axis inversion.
"""
import matplotlib.pyplot as plt
from matplotlib_anim_helper import animate_paths

def debug_animate_paths():
    """Debug the animate_paths y-axis inversion issue"""
    
    # Simple test path
    test_paths = [
        [(10, 10), (90, 10), (90, 90), (10, 90), (10, 10)]  # Square
    ]
    
    print("Testing animate_paths with invert_y=True...")
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Set up the axes BEFORE calling animate_paths
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.set_title('animate_paths Debug Test')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    # Add corner markers to show current orientation
    ax.plot(0, 0, 'ro', markersize=10, label='(0,0)')
    ax.plot(100, 0, 'go', markersize=10, label='(100,0)')
    ax.plot(0, 100, 'bo', markersize=10, label='(0,100)')
    ax.plot(100, 100, 'mo', markersize=10, label='(100,100)')
    
    print(f"Before animate_paths: Y-axis inverted = {ax.yaxis_inverted()}")
    
    # Call animate_paths with invert_y=True
    anim = animate_paths(ax, test_paths, interval=2000, invert_y=True, show_left_forbidden=True)
    
    print(f"After animate_paths: Y-axis inverted = {ax.yaxis_inverted()}")
    
    # Test double inversion protection
    print("Testing double inversion protection...")
    print(f"Before second call: Y-axis inverted = {ax.yaxis_inverted()}")
    
    # This should NOT double-invert
    anim2 = animate_paths(ax, test_paths, interval=2000, invert_y=True, show_left_forbidden=False)
    
    print(f"After second call: Y-axis inverted = {ax.yaxis_inverted()}")
    print("If protection works, y-axis should still be inverted (True)")
    
    ax.legend()
    plt.show()
    
    print("Debug test completed!")

if __name__ == "__main__":
    debug_animate_paths()

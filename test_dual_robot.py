# Dual-robot drawing test
# This script demonstrates how to use draw_paths_dual for coordinated drawing.

from robot_communication import RobotController

# Example: split contours for right and left robots

# Example: split actions for right and left robots, including 'wait'
def example_actions():
    # Replace with your real contour data
    right = [
        [(10, 10), (20, 10), (20, 20), (10, 20)],
        'wait',
        [(30, 30), (40, 30), (40, 40), (30, 40)]
    ]
    left = [
        [(-10, 10), (-20, 10), (-20, 20), (-10, 20)],
        [(-30, 30), (-40, 30), (-40, 40), (-30, 40)],
        'wait'
    ]
    return right, left

if __name__ == "__main__":
    rc = RobotController()
    if not rc.connect():
        print("Failed to connect to both robots.")
        exit(1)
    right_actions, left_actions = example_actions()
    rc.draw_paths_dual(right_actions, left_actions)
    rc.disconnect()

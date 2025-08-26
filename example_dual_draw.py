"""
Example script for dual-arm robot drawing using RobotDrawer.draw_dual().
"""
from robot_drawer import RobotDrawer

if __name__ == "__main__":
    # Initialize RobotDrawer (adjust IP/port if needed)
    drawer = RobotDrawer()
    
    # Connect to both robots
    if not drawer.connect():
        print("Failed to connect to robot(s). Exiting.")
        exit(1)

    # Load and process an image (replace with your image path)
    image_path = "out.png"  # Use your own image file here
    if not drawer.load_image(image_path, precision="high", detection_method="threshold"):
        print("Failed to load/process image.")
        exit(1)

    # (Optional) Preview the planned drawing
    drawer.plot_preview()
    input("Press Enter to start dual-arm drawing...")

    # Start dual-arm drawing (buffer_x/buffer_y can be tuned)
    success = drawer.draw_dual(buffer_x=10, buffer_y=70)
    if success:
        print("Dual-arm drawing completed!")
    else:
        print("Dual-arm drawing failed.")

    # Disconnect from robots
    drawer.disconnect()

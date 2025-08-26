"""
Command-Line Interface for the Robot Drawing System.

This module provides a command-line interface for the Robot Drawing System,
offering a text-based workflow for advanced users and automation scenarios.

Features:
- Interactive command-line interface
- Image processing with configurable precision
- Detection method selection (Threshold, Canny, Adaptive, Canny+Fill)
- Drawing dimensions configuration
- TSP optimization controls
- Robot connection and drawing execution
- Text-based preview and confirmation
- Batch processing capabilities

The CLI interface provides full access to all system features while
maintaining simplicity for scripting and automation use cases.

Usage: python cli.py

Version: 1.0
"""
import os
import time
from robot_drawer import RobotDrawer


def main():
    """
    Command-line interface for the Robot Drawing System.
    
    Provides an interactive workflow for:
    1. TSP optimization configuration
    2. Drawing dimensions configuration  
    3. Image loading and processing
    4. Detection method selection
    5. Precision level selection
    6. Drawing preview and confirmation
    7. Robot connection and execution
    """
    print("=== Robot Drawing System ===")
    print("Command-Line Interface v1.0\n")
    
    # TSP optimization configuration
    tsp_choice = input("Enable TSP path optimization? (y/n, default=y): ").strip().lower()
    enable_tsp = tsp_choice != 'n'
    
    print(f"TSP Optimization: {'ENABLED' if enable_tsp else 'DISABLED'}")
    
    # Drawing dimensions configuration
    print("\nDrawing Area Configuration:")
    dimension_choice = input("Use default dimensions 290x210mm (A4)? (y/n, default=y): ").strip().lower()
    
    if dimension_choice == 'n':
        try:
            max_x = int(input("Enter drawing width in mm (50-500, default=290): ").strip() or "290")
            max_x = max(50, min(500, max_x))  # Clamp values
            
            max_y = int(input("Enter drawing height in mm (50-400, default=210): ").strip() or "210")
            max_y = max(50, min(400, max_y))  # Clamp values
            
            print(f"Drawing area set to: {max_x}x{max_y}mm")
        except ValueError:
            print("Invalid input, using default dimensions")
            max_x, max_y = 290, 210
    else:
        max_x, max_y = 290, 210
    
    # Initialize drawer with user's preferences
    drawer = RobotDrawer(max_x=max_x, max_y=max_y, enable_tsp=enable_tsp)
    
    image_path = input("Enter path to image file (or press Enter to skip): ").strip()
    
    if image_path and os.path.exists(image_path):
        # Choose detection method
        detection_choice = input("Detection method: (1) Threshold (2) Canny (3) Adaptive (4) Canny+Fill (default=1): ").strip()
        if detection_choice == "2":
            detection_method = "canny"
        elif detection_choice == "3":
            detection_method = "adaptive"
        elif detection_choice == "4":
            detection_method = "canny_filled"
        else:
            detection_method = "threshold"
        
        # Choose precision level
        precision_choices = {"1": "highest", "2": "high", "3": "medium", "4": "low"}
        choice = input("Precision: (1) Highest (2) High (3) Medium (4) Low (default=2): ").strip()
        precision = precision_choices.get(choice, "high")
        
        # Load and process image using optimized edge following
        success = drawer.load_image(image_path, precision=precision, detection_method=detection_method)
        
        if success:
            # Show processing steps
            drawer.show_processing_steps(image_path)
            
            # Show graphical preview
            drawer.plot_preview()
            
            # Optional text preview
            if input("Show text coordinates? (y/n): ").strip().lower() == 'y':
                drawer.preview_points()
            
            # Proceed with drawing
            if input("Proceed with drawing? (y/n): ").strip().lower() == 'y':
                # Ask about batch settings
                batch_choice = input("Use batch coordinate sending for better performance? (y/n, default=y): ").strip().lower()
                use_batching = batch_choice != 'n'
                
                batch_size = 3  # Default
                if use_batching:
                    size_input = input("Batch size (1-4, default=3): ").strip()
                    try:
                        batch_size = int(size_input) if size_input else 3
                        batch_size = max(1, min(4, batch_size))  # Clamp to valid range
                    except ValueError:
                        batch_size = 3
                
                print(f"Drawing with {'batch' if use_batching else 'individual'} coordinate sending")
                if use_batching:
                    print(f"Batch size: {batch_size} coordinates per command")
                
                if drawer.connect():
                    try:
                        drawer.draw(move_delay=0.02, use_batching=use_batching, batch_size=batch_size)
                    finally:
                        drawer.disconnect()
                else:
                    print("Failed to connect to robot")
            else:
                print("Drawing cancelled.")
        else:
            print("Failed to load image.")
    
    else:
        # Fallback example - draw rectangle border
        print("Running rectangle drawing example...")
        if drawer.connect():
            try:
                # Draw rectangle border (290x210mm area)
                drawer.send_move(0, 0)
                time.sleep(1)
                drawer.send_move(290, 0)
                time.sleep(1)
                drawer.send_move(290, 210)
                time.sleep(1)
                drawer.send_move(0, 210)
                time.sleep(1)
                drawer.send_stop()
                time.sleep(3)
            finally:
                drawer.disconnect()


if __name__ == "__main__":
    main()

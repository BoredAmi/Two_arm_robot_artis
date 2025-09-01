"""
Visualization module for plotting and previewing drawing points.

Handles matplotlib operations and preview functionality for the Robot Drawing System.
The visualizer displays coordinates in the centered coordinate system where (0,0)
is at the center of the drawing area.

Features:
- Preview drawing paths with coordinate grids
- Display coordinate ranges from -max/2 to +max/2
- Show center point and axis lines for reference
- Process visualization steps (original → edges → robot coordinates)
- Color-coded contours for easy identification
"""
import matplotlib.pyplot as plt
import numpy as np
import cv2


class DrawingVisualizer:
    def __init__(self, max_x=290, max_y=210):
        self.max_x = max_x
        self.max_y = max_y
    
    def preview_points_text(self, drawing_points, max_display=50):
        """Preview the extracted points in text format"""
        if not drawing_points:
            print("No points to preview.")
            return
        
        print(f"Drawing consists of {len(drawing_points)} contour(s):")
        for i, contour in enumerate(drawing_points):
            print(f"  Contour {i+1}: {len(contour)} points")
            if len(contour) <= max_display:
                for j, (x, y) in enumerate(contour):
                    print(f"    Point {j+1}: ({x:.2f}, {y:.2f})")
            else:
                print(f"    First 5 points:")
                for j, (x, y) in enumerate(contour[:5]):
                    print(f"    Point {j+1}: ({x:.2f}, {y:.2f})")
                print(f"    ... and {len(contour)-5} more points")
    
    def plot_preview(self, drawing_points):
        """Show graphical preview of all drawing points"""
        if not drawing_points:
            print("No points to preview.")
            return
        
        plt.figure(figsize=(12, 8))
        
        # Create different colors for each contour
        colors = plt.cm.tab10(np.linspace(0, 1, len(drawing_points)))
        
        for i, contour in enumerate(drawing_points):
            if len(contour) > 0:
                # Extract X and Y coordinates
                x_coords = [point[0] for point in contour]
                y_coords = [point[1] for point in contour]
                
                # Plot the contour
                plt.plot(x_coords, y_coords, 'o-', color=colors[i], 
                        linewidth=2, markersize=3, label=f'Contour {i+1} ({len(contour)} points)')
                
                # Mark start point with larger marker
                if len(contour) > 0:
                    plt.plot(x_coords[0], y_coords[0], 'o', color=colors[i], 
                            markersize=8, markeredgecolor='black', markeredgewidth=2)
        
        # Set up the plot with centered coordinate system
        plt.xlim(-self.max_x/2, self.max_x/2)
        plt.ylim(-self.max_y/2, self.max_y/2)
        
        # Invert y-axis so (0,0) is at top-left corner
        plt.gca().invert_yaxis()
        
        plt.xlabel('X coordinate (mm)')
        plt.ylabel('Y coordinate (mm)')
        plt.title('Robot Drawing Preview - All Points')
        plt.grid(True, alpha=0.3)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Draw drawing area border (centered coordinate system)
        border_x = [-self.max_x/2, self.max_x/2, self.max_x/2, -self.max_x/2, -self.max_x/2]
        border_y = [-self.max_y/2, -self.max_y/2, self.max_y/2, self.max_y/2, -self.max_y/2]
        plt.plot(border_x, border_y, 'k-', linewidth=3, label='Drawing area border')
        
        # Draw center axes to show (0,0) position
        plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        
        # Mark center point
        plt.plot(0, 0, 'r+', markersize=10, markeredgewidth=2, label='Center (0,0)')
        
        # Add some statistics
        total_points = sum(len(contour) for contour in drawing_points)
        plt.figtext(0.02, 0.02, f'Total points: {total_points} | Total contours: {len(drawing_points)}', 
                   fontsize=10, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        plt.tight_layout()
        plt.show()
        
        print(f"Preview shows {len(drawing_points)} contours with {sum(len(c) for c in drawing_points)} total points")
        print("Large dots with black borders mark the starting points of each contour")
    
    def show_processing_steps(self, image_data, drawing_points):
        """Show complete processing pipeline: original -> edges -> final points"""
        if not image_data:
            print("No image data available for visualization")
            return
        
        # Create the plot
        plt.figure(figsize=(15, 5))
        
        # Original image
        plt.subplot(131)
        plt.imshow(cv2.cvtColor(image_data['original'], cv2.COLOR_BGR2RGB))
        plt.title('1. Original Image')
        plt.xticks([]), plt.yticks([])
        
        # Edge detection
        plt.subplot(132)
        plt.imshow(image_data['edges'], cmap='gray')
        plt.title('2. Edge Detection (Canny)')
        plt.xticks([]), plt.yticks([])
        
        # Drawing preview
        plt.subplot(133)
        if drawing_points:
            colors = plt.cm.tab10(np.linspace(0, 1, len(drawing_points)))
            
            for i, contour in enumerate(drawing_points):
                if len(contour) > 0:
                    x_coords = [point[0] for point in contour]
                    y_coords = [point[1] for point in contour]
                    
                    plt.plot(x_coords, y_coords, 'o-', color=colors[i], 
                            linewidth=1.5, markersize=2)
            
            # Drawing area border (centered coordinate system)
            border_x = [-self.max_x/2, self.max_x/2, self.max_x/2, -self.max_x/2, -self.max_x/2]
            border_y = [-self.max_y/2, -self.max_y/2, self.max_y/2, self.max_y/2, -self.max_y/2]
            plt.plot(border_x, border_y, 'k-', linewidth=2)
            
            # Draw center axes
            plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            plt.plot(0, 0, 'r+', markersize=8, markeredgewidth=2)
            
            plt.xlim(-self.max_x/2, self.max_x/2)
            plt.ylim(-self.max_y/2, self.max_y/2)
            
            # Invert y-axis so (0,0) is at top-left corner
            plt.gca().invert_yaxis()
            
            plt.xlabel('X (mm)')
            plt.ylabel('Y (mm)')
            
            total_points = sum(len(contour) for contour in drawing_points)
            plt.title(f'3. Robot Drawing Preview\n({total_points} points)')
        else:
            plt.text(0.5, 0.5, 'No drawing points\nLoad image first', 
                    ha='center', va='center', transform=plt.gca().transAxes)
            plt.title('3. Robot Drawing Preview')
        
        plt.tight_layout()
        plt.show()

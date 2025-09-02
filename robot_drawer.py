"""
Main RobotDrawer class that orchestrates all components.

This module provides the primary interface for the Robot Drawing System,
coordinating between image processing, coordinate transformation, robot
communication, and visualization components.

Key Features:
- Simplified image-to-robot drawing workflow
- Automatic coordinate transformation and scaling
- Real-time visualization and preview
- Configurable precision and optimization settings
- Direct robot communication and control

The RobotDrawer class serves as the main orchestrator, hiding the complexity
of the individual subsystems behind a clean, easy-to-use interface.

Version: 1.0
"""
import os
from robot_communication import RobotController
from image_processor import ImageProcessor
from coordinate_transformer import CoordinateTransformer
from visualizer import DrawingVisualizer


class RobotDrawer:
    def draw_dual(self, buffer_radius=40, buffer_x=10, buffer_y=70, progress_callback=None):
        """
        Dual-arm drawing: assigns contours to right/left arms step by step using forbidden area logic, then draws with both robots in sync.
        Args:
            buffer_x, buffer_y: Forbidden area buffer parameters (mm)
            progress_callback: Optional callback for progress updates
        Returns:
            True if drawing completed successfully, False otherwise
        """
        from coordinate_transformer import master_slave_assign_contours
        if not self.drawing_points or len(self.drawing_points) < 2:
            print("Not enough contours for dual-arm drawing.")
            return False
        # Prepare assignment lists for each step
        remaining = self.drawing_points[:]
        master_role = 'right'
        right_actions = []
        left_actions = []
        step = 0
        while remaining:
            # Use the latest master_slave_assign_contours (returns forbidden_poly as last value)
            result = master_slave_assign_contours(remaining, master=master_role, buffer_radius=buffer_radius, buffer_x=buffer_x, buffer_y=buffer_y)
            if len(result) == 5:
                master, slave, rest, unassigned, _ = result
            else:
                master, slave, rest, unassigned = result
            # Assign contours to each arm for this step
            if master_role == 'right':
                right_actions.append(master)
                left_actions.append(slave if slave else 'wait')
            else:
                left_actions.append(master)
                right_actions.append(slave if slave else 'wait')
            remaining = rest
            master_role = 'left' if master_role == 'right' else 'right'
            step += 1
        print(f"Prepared {len(right_actions)} steps for dual-arm drawing.")
        # Remove any None actions (shouldn't happen, but for safety)
        right_actions = [a if a is not None else 'wait' for a in right_actions]
        left_actions = [a if a is not None else 'wait' for a in left_actions]
        # Start dual-arm drawing
        return self.robot.draw_paths_dual(right_actions, left_actions, progress_callback=progress_callback)
    """
    Main orchestrator class for the Robot Drawing System.
    
    Coordinates image processing, coordinate transformation, robot communication,
    and visualization to provide a complete image-to-robot drawing solution.
    
    Attributes:
        robot: RobotController instance for communication
        processor: ImageProcessor for edge detection and path extraction
        transformer: CoordinateTransformer for scaling and smoothing
        visualizer: DrawingVisualizer for previews and plotting
        drawing_points: List of processed drawing paths
        image_data: Loaded image data for visualization
    """
    
    # Default robot workspace dimensions (in mm)
    DEFAULT_MAX_X = 290
    DEFAULT_MAX_Y = 210
    
    # Default connection settings
    DEFAULT_IP = "192.168.125.1"
    DEFAULT_PORT = 1025
    
    def __init__(self, ip=DEFAULT_IP, port=DEFAULT_PORT, 
                 max_x=DEFAULT_MAX_X, max_y=DEFAULT_MAX_Y, 
                 enable_smoothing=True, smoothing_type="bezier", enable_tsp=True, use_center_origin=True,
                 margin_x=10, margin_y=10):
        """
        Initialize the RobotDrawer with specified settings.
        
        Args:
            ip (str): Robot IP address
            port (int): Robot communication port
            max_x (int): Maximum X coordinate in mm
            max_y (int): Maximum Y coordinate in mm
            enable_smoothing (bool): Enable path smoothing
            smoothing_type (str): Type of smoothing to apply
            enable_tsp (bool): Enable TSP path optimization
            use_center_origin (bool): True for center at (0,0), False for corner at (0,0)
            enable_smoothing (bool): Whether to enable path smoothing
            smoothing_type (str): Type of smoothing algorithm ("bezier", "linear")
            enable_tsp (bool): Whether to enable TSP optimization
            margin_x (int): Horizontal margin in mm (padding from edges)
            margin_y (int): Vertical margin in mm (padding from edges)
        """
        # Initialize all subsystem components
        self.robot = RobotController(ip, port)
        self.processor = ImageProcessor(enable_tsp=enable_tsp)
        self.transformer = CoordinateTransformer(max_x, max_y, enable_smoothing, smoothing_type, use_center_origin, margin_x, margin_y)
        self.visualizer = DrawingVisualizer(max_x, max_y)
        
        # Initialize state variables
        self.drawing_points = []
        self.image_data = None
        self.max_x = max_x
        self.max_y = max_y
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.enable_tsp = enable_tsp
        self.use_center_origin = use_center_origin
        self.detection_method = "threshold"  # Default detection method
    
    def load_image(self, image_path, precision="high", enable_tsp=None, detection_method="threshold", logo_settings=None):
        """
        Load and process image to extract drawing points.
        
        Args:
            image_path: Path to the image file
            precision: Edge detection precision
            enable_tsp: Override TSP setting for this operation. If None, uses instance setting.
            detection_method: Edge detection method ("canny", "threshold", or "adaptive")
            logo_settings: Dictionary with logo settings {'enabled': bool, 'corner': str, 'size': int}
        """
        print(f"Drawing area: {self.max_x}mm x {self.max_y}mm")
        
        # Store the detection method for later use
        self.detection_method = detection_method
        
        # Process the image using optimized edge following (without logo)
        contour_data = self.processor.load_and_process_image(image_path, precision, enable_tsp, detection_method)
        if not contour_data:
            return False
        
        # Transform to robot coordinates
        self.drawing_points = self.transformer.contours_to_robot_coordinates(contour_data)
        
        # Add logo directly to robot coordinates if enabled
        if logo_settings and logo_settings.get('enabled', False):
            logo_size = logo_settings.get('size', 20)
            print(f"Adding logo to drawing area corner (size: {logo_size}mm)")
            logo_points = self.generate_logo_coordinates(logo_size)
            if logo_points:
                self.drawing_points.extend(logo_points)
                print(f"Logo added: {len(logo_points)} additional paths")
        
        # Store image data for visualization
        self.image_data = self.processor.get_edges_for_visualization(image_path, detection_method)
        
        print(f"Extracted {len(self.drawing_points)} drawing path(s)")
        total_points = sum(len(contour) for contour in self.drawing_points)
        print(f"Final result: {len(self.drawing_points)} contours with {total_points} total points")
        
        return True

    def connect(self):
        """Connect to the robot"""
        return self.robot.connect()
    
    def disconnect(self):
        """Disconnect from the robot"""
        self.robot.disconnect()
    
    def set_coordinate_system(self, use_center_origin):
        """Update coordinate system for robot and transformer"""
        self.use_center_origin = use_center_origin
        self.robot.set_coordinate_system(use_center_origin)
        # Update the transformer with new coordinate system and maintain margins
        self.transformer = CoordinateTransformer(
            self.max_x, self.max_y, 
            self.transformer.enable_smoothing, 
            self.transformer.smoothing_type, 
            use_center_origin,
            self.margin_x, self.margin_y
        )
    
    def draw(self, progress_callback=None):
        """
        Draw the loaded image on the robot with maximum speed optimizations.
        
        Uses ultra-fast mode with path optimization and large batch sizes.
        All settings are optimized for maximum performance.
        
        Args:
            progress_callback: Optional callback function(current_batch, total_batches, points_sent, total_points)
        """
        return self.robot.draw_paths(self.drawing_points, progress_callback=progress_callback)
    
    def preview_points(self, max_display=50):
        """Preview the extracted points in text format"""
        self.visualizer.preview_points_text(self.drawing_points, max_display)
    
    def plot_preview(self):
        """Show graphical preview of all drawing points"""
        self.visualizer.plot_preview(self.drawing_points)
    
    def show_processing_steps(self, image_path):
        """Show complete processing pipeline: original -> edges -> final points"""
        if not self.image_data:
            self.image_data = self.processor.get_edges_for_visualization(image_path, self.detection_method)
        
        self.visualizer.show_processing_steps(self.image_data, self.drawing_points)
    
    # Convenience methods for backward compatibility
    def send_move(self, x, y):
        """Send movement command to robot"""
        return self.robot.send_move(x, y)
    
    def send_pen_up(self):
        """Send pen up command"""
        return self.robot.send_pen_up()
    
    def send_pen_down(self):
        """Send pen down command"""
        return self.robot.send_pen_down()
    
    def send_stop(self):
        """Send stop command"""
        return self.robot.send_stop()
    
    def send_start(self):
        """Send START command with extended timeout for robot initialization"""
        return self.robot.send_start()

    def generate_logo_coordinates(self, size_mm=20):
        """
        Generate logo coordinates by processing logo_short.png and placing it at top-right corner.
        
        Args:
            size_mm: Logo size in millimeters
            
        Returns:
            List of logo drawing paths in robot coordinates
        """
        logo_path = "logo_short.png"
        
        if not os.path.exists(logo_path):
            print(f"Logo file {logo_path} not found, skipping logo addition")
            return []
        
        try:
            # Process logo image to get contours (with logo protection to prevent frame filtering)
            print(f"Processing logo image: {logo_path}")
            logo_contour_data = self.processor.extract_edge_following_path(logo_path, precision="high", detection_method="threshold", protect_logo=True)
            
            if not logo_contour_data or not logo_contour_data.get('contours'):
                print("No contours found in logo image")
                return []
            
            # Get logo contours
            logo_contours = logo_contour_data['contours']
            logo_image_shape = logo_contour_data['image_shape']
            
            # Calculate scaling to fit logo in specified size
            if len(logo_image_shape) >= 2:
                logo_pixel_height = logo_image_shape[0]  # height in pixels
                logo_pixel_width = logo_image_shape[1]   # width in pixels
            else:
                print(f"Invalid image shape: {logo_image_shape}")
                return []
            
            # Scale logo to fit in size_mm, maintaining aspect ratio
            scale_factor = size_mm / max(logo_pixel_width, logo_pixel_height)
            
            # Calculate logo position (top-right corner with margin)
            margin = 5  # 5mm margin from corner
            logo_x_offset = self.max_x - self.margin_x - size_mm - margin
            logo_y_offset = self.margin_y + margin  # Changed: now at top instead of bottom
            
            # Transform logo contours to robot coordinates
            logo_robot_contours = []
            
            for contour in logo_contours:
                robot_contour = []
                for point in contour:
                    # Handle numpy array points - extract x,y coordinates
                    if hasattr(point, 'shape'):
                        # It's a numpy array, get the coordinates
                        if len(point.shape) == 1 and point.shape[0] >= 2:
                            px = float(point[0])
                            py = float(point[1])
                        elif len(point.shape) == 2 and point.shape[1] >= 2:
                            px = float(point[0][0])
                            py = float(point[0][1])
                        else:
                            continue
                    else:
                        # Regular tuple/list
                        px = float(point[0])
                        py = float(point[1])
                        
                    # Scale and position the logo
                    x = px * scale_factor + logo_x_offset
                    y = py * scale_factor + logo_y_offset
                    
                    # Mirror logo horizontally (flip X coordinates)
                    # Calculate logo width to flip around its center
                    logo_width_mm = logo_pixel_width * scale_factor
                    x = logo_x_offset + logo_width_mm - (px * scale_factor)
                    
                    # Adjust for coordinate system (center vs corner origin)
                    if hasattr(self, 'use_center_origin') and self.use_center_origin:
                        # Convert to center-based coordinates
                        x = x - (self.max_x / 2)
                        y = y - (self.max_y / 2)
                    
                    robot_contour.append((x, y))
                
                if robot_contour:
                    logo_robot_contours.append(robot_contour)
            return logo_robot_contours
            
        except Exception as e:
            print(f"Error processing logo: {e}")
            return []

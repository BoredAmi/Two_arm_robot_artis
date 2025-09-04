"""
Image processing module for edge detection and contour extraction.

This module provides the ImageProcessor class which handles OpenCV operations
for converting images into robot-drawable paths. Features include:

- Edge detection using Canny algorithm
- Contour extraction and simplification
- Path deduplication and connection
- Optional TSP optimization for path ordering
- Multiple precision levels for different use cases

The module is designed for robotics applications where images need to be
converted into optimal drawing paths for robotic systems.

Version: 1.0
"""
import cv2
import numpy as np
import os


# Module version
__version__ = "1.0.0"


class ImageProcessor:
    """
    Image processing class for edge detection and contour extraction.
    
    Handles OpenCV operations and filtering for robot drawing applications.
    Supports TSP optimization for optimal path ordering when enabled.
    """
    
    # Default precision factors for contour simplification
    DEFAULT_PRECISION_FACTORS = {
        "highest": 0.0000002,
        "high": 0.0008,
        "medium": 0.002,
        "low": 0.005
    }
    
    # Edge detection parameters
    CANNY_LOW_THRESHOLD = 50
    CANNY_HIGH_THRESHOLD = 100
    GAUSSIAN_KERNEL_SIZE = (5, 5)
    GAUSSIAN_SIGMA = 3
    
    # Threshold detection parameters
    THRESHOLD_VALUE = 220
    
    # Adaptive threshold parameters
    ADAPTIVE_MAX_VALUE = 255
    ADAPTIVE_BLOCK_SIZE = 11  # Must be odd number (larger = less sensitive)
    ADAPTIVE_C = 2  # Constant subtracted from mean (higher = less sensitive)
    
    # Adaptive threshold precision adjustments
    ADAPTIVE_PRECISION_ADJUSTMENTS = {
        "highest": {"block_size": 7, "c": 1},  # Most sensitive
        #"highest": {"block_size": 15, "c": 3},   # More selective, fewer contours
        "high": {"block_size": 21, "c": 5},      # Balanced
        "medium": {"block_size": 31, "c": 8},    # Less sensitive
        "low": {"block_size": 41, "c": 12}       # Much less sensitive, cleanest
    }
    
    # Contour filtering parameters
    MIN_CONTOUR_LENGTH = 10
    DEFAULT_DISTANCE_THRESHOLD = 2.0
    DEFAULT_MAX_GAP = 3
    
    def __init__(self, enable_tsp=True):
        """
        Initialize ImageProcessor with optional TSP optimization control.
        
        Args:
            enable_tsp (bool): Whether to use TSP optimization for path ordering.
                              If False, contours will be processed in original order.
        """
        self.precision_factors = self.DEFAULT_PRECISION_FACTORS.copy()
        self.enable_tsp = enable_tsp
    
    def load_and_process_image(self, image_path, precision="high", enable_tsp=None, detection_method="threshold", protect_logo=False):
        """
        Load image and extract edge following paths for optimal robot drawing.
        
        Args:
            image_path: Path to the image file
            precision: Edge detection precision ("highest", "high", "medium", "low")
            enable_tsp: Override TSP setting for this operation. If None, uses instance setting.
            detection_method: Edge detection method ("canny", "threshold", or "adaptive")
            protect_logo: If True, disables border cropping and frame filtering (for logo processing)
        """
        # Temporarily override TSP setting if specified
        original_tsp_setting = self.enable_tsp
        if enable_tsp is not None:
            self.enable_tsp = enable_tsp
            
        try:
            result = self.extract_edge_following_path(image_path, precision, detection_method, protect_logo)
            return result
        finally:
            # Restore original TSP setting
            self.enable_tsp = original_tsp_setting
    
    def extract_edge_following_path(self, image_path, precision="high", detection_method="threshold", protect_logo=False):
        """
        Extract edge pixels as sequential paths for robot to follow edges directly.
        
        This method processes an image to extract contours suitable for robot drawing:
        1. Converts image to grayscale and applies Gaussian blur
        2. Detects edges using Canny algorithm, threshold method, adaptive threshold, or Canny+fill+threshold
        3. Thins edges to single-pixel width (for Canny)
        4. Finds and filters contours
        5. Applies precision-based simplification
        6. Optionally applies TSP optimization for path ordering
        
        Args:
            image_path (str): Path to the image file to process
            precision (str): Edge detection precision level
                           ("highest", "high", "medium", "low")
            detection_method (str): Edge detection method ("canny", "threshold", or "adaptive")
            protect_logo (bool): If True, disables border cropping and frame filtering (for logo processing)
        
        Returns:
            dict: Dictionary containing:
                - 'contours': List of simplified contour paths
                - 'image_shape': Shape of the processed edge image
                - 'simplification_factor': Factor used for contour simplification
            None: If image loading or processing fails
        """
        if not os.path.exists(image_path):
            print(f"Error: Image file {image_path} not found")
            return None
        
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                print(f"Error: Could not load image {image_path}")
                return None
            
            # Flip image 180 degrees (rotate around center)
            image = cv2.rotate(image, cv2.ROTATE_180)
            
            # SOLUTION: Add white border padding to prevent edge detection
            # This is better than cropping because it preserves all content
            if not protect_logo:
                border_padding = 20  # Pixels of white padding to add
                if border_padding > 0:
                    # Add white border padding around the entire image
                    image = cv2.copyMakeBorder(image, border_padding, border_padding, 
                                             border_padding, border_padding, 
                                             cv2.BORDER_CONSTANT, value=[255, 255, 255])
                    print(f"Added {border_padding}px white padding to prevent edge detection")
            else:
                print("Logo mode: Skipping border padding to preserve exact logo dimensions")
            
            print(f"Loaded and flipped image 180°: {image.shape} pixels")
            print(f"Precision mode: {precision}")
            print(f"Detection method: {detection_method}")
            
            # Convert to grayscale and apply edge detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise before edge detection
            gray = cv2.GaussianBlur(gray, self.GAUSSIAN_KERNEL_SIZE, self.GAUSSIAN_SIGMA)
            gray = cv2.medianBlur(gray, 5)
            # Apply detection method based on user choice
            if detection_method.lower() == "canny":
                # Apply Canny edge detection
                edges = cv2.Canny(gray, self.CANNY_LOW_THRESHOLD, self.CANNY_HIGH_THRESHOLD)
                
                # Thin the edges to single pixel width to avoid parallel contours
                edges = self._thin_edges(edges)
                
                # Apply morphological operations to connect nearby broken edges
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
            elif detection_method.lower() == "adaptive":
                # Apply adaptive threshold - great for varying lighting conditions
                # Adjust parameters based on precision level
                adaptive_params = self.ADAPTIVE_PRECISION_ADJUSTMENTS.get(precision, 
                                    self.ADAPTIVE_PRECISION_ADJUSTMENTS["high"])
                block_size = adaptive_params["block_size"]
                c_value = adaptive_params["c"]
                
                # Use Gaussian adaptive threshold instead of mean - much faster and smoother results
                edges = cv2.adaptiveThreshold(gray, self.ADAPTIVE_MAX_VALUE, 
                                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 
                                            block_size, c_value)
                print(f"Adaptive threshold (Gaussian): block_size={block_size}, C={c_value}")
            else:  # threshold method (default)
                # Apply binary threshold with OTSU for automatic threshold selection
                ret, edges = cv2.threshold(gray, self.THRESHOLD_VALUE, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Use OpenCV's contour detection
            # RETR_LIST gets all contours, CHAIN_APPROX_SIMPLE simplifies the contour
            contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                print("No edge contours found in image")
                return None
            
            print(f"Found {len(contours)} edge contours")
            
            # Filter contours to remove very small ones (noise)
            # With border padding, most edge contours should already be eliminated
            min_length = self.MIN_CONTOUR_LENGTH
            if detection_method.lower() == "adaptive":
                min_length = max(20, self.MIN_CONTOUR_LENGTH * 2)  # More aggressive filtering for adaptive
                
                # Also filter by area for adaptive threshold to remove tiny noise contours
                filtered_contours = []
                for c in contours:
                    if len(c) >= min_length and cv2.contourArea(c) >= 50:  # Minimum area threshold
                        # Optional: still check for border contours if not protecting logo (but should be rare now)
                        if protect_logo or not self._is_border_contour(c, edges.shape):
                            filtered_contours.append(c)
            else:
                filtered_contours = []
                for c in contours:
                    if len(c) >= min_length:
                        # Optional: still check for border contours if not protecting logo (but should be rare now) 
                        if protect_logo or not self._is_border_contour(c, edges.shape):
                            filtered_contours.append(c)
            
            print(f"Filtered to {len(filtered_contours)} contours with >= {min_length} points (border padding should prevent most edge issues)")
            
            # Apply precision-based simplification
            simplification_factor = self.precision_factors.get(precision, 0.0008)
            simplified_paths = []
            
            for contour in filtered_contours:
                # Simplify contour based on precision
                epsilon = simplification_factor * cv2.arcLength(contour, False)
                simplified = cv2.approxPolyDP(contour, epsilon, False)
                
                if len(simplified) >= 2:  # Keep paths with at least 2 points
                    simplified_paths.append(simplified)
            
            # Sort by contour length (longest first) to prioritize main edges
            simplified_paths.sort(key=lambda x: cv2.arcLength(x, False), reverse=True)
            
            print(f"Created {len(simplified_paths)} edge-following paths")
            total_points = sum(len(path) for path in simplified_paths)
            print(f"Total points after simplification: {total_points}")
            
            return {
                'contours': simplified_paths,
                'image_shape': edges.shape,
                'simplification_factor': simplification_factor
            }
            
        except Exception as e:
            print(f"Error extracting edge following path: {e}")
            return None
    
    def _is_border_contour(self, contour, image_shape):
        """
        Check if a contour touches the image borders (likely a frame contour).
        
        Args:
            contour: OpenCV contour
            image_shape: Shape of the image (height, width)
        
        Returns:
            True if contour touches borders and should be filtered out
        """
        height, width = image_shape
        border_margin = 5  # Pixels from edge to consider as "border"
        
        # Get contour points
        points = contour.reshape(-1, 2)
        
        # Check if any points are near the borders
        for x, y in points:
            # Check if point is near any border
            if (x <= border_margin or x >= width - border_margin or 
                y <= border_margin or y >= height - border_margin):
                
                # Additional check: if contour is very large relative to image, it's likely a frame
                contour_area = cv2.contourArea(contour)
                image_area = width * height
                
                # If contour covers more than 20% of image area and touches border, it's likely a frame
                if contour_area > (image_area * 0.2):
                    return True
                    
                # If contour has points spanning most of the image width/height, it's likely a frame
                x_coords = points[:, 0]
                y_coords = points[:, 1]
                x_span = np.max(x_coords) - np.min(x_coords)
                y_span = np.max(y_coords) - np.min(y_coords)
                
                if (x_span > width * 0.8 or y_span > height * 0.8):
                    return True
        
        return False

    def _thin_edges(self, edges):
        """
        Apply morphological thinning to get single-pixel-width edges.
        
        Uses iterative erosion and dilation operations to reduce thick edges
        to single-pixel width while preserving connectivity.
        
        Args:
            edges (np.ndarray): Binary edge image from Canny detection
        
        Returns:
            np.ndarray: Thinned edge image with single-pixel-width edges
        """
        # Use OpenCV's morphological thinning (skeletonization)
        kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        
        # Apply thinning using iterative erosion
        thinned = edges.copy()
        while True:
            eroded = cv2.erode(thinned, kernel)
            temp = cv2.dilate(eroded, kernel)
            temp = cv2.subtract(thinned, temp)
            thinned = cv2.bitwise_or(eroded, temp)
            
            if cv2.countNonZero(cv2.subtract(edges, thinned)) == 0:
                break
            edges = thinned.copy()
        
        return thinned

    
    def _calculate_tour_distance_closed(self, tour, dist_matrix):
        """
        Calculate total distance of a closed tour (returns to start).
        
        Args:
            tour: Tour as list of indices
            dist_matrix: Distance matrix
            
        Returns:
            Total tour distance including return to start
        """
        distance = 0
        n = len(tour)
        for i in range(n):
            j = (i + 1) % n  # This creates a closed loop
            distance += dist_matrix[tour[i]][tour[j]]
        return distance
    
    def get_edges_for_visualization(self, image_path, detection_method="threshold"):
        """
        Get edges for visualization purposes.
        
        Loads an image and applies edge detection for display
        in visualization components.
        
        Args:
            image_path (str): Path to the image file
            detection_method (str): Edge detection method ("canny", "threshold", or "adaptive")
        
        Returns:
            dict: Dictionary containing original image, edges, and grayscale version
            None: If image loading fails
        """
        if not os.path.exists(image_path):
            return None
        
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        # Flip image 180 degrees (rotate around center) for consistency
        image = cv2.rotate(image, cv2.ROTATE_180)
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply detection method based on user choice
        if detection_method.lower() == "canny":
            edges = cv2.Canny(gray, self.CANNY_LOW_THRESHOLD, self.CANNY_HIGH_THRESHOLD)
        elif detection_method.lower() == "adaptive":
            # Apply adaptive threshold with precision-based parameters
            adaptive_params = self.ADAPTIVE_PRECISION_ADJUSTMENTS.get("high", 
                                self.ADAPTIVE_PRECISION_ADJUSTMENTS["high"])
            block_size = adaptive_params["block_size"]
            c_value = adaptive_params["c"]
            
            # Use Gaussian adaptive threshold for smoother results
            edges = cv2.adaptiveThreshold(gray, self.ADAPTIVE_MAX_VALUE, 
                                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 
                                        block_size, c_value)
        else:  # threshold method (default)
            ret, edges = cv2.threshold(gray, self.THRESHOLD_VALUE, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return {
            'original': image,
            'edges': edges,
            'gray': gray
        }

    def add_logo_to_image(self, image, logo_path="logo_short.png", corner="bottom_right", size_factor=0.1):
        """
        Composite logo image into the corner of the main image.
        
        Args:
            image: Main image (numpy array)
            logo_path: Path to logo image file
            corner: Corner position ("bottom_right", "bottom_left", "top_right", "top_left")
            size_factor: Logo size as fraction of image width (0.05 to 0.2)
        
        Returns:
            Modified image with logo composited
        """
        if not os.path.exists(logo_path):
            print(f"Logo file {logo_path} not found, skipping logo addition")
            return image
        
        try:
            # Load logo
            logo = cv2.imread(logo_path)
            if logo is None:
                print(f"Could not load logo from {logo_path}")
                return image
            
            # Calculate logo size based on image dimensions
            img_height, img_width = image.shape[:2]
            logo_width = int(img_width * size_factor)
            logo_height = int(logo_width * logo.shape[0] / logo.shape[1])  # Maintain aspect ratio
            
            # Resize logo
            logo_resized = cv2.resize(logo, (logo_width, logo_height))
            
            # Calculate position based on corner
            margin = int(min(img_width, img_height) * 0.02)  # 2% margin
            
            if corner == "bottom_right":
                y_start = img_height - logo_height - margin
                x_start = img_width - logo_width - margin
            elif corner == "bottom_left":
                y_start = img_height - logo_height - margin
                x_start = margin
            elif corner == "top_right":
                y_start = margin
                x_start = img_width - logo_width - margin
            else:  # top_left
                y_start = margin
                x_start = margin
            
            # Ensure coordinates are within bounds
            y_start = max(0, min(y_start, img_height - logo_height))
            x_start = max(0, min(x_start, img_width - logo_width))
            y_end = y_start + logo_height
            x_end = x_start + logo_width
            
            # Create a copy of the image to modify
            result_image = image.copy()
            
            # Composite logo onto image
            # For white backgrounds in logo, use the original image
            # For black parts in logo, use black
            logo_gray = cv2.cvtColor(logo_resized, cv2.COLOR_BGR2GRAY)
            mask = logo_gray < 200  # Black parts of logo
            
            # Apply logo where mask is True (black parts)
            result_image[y_start:y_end, x_start:x_end][mask] = logo_resized[mask]
            
            print(f"Logo added at {corner} corner (size: {logo_width}x{logo_height})")
            return result_image
            
        except Exception as e:
            print(f"Error adding logo: {e}")
            return image

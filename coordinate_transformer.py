from shapely.geometry import Polygon, box

def polygons_overlap(contour1, contour2):
    """
    Returns True if two contours (as point lists) overlap (intersect) using shapely polygons.
    Handles open contours by buffering them slightly.
    """
    if len(contour1) < 3:
        poly1 = Polygon(contour1).buffer(1.0)
    else:
        poly1 = Polygon(contour1)
    if len(contour2) < 3:
        poly2 = Polygon(contour2).buffer(1.0)
    else:
        poly2 = Polygon(contour2)
    return poly1.intersects(poly2)

def contour_overlaps_forbidden(contour, forbidden_poly):
    """
    Returns True if the contour (as point list) overlaps the forbidden area polygon.
    """
    if len(contour) < 3:
        poly = Polygon(contour).buffer(1.0)
    else:
        poly = Polygon(contour)
    return poly.intersects(forbidden_poly)
def get_contour_bounds(contour, buffer_x=0, buffer_y=0):
    xs = [p[0] for p in contour]
    ys = [p[1] for p in contour]
    min_x, max_x = min(xs) - buffer_x, max(xs) + buffer_x
    min_y, max_y = min(ys) - buffer_y, max(ys) + buffer_y
    return min_x, max_x, min_y, max_y

def contours_overlap(bounds1, bounds2):
    min_x1, max_x1, min_y1, max_y1 = bounds1
    min_x2, max_x2, min_y2, max_y2 = bounds2
    overlap_x = max_x1 >= min_x2 and max_x2 >= min_x1
    overlap_y = max_y1 >= min_y2 and max_y2 >= min_y1
    return overlap_x and overlap_y

def master_slave_assign_contours(contours, master, buffer_radius=40, buffer_x=10, buffer_y=70):
    """
    Assigns contours to master and slave arms for dual-arm drawing with buffer zones.
    Returns (master_contour, slave_contour, remaining_contours).
    """
    if not contours:
        return None, None, [], []
    # Prioritize contours by X position for each arm
    def contour_center_x(contour):
        xs = [p[0] for p in contour]
        return sum(xs) / len(xs) if xs else 0
    # Build sorted order depending on master preference
    if master == "right":
        # Right arm: pick contour with highest center X (rightmost)
        sorted_contours = sorted(contours, key=contour_center_x)
    else:
        # Left arm: pick contour with lowest center X (leftmost)
        sorted_contours = sorted(contours, key=contour_center_x, reverse=True)

    # Helper: detect if a contour intersects the left-arm unreachable rectangle
    # Left arm cannot reach coordinates x < 130 mm and y < 40 mm (rectangle from origin)
    def _contour_in_left_forbidden(c):
        try:
            for p in c:
                x, y = p[0], p[1]
                if x < 130 and y < 40:
                    return True
        except Exception:
            pass
        return False

    # Select master contour while avoiding assigning left-arm to contours inside its unreachable rectangle
    master_contour = None
    if master == 'left':
        for c in sorted_contours:
            if not _contour_in_left_forbidden(c):
                master_contour = c
                break
        if master_contour is None:
            # If no contour is reachable by the left arm, swap roles and pick a right master
            # This prevents assigning an unreachable contour to the left arm even when left was requested.
            master = 'right'
            # Recompute sorted order for right master (rightmost)
            sorted_contours = sorted(contours, key=contour_center_x)
            master_contour = sorted_contours[0]
    else:
        master_contour = sorted_contours[0]
    from shapely.geometry import Polygon
    import numpy as np
    # Use the caller-specified buffer_radius around the contour
    # (default is 40 mm)
    master_poly = Polygon(master_contour)
    forbidden_poly = master_poly.buffer(buffer_radius)
    # Add a 'tail' in the forbidden direction, width matches buffer (60mm)
    xs = [p[0] for p in master_contour]
    ys = [p[1] for p in master_contour]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    SHEET_LIMIT = 1e4  # Large value, should be bigger than any real sheet
    if master == "right":
        # Tail to the left, width matches buffer, goes to far left
        tail_poly = Polygon([
            (-SHEET_LIMIT, min_y - buffer_radius),
            (min_x, min_y - buffer_radius),
            (min_x, max_y + buffer_radius),
            (-SHEET_LIMIT, max_y + buffer_radius)
        ])
    else:
        # Tail to the right, width matches buffer, goes to far right
        tail_poly = Polygon([
            (max_x, min_y - buffer_radius),
            (SHEET_LIMIT, min_y - buffer_radius),
            (SHEET_LIMIT, max_y + buffer_radius),
            (max_x, max_y + buffer_radius)
        ])
    forbidden_poly = forbidden_poly.union(tail_poly)
    # Find the first slave contour that is completely outside forbidden area (no intersection at all)
    from shapely.geometry import Polygon
    slave_contour = None
    # Determine which side the slave would be (opposite of master)
    slave_side = 'left' if master == 'right' else 'right'
    for c in contours:
        # Skip any contours already assigned
        if c in [master_contour]:
            continue
        # If slave is left, avoid assigning contours inside the left unreachable rectangle
        if slave_side == 'left' and _contour_in_left_forbidden(c):
            continue
        # Convert to polygon (buffer if needed)
        if len(c) < 3:
            slave_poly = Polygon(c).buffer(1.0)
        else:
            slave_poly = Polygon(c)
        # Only assign if there is NO intersection at all
        if not forbidden_poly.intersects(slave_poly):
            slave_contour = c
            break
    # Remove assigned contours from list
    assigned = [master_contour]
    if slave_contour:
        assigned.append(slave_contour)
    # All other contours remain for next steps
    remaining = [c for c in contours if c not in assigned]
    # Find unassigned contours that are completely outside forbidden area (free for next step)
    unassigned = []
    for c in remaining:
        if not contour_overlaps_forbidden(c, forbidden_poly):
            unassigned.append(c)
    # Ensure slave is only assigned if it does NOT overlap forbidden area
    # (already enforced above, but this is explicit)
    return master_contour, slave_contour, remaining, unassigned, forbidden_poly
"""
Coordinate transformation module for Robot Drawing System.

This module handles the conversion from image pixel coordinates to robot
workspace coordinates, including scaling, smoothing, and adaptive simplification.

The coordinate system has (0,0) positioned at the center of the drawing area,
with coordinates ranging from -max/2 to +max/2 in both X and Y directions.

Key Features:
- Centered coordinate system for intuitive positioning
- Automatic scaling to fit robot workspace
- Multiple smoothing algorithms (Bézier curves, Catmull-Rom splines)
- Adaptive simplification to reduce point density
- Line length limiting for optimal robot movement
- Path optimization and smoothing

The CoordinateTransformer ensures that image paths are properly scaled and
optimized for the physical robot workspace while maintaining drawing quality.

Version: 1.0
"""
import cv2
import numpy as np


class CoordinateTransformer:
    def _filter_min_distance(self, points, min_distance=None):
        """
        Remove points that are closer than min_distance to the previous point.
        Args:
            points (list): List of (x, y) tuples
            min_distance (float): Minimum allowed distance between points (mm)
        Returns:
            list: Filtered list of points
        """
        if not points:
            return points
        if min_distance is None:
            min_distance = self.MIN_DISTANCE_THRESHOLD
        filtered = [points[0]]
        for pt in points[1:]:
            last = filtered[-1]
            dist = ((pt[0] - last[0]) ** 2 + (pt[1] - last[1]) ** 2) ** 0.5
            if dist >= min_distance:
                filtered.append(pt)
        return filtered
    """
    Transforms image coordinates to robot workspace coordinates.
    
    Handles scaling, smoothing, and optimization of drawing paths to ensure
    they fit within the robot's physical workspace while maintaining quality.
    
    The coordinate system has (0,0) at the center of the drawing area:
    - X coordinates range from -max_x/2 to +max_x/2
    - Y coordinates range from -max_y/2 to +max_y/2
    
    Attributes:
        max_x (int): Maximum X coordinate extent from center (±max_x/2 range)
        max_y (int): Maximum Y coordinate extent from center (±max_y/2 range)
        enable_smoothing (bool): Whether to apply path smoothing
        smoothing_type (str): Type of smoothing algorithm to use
    """
    
    # Default workspace dimensions (mm)
    DEFAULT_MAX_X = 290
    DEFAULT_MAX_Y = 210
    
    # Smoothing algorithm options
    SMOOTHING_TYPES = ["bezier", "catmull_rom", "linear"]
    
    # Simplification parameters
    MIN_DISTANCE_THRESHOLD = 1.0  # Minimum distance between points (mm)
    MAX_LINE_LENGTH = 20.0        # Maximum line segment length (mm)
    
    def __init__(self, max_x=DEFAULT_MAX_X, max_y=DEFAULT_MAX_Y, 
                 enable_smoothing=True, smoothing_type="bezier", use_center_origin=True,
                 margin_x=10, margin_y=10):
        """
        Initialize the coordinate transformer.
        
        Sets up a coordinate system with (0,0) at center or corner based on use_center_origin.
        
        Args:
            max_x (int): Total X extent of workspace
            max_y (int): Total Y extent of workspace
            enable_smoothing (bool): Enable path smoothing algorithms
            smoothing_type (str): Smoothing algorithm type
            use_center_origin (bool): True for center at (0,0), False for corner at (0,0)
            enable_smoothing (bool): Whether to enable path smoothing
            smoothing_type (str): Smoothing algorithm ("bezier", "catmull_rom", "linear")
            margin_x (int): Horizontal margin in mm (padding from edges)
            margin_y (int): Vertical margin in mm (padding from edges)
        """
        self.max_x = max_x
        self.max_y = max_y
        self.margin_x = margin_x
        self.margin_y = margin_y
        self.enable_smoothing = enable_smoothing
        self.use_center_origin = use_center_origin
        
        # Calculate effective drawing area after margins
        self.effective_x = max_x - (2 * margin_x)
        self.effective_y = max_y - (2 * margin_y)
        
        if self.effective_x <= 0 or self.effective_y <= 0:
            raise ValueError(f"Margins too large for workspace. Effective area: {self.effective_x}x{self.effective_y}")
        
        if smoothing_type not in self.SMOOTHING_TYPES:
            raise ValueError(f"Invalid smoothing type. Must be one of: {self.SMOOTHING_TYPES}")
        self.smoothing_type = smoothing_type
    
    def contours_to_robot_coordinates(self, contour_data):
        """
        Convert OpenCV contours to robot coordinate points.
        
        Transforms image pixel coordinates to robot workspace coordinates,
        applying scaling, smoothing, and optimization as configured.
        
        Args:
            contour_data (dict): Dictionary containing:
                - 'contours': List of OpenCV contours
                - 'image_shape': Shape of the source image
                - 'simplification_factor': Factor used for contour simplification
        
        Returns:
            list: List of coordinate paths suitable for robot drawing
        """
        contours = contour_data['contours']
        image_shape = contour_data['image_shape']
        simplification_factor = contour_data['simplification_factor']
        
        points = []
        height, width = image_shape[:2]
        
        # Calculate scale factors to fit within effective drawing area (after margins)
        scale_x = self.effective_x / width
        scale_y = self.effective_y / height
        
        # Use the smaller scale to maintain aspect ratio
        scale = min(scale_x, scale_y)
        
        # Calculate offsets to center the scaled image within the effective drawing area
        scaled_width = width * scale
        scaled_height = height * scale
        effective_offset_x = (self.effective_x - scaled_width) / 2
        effective_offset_y = (self.effective_y - scaled_height) / 2
        
        # Add margins to get final offset in workspace coordinates
        final_offset_x = effective_offset_x + self.margin_x
        final_offset_y = effective_offset_y + self.margin_y
        
        # Calculate adaptive simplification based on image size and scale
        image_pixels = width * height
        
        # Base simplification on image resolution and final scale
        resolution_thresholds = [(1000000, 3.0), (500000, 2.0), (100000, 1.5)]
        resolution_factor = 1.0
        for threshold, factor in resolution_thresholds:
            if image_pixels > threshold:
                resolution_factor = factor
                break
        
        # Scale factor affects how much detail we can preserve
        scale_factor = min(2.0, max(0.5, scale * 1000))  # Normalize scale to reasonable range
        
        print(f"Image: {width}x{height} ({image_pixels/1000:.0f}K pixels)")
        print(f"Scale factor: {scale:.4f} (resolution_factor: {resolution_factor:.1f}, scale_factor: {scale_factor:.2f})")
        
        total_points = 0
        for contour in contours:

            # Skip very small contours
            if len(contour) < 5:
                continue
            
            # Calculate adaptive epsilon based on contour size and image properties
            perimeter = cv2.arcLength(contour, True)
            
            # Adaptive simplification
            base_epsilon = simplification_factor * perimeter
            adaptive_epsilon = base_epsilon * resolution_factor / scale_factor
            
            # Ensure minimum and maximum epsilon values
            min_epsilon = 0.5  # Minimum simplification in pixels
            max_epsilon = perimeter * 0.1  # Max 10% of perimeter
            adaptive_epsilon = max(min_epsilon, min(max_epsilon, adaptive_epsilon))
            
            simplified = cv2.approxPolyDP(contour, adaptive_epsilon, True)
            
            # Ensure we don't over-simplify small contours
            if len(simplified) < 8 and len(contour) > 15:
                simplified = cv2.approxPolyDP(contour, adaptive_epsilon * 0.5, True)
            
            # If still too simplified, use original contour points but sample them
            if len(simplified) < 6:
                sample_rate = max(1, len(contour) // 20)  # Sample every N points, max 20 points
                simplified = contour[::sample_rate]
                
                # Always include first and last points
                if len(simplified) > 2:
                    simplified[0] = contour[0]
                    simplified[-1] = contour[-1]
            
            contour_points = []
            for point in simplified:
                x, y = point[0]
                
                # Transform to robot coordinates based on coordinate system
                if self.use_center_origin:
                    # Center-based coordinates: (0,0) at center
                    robot_x = (x * scale) + final_offset_x - (self.max_x / 2)
                    robot_y = ((height - y) * scale) + final_offset_y - (self.max_y / 2)  # Flip Y axis
                    
                    # Ensure coordinates are within bounds (centered coordinate system)
                    robot_x = max(-self.max_x/2, min(self.max_x/2, robot_x))
                    robot_y = max(-self.max_y/2, min(self.max_y/2, robot_y))
                else:
                    # Corner-based coordinates: (0,0) at corner
                    robot_x = (x * scale) + final_offset_x
                    robot_y = ((height - y) * scale) + final_offset_y  # Flip Y axis
                    
                    # Ensure coordinates are within bounds (corner coordinate system)
                    robot_x = max(0, min(self.max_x, robot_x))
                    robot_y = max(0, min(self.max_y, robot_y))
                
                contour_points.append((robot_x, robot_y))
            
            # Apply edge smoothing if enabled and contour has enough points
            if self.enable_smoothing and len(contour_points) >= 4:
                if self.smoothing_type == "bezier":
                    contour_points = self._smooth_path_bezier(contour_points)
                elif self.smoothing_type == "catmull_rom":
                    contour_points = self._smooth_path_catmull_rom(contour_points)

            # Filter out points that are too close together
            contour_points = self._filter_min_distance(contour_points)

            if contour_points:
                points.append(contour_points)
                total_points += len(contour_points)
        
        print(f"Image scaled by factor {scale:.3f} to fit {self.effective_x}x{self.effective_y} effective area")
        coord_system = "center" if self.use_center_origin else "corner"
        print(f"Coordinate system: (0,0) at {coord_system}, workspace: {self.max_x}x{self.max_y}mm")
        print(f"Margins applied: {self.margin_x}mm horizontal, {self.margin_y}mm vertical")
        print(f"Drawing will be centered with {effective_offset_x:.1f}mm internal margin on X and {effective_offset_y:.1f}mm internal margin on Y")
        smoothing_status = f" with {self.smoothing_type} smoothing" if self.enable_smoothing else ""
        print(f"Total points extracted: {total_points} (adaptive simplification{smoothing_status})")
        
        # Apply path optimization for minimum travel distance (always enabled)
        print("Applying path optimization to minimize travel distance...")
        points = self._optimize_contour_drawing_order(points)
        
        return points
    
    def _optimize_path(self, contours):
        """Optimize each contour as a TSP and then optimize contour order"""
        if len(contours) <= 1:
            return contours
        
        # Step 1: Merge close contours to reduce pen lifts
        merged_contours = self._merge_close_contours(contours)
        print(f"Merged {len(contours)} contours into {len(merged_contours)} groups")
        
        # Step 2: Optimize each contour individually using TSP
        optimized_contours = []
        for contour in merged_contours:
            if len(contour) <= 3:
                # Too few points for meaningful optimization
                optimized_contours.append(contour)
            else:
                optimized_contour = self._solve_tsp_for_contour(contour)
                optimized_contours.append(optimized_contour)
        
        # Step 3: Optimize the order of contours (inter-contour TSP)
        contour_order = self._optimize_contour_order(optimized_contours)
        
        return contour_order
    
    def _merge_close_contours(self, contours):
        """Merge contours that are close together to reduce pen lifts"""
        if len(contours) <= 1:
            return contours
        
        # Calculate merge threshold based on drawing area
        merge_threshold = min(self.max_x, self.max_y) * 0.05  # 5% of smaller dimension
        
        merged = []
        used = set()
        
        for i, contour_a in enumerate(contours):
            if i in used:
                continue
                
            # Start a new merged group with this contour
            current_group = list(contour_a)
            used.add(i)
            
            # Look for nearby contours to merge
            found_merge = True
            while found_merge:
                found_merge = False
                
                for j, contour_b in enumerate(contours):
                    if j in used:
                        continue
                    
                    # Check if contour_b is close enough to current_group
                    min_distance = self._find_min_distance_between_contours(current_group, contour_b)
                    
                    if min_distance <= merge_threshold:
                        # Merge contour_b into current_group
                        connection_points = self._find_best_connection(current_group, contour_b)
                        current_group = self._connect_contours(current_group, contour_b, connection_points)
                        used.add(j)
                        found_merge = True
                        break
            
            merged.append(current_group)
        
        return merged
    
    def _find_min_distance_between_contours(self, contour_a, contour_b):
        """Find minimum distance between any two points in different contours"""
        min_dist = float('inf')
        
        # Check a sample of points to avoid O(n²) for large contours
        sample_a = self._sample_contour_points(contour_a, max_points=10)
        sample_b = self._sample_contour_points(contour_b, max_points=10)
        
        for point_a in sample_a:
            for point_b in sample_b:
                dist = self._distance(point_a, point_b)
                if dist < min_dist:
                    min_dist = dist
        
        return min_dist
    
    def _sample_contour_points(self, contour, max_points=10):
        """Sample points from contour for distance calculations"""
        if len(contour) <= max_points:
            return contour
        
        # Always include endpoints and sample evenly spaced points
        indices = [0, len(contour) - 1]  # Start and end
        
        # Add evenly spaced points
        step = len(contour) // (max_points - 2) if max_points > 2 else 1
        for i in range(step, len(contour) - 1, step):
            indices.append(i)
            if len(indices) >= max_points:
                break
        
        return [contour[i] for i in sorted(set(indices))]
    
    def _find_best_connection(self, contour_a, contour_b):
        """Find the best points to connect two contours"""
        min_dist = float('inf')
        best_connection = None
        
        # Check endpoints of both contours
        endpoints_a = [0, len(contour_a) - 1]
        endpoints_b = [0, len(contour_b) - 1]
        
        for idx_a in endpoints_a:
            for idx_b in endpoints_b:
                dist = self._distance(contour_a[idx_a], contour_b[idx_b])
                if dist < min_dist:
                    min_dist = dist
                    best_connection = (idx_a, idx_b)
        
        return best_connection
    
    def _connect_contours(self, contour_a, contour_b, connection_points):
        """Connect two contours at specified points"""
        idx_a, idx_b = connection_points
        
        # Determine the best way to connect the contours
        # Case 1: Connect end of A to start of B
        if idx_a == len(contour_a) - 1 and idx_b == 0:
            return contour_a + contour_b
        
        # Case 2: Connect end of A to end of B (reverse B)
        elif idx_a == len(contour_a) - 1 and idx_b == len(contour_b) - 1:
            return contour_a + contour_b[::-1]
        
        # Case 3: Connect start of A to start of B (reverse A)
        elif idx_a == 0 and idx_b == 0:
            return contour_a[::-1] + contour_b
        
        # Case 4: Connect start of A to end of B
        elif idx_a == 0 and idx_b == len(contour_b) - 1:
            return contour_b + contour_a
        
        # Default: just concatenate (shouldn't happen with endpoint logic)
        return contour_a + contour_b

    def _distance(self, p1, p2):
        """Fast Euclidean distance calculation"""
        return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5
    
    def _solve_tsp_for_contour(self, contour):
        """Solve TSP for a single contour using nearest neighbor + 2-opt"""
        n = len(contour)
        if n <= 3:
            return contour
        
        # Check if contour is closed (endpoints are close) or open (like letters F, ), etc.)
        start_point = contour[0]
        end_point = contour[-1]
        endpoint_distance = self._distance(start_point, end_point)
        
        # Calculate average distance between consecutive points for comparison
        consecutive_distances = []
        for i in range(len(contour) - 1):
            consecutive_distances.append(self._distance(contour[i], contour[i + 1]))
        avg_consecutive_dist = sum(consecutive_distances) / len(consecutive_distances)
        
        # If endpoints are far apart relative to normal point spacing, treat as open contour
        is_closed = endpoint_distance < (avg_consecutive_dist * 2.0)
        
        if not is_closed:
            # For open contours (like letters), only optimize the path but don't close the loop
            return self._optimize_open_contour(contour)
        
        # For closed contours, use full TSP
        # Create distance matrix
        dist_matrix = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    dist_matrix[i][j] = self._distance(contour[i], contour[j])
        
        # Nearest neighbor heuristic for initial solution
        tour = self._nearest_neighbor_tsp(dist_matrix, n)
        
        # Improve with 2-opt if contour is large enough
        if n > 4:
            tour = self._two_opt_improve(tour, dist_matrix)
        
        # Convert tour indices back to coordinates
        optimized_contour = [contour[i] for i in tour]
        
        return optimized_contour
    
    def _nearest_neighbor_tsp(self, dist_matrix, n):
        """Nearest neighbor heuristic for TSP"""
        unvisited = set(range(1, n))
        tour = [0]  # Start from first point
        current = 0
        
        while unvisited:
            nearest = min(unvisited, key=lambda x: dist_matrix[current][x])
            tour.append(nearest)
            unvisited.remove(nearest)
            current = nearest
        
        return tour
    
    def _optimize_open_contour(self, contour):
        """Optimize open contour without closing the loop (for letters like F, ), etc.)"""
        n = len(contour)
        if n <= 4:
            return contour  # Too small to meaningfully optimize
        
        # For open contours, we'll use a different approach:
        # Find the best path that minimizes backtracking while preserving the open nature
        
        # Simple approach: check if reversing improves the path
        # Calculate total path length in original order
        original_length = 0
        for i in range(len(contour) - 1):
            original_length += self._distance(contour[i], contour[i + 1])
        
        # Calculate total path length if reversed
        reversed_contour = contour[::-1]
        reversed_length = 0
        for i in range(len(reversed_contour) - 1):
            reversed_length += self._distance(reversed_contour[i], reversed_contour[i + 1])
        
        # Return the version with shorter total path length
        if reversed_length < original_length:
            return reversed_contour
        else:
            return contour
    
    def _two_opt_improve(self, tour, dist_matrix):
        """Improve tour using 2-opt local search"""
        n = len(tour)
        improved = True
        best_tour = tour[:]
        
        # Calculate initial distance
        best_distance = self._calculate_tour_distance(best_tour, dist_matrix)
        
        iteration = 0
        max_iterations = min(100, n * 2)  # Limit iterations for performance
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            for i in range(n - 1):
                for j in range(i + 2, n):
                    # Skip if edge case
                    if i == 0 and j == n - 1:
                        continue
                    
                    # Create new tour by reversing segment between i and j
                    new_tour = best_tour[:i+1] + best_tour[i+1:j+1][::-1] + best_tour[j+1:]
                    new_distance = self._calculate_tour_distance(new_tour, dist_matrix)
                    
                    if new_distance < best_distance:
                        best_tour = new_tour
                        best_distance = new_distance
                        improved = True
        
        return best_tour
    
    def _calculate_tour_distance(self, tour, dist_matrix):
        """Calculate total distance of a tour (closed loop)"""
        distance = 0
        n = len(tour)
        for i in range(n):
            j = (i + 1) % n  # This creates a closed loop
            distance += dist_matrix[tour[i]][tour[j]]
        return distance
    
    def _optimize_contour_order(self, contours):
        """Optimize the order of drawing contours using nearest neighbor"""
        if len(contours) <= 1:
            return contours
        
        optimized = []
        remaining = list(range(len(contours)))
        current_pos = (0, 0)  # Starting position
        total_travel = 0
        
        while remaining:
            min_dist = float('inf')
            best_idx = 0
            best_start_reversed = False
            best_start_point = None
            
            # Find closest contour and best starting point
            for i, contour_idx in enumerate(remaining):
                contour = contours[contour_idx]
                
                # Check all points in contour as potential starting points
                for point_idx, point in enumerate(contour):
                    dist = self._distance(current_pos, point)
                    if dist < min_dist:
                        min_dist = dist
                        best_idx = i
                        best_start_point = point_idx
                        best_start_reversed = False
                
                # Also check reversed contour
                for point_idx, point in enumerate(reversed(contour)):
                    dist = self._distance(current_pos, point)
                    if dist < min_dist:
                        min_dist = dist
                        best_idx = i
                        best_start_point = len(contour) - 1 - point_idx
                        best_start_reversed = True
            
            # Get the best contour and reorder it to start from best point
            contour_idx = remaining.pop(best_idx)
            selected_contour = contours[contour_idx]
            
            # Reorder contour to start from best point
            if best_start_point is not None and best_start_point != 0:
                selected_contour = (selected_contour[best_start_point:] + 
                                  selected_contour[:best_start_point])
            
            # Reverse if needed
            if best_start_reversed:
                selected_contour = selected_contour[::-1]
            
            optimized.append(selected_contour)
            current_pos = selected_contour[-1]
            total_travel += min_dist
        
        print(f"Path optimized: {total_travel:.1f}mm total pen-up travel")
        print(f"Applied TSP optimization to {len(contours)} contours")
        return optimized
    
    def _optimize_contour_drawing_order(self, contours):
        """Optimize contour drawing order to minimize travel distance between contours"""
        if len(contours) <= 1:
            return contours
        
        print("Optimizing contour drawing order...")
        
        # Calculate distances between all contour start/end points
        def distance(p1, p2):
            return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5
        
        # Use greedy nearest-neighbor algorithm for path optimization
        optimized = []
        remaining = list(enumerate(contours))  # (index, contour) pairs
        
        # Start with the first contour (or could optimize starting point too)
        current_idx, current_contour = remaining.pop(0)
        optimized.append(current_contour)
        current_end = current_contour[-1] if current_contour else (0, 0)
        
        total_saved_distance = 0
        
        # Greedily select nearest contours
        while remaining:
            best_distance = float('inf')
            best_idx = 0
            best_contour = None
            best_reversed = False
            
            # Find closest contour (only checking start points to preserve drawing direction)
            for i, (orig_idx, contour) in enumerate(remaining):
                if not contour:
                    continue
                
                # Distance to start of contour only - don't reverse contours
                dist_to_start = distance(current_end, contour[0])
                
                # Choose the best option without reversing
                if dist_to_start < best_distance:
                    best_distance = dist_to_start
                    best_idx = i
                    best_contour = contour
                    best_reversed = False
            
            # Add the best contour to our optimized path
            if best_contour:
                optimized.append(best_contour)
                current_end = best_contour[-1]
                remaining.pop(best_idx)
                
                total_saved_distance += best_distance
        
        print(f"Path optimization complete - estimated total travel: {total_saved_distance:.1f}mm")
        return optimized
        
    def _smooth_path_bezier(self, path, smoothness=0.3):
        """
        Smooth path using quadratic Bezier curves between path segments.
        
        Args:
            path: List of (x, y) coordinate tuples
            smoothness: Factor controlling curve intensity (0.0 = no smoothing, 1.0 = maximum)
        
        Returns:
            Smoothed path with interpolated points
        """
        if len(path) < 3:
            return path
        
        smoothed = [path[0]]  # Always keep first point
        
        for i in range(1, len(path) - 1):
            prev_point = path[i - 1]
            current_point = path[i]
            next_point = path[i + 1]
            
            # Calculate vectors from current point to neighbors
            v1 = (current_point[0] - prev_point[0], current_point[1] - prev_point[1])
            v2 = (next_point[0] - current_point[0], next_point[1] - current_point[1])
            
            # Calculate distances
            d1 = (v1[0]**2 + v1[1]**2)**0.5
            d2 = (v2[0]**2 + v2[1]**2)**0.5
            
            if d1 < 0.1 or d2 < 0.1:  # Skip if points are too close
                smoothed.append(current_point)
                continue
            
            # Calculate control points for Bezier curve
            factor = min(d1, d2) * smoothness * 0.5
            
            # Control point before current point
            cp1_x = current_point[0] - (v1[0] / d1) * factor
            cp1_y = current_point[1] - (v1[1] / d1) * factor
            
            # Control point after current point  
            cp2_x = current_point[0] + (v2[0] / d2) * factor
            cp2_y = current_point[1] + (v2[1] / d2) * factor
            
            # Generate Bezier curve points
            bezier_points = self._generate_bezier_curve(
                (cp1_x, cp1_y), current_point, (cp2_x, cp2_y), num_points=3
            )
            
            # Add the bezier points (skip first point to avoid duplication)
            smoothed.extend(bezier_points[1:])
        
        smoothed.append(path[-1])  # Always keep last point
        return smoothed
    
    def _generate_bezier_curve(self, p0, p1, p2, num_points=5):
        """
        Generate points along a quadratic Bezier curve.
        
        Args:
            p0, p1, p2: Control points (x, y) tuples
            num_points: Number of points to generate
        
        Returns:
            List of (x, y) points along the curve
        """
        points = []
        
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            
            # Quadratic Bezier formula: B(t) = (1-t)²P0 + 2(1-t)tP1 + t²P2
            x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
            y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
            
            points.append((x, y))
        
        return points
    
    def _smooth_path_catmull_rom(self, path, resolution=0.1):
        """
        Alternative smoothing using Catmull-Rom splines.
        Creates very natural curves but may deviate more from original path.
        
        Args:
            path: List of (x, y) coordinate tuples
            resolution: Step size for curve generation (smaller = smoother)
        
        Returns:
            Smoothed path with interpolated points
        """
        if len(path) < 4:
            return path
        
        smoothed = [path[0]]
        
        # Add phantom points at beginning and end
        extended_path = [path[0]] + path + [path[-1]]
        
        for i in range(1, len(extended_path) - 2):
            p0, p1, p2, p3 = extended_path[i-1:i+3]
            
            # Generate curve segment between p1 and p2
            t = 0.0
            while t <= 1.0:
                # Catmull-Rom spline formula
                x = 0.5 * (
                    2 * p1[0] +
                    (-p0[0] + p2[0]) * t +
                    (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t**2 +
                    (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t**3
                )
                
                y = 0.5 * (
                    2 * p1[1] +
                    (-p0[1] + p2[1]) * t +
                    (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t**2 +
                    (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t**3
                )
                
                smoothed.append((x, y))
                t += resolution
        
        smoothed.append(path[-1])
        return smoothed

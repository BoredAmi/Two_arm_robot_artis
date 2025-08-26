"""
Robot communication module for ABB robot control.

This module provides TCP/IP communication capabilities for controlling
ABB industrial robots. It handles connection management, command sending,
and response handling for robot drawing operations.

Key Features:
- TCP socket communication with configurable timeouts
- Command queuing and response validation
- Connection state management
- Error handling and retry mechanisms
- Support for ABB robot command protocol

The RobotController class abstracts the low-level communication details,
providing a clean interface for sending movement and control commands.

Version: 1.0
"""
import socket
import time


class RobotController:
    """
    TCP/IP communication controller for ABB robots.
    
    Manages connection state and provides methods for sending movement
    and control commands to the robot controller.
    
    Attributes:
        ip (str): Robot controller IP address
        port (int): TCP communication port
        socket: Active socket connection
    """
    
    # Default connection settings
    DEFAULT_IP = "192.168.125.1"
    DEFAULT_PORT = 1025
    DEFAULT_TIMEOUT = 5.0
    DEFAULT_PORT_L = 1026

    # Command response settings
    RESPONSE_TIMEOUT = 20.0
    START_COMMAND_TIMEOUT = 90.0  # Extended timeout for START command (robot initialization)
    MAX_RETRIES = 3
    
    def __init__(self, ip=DEFAULT_IP, port=DEFAULT_PORT):
        """
        Initialize robot controller.
        
        Args:
            ip (str): Robot controller IP address
            port (int): TCP communication port
        """
        self.ip = ip
        self.port = port
        self.socket = None
        self.socket2 = None  # For second port (1026)
        self.use_batch_mode = True  # Default to batch mode for speed
        self.use_center_origin = True  # Default to center-based coordinates (current system)
    
    def connect(self):
        """
        Establish TCP connections to the robot controller on both ports 1025 and 1026.
        
        Returns:
            bool: True if both connections are successful, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.DEFAULT_TIMEOUT)
            self.socket.connect((self.ip, self.port))
            print(f"Connected to ABB robot at {self.ip}:{self.port}")

            # Connect to second port (1026)
            self.socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket2.settimeout(self.DEFAULT_TIMEOUT)
            self.socket2.connect((self.ip, self.DEFAULT_PORT_L))
            print(f"Connected to ABB robot at {self.ip}:{self.DEFAULT_PORT_L}")

            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.socket = None
            if hasattr(self, 'socket2') and self.socket2:
                self.socket2.close()
            self.socket2 = None
            return False
    
    def send_move(self, x, y, wait_response=True, target='primary'):
        """Send movement command to robot with coordinate system awareness"""
        # When using corner coordinates, send them directly to robot
        # The robot will handle the coordinate system based on START vs START_CORNER
        cmd = f"MOVE,{x:.2f},{y:.2f}\n"
        return self._send_command(cmd, wait_response, target=target)
    
    def send_batch_moves(self, points, batch_size=3, max_batch_size=6, target='primary'):
        """
        Send multiple coordinates in batches with dynamic sizing optimization.
        
        Args:
            points (list): List of (x, y) coordinate tuples
            batch_size (int): Default number of points per batch
            max_batch_size (int): Maximum batch size to attempt (default=6)
        
        Returns:
            bool: True if all batches sent successfully, False otherwise
        """
        if not points:
            return True
            
        print(f"Sending {len(points)} points with dynamic batch sizing (base: {batch_size}, max: {max_batch_size})")
        
        # Optimize batch size based on coordinate precision
        optimal_batch_size = self._calculate_optimal_batch_size(points, batch_size, max_batch_size)
        
        # Process points in optimized batches
        for i in range(0, len(points), optimal_batch_size):
            batch = points[i:i + optimal_batch_size]
            
            # Format batch command - robot handles coordinate system based on START command
            coords = []
            for x, y in batch:
                coords.extend([f"{x:.1f}", f"{y:.1f}"])  # Send coordinates directly
            
            cmd = f"BATCH,{','.join(coords)}\n"
            
            # Check command length - RAPID strings are limited to 80 characters
            if len(cmd) > 78:  # 78 to leave small safety margin
                print(f"Warning: Batch command length ({len(cmd)}) exceeds 80-char limit, splitting batch")
                # Split oversized batch and retry with smaller chunks
                mid_point = len(batch) // 2
                if mid_point > 0:
                    if not self.send_batch_moves(batch[:mid_point], batch_size=mid_point, target=target):
                        return False
                    if not self.send_batch_moves(batch[mid_point:], batch_size=len(batch) - mid_point, target=target):
                        return False
                else:
                    # Single point fallback
                    for x, y in batch:
                        if not self.send_move(x, y, wait_response=True, target=target):
                            return False
            else:
                if not self._send_command(cmd, wait_response=True, target=target):
                    return False
                    
        return True
    
    def _calculate_optimal_batch_size(self, points, base_batch_size, max_batch_size):
        """Calculate optimal batch size based on coordinate characteristics"""
        if len(points) < base_batch_size:
            return len(points)
        
        # Sample first few points to estimate coordinate string length
        sample_points = points[:min(3, len(points))]
        avg_coord_length = sum(len(f"{x:.1f}") + len(f"{y:.1f}") for x, y in sample_points) / len(sample_points)
        
        # Estimate max coordinates that fit in 80 characters with safety margin
        # Format: "BATCH," (6 chars) + coordinates + commas
        available_chars = 80 - 6 - 3  # Reserve 6 chars for "BATCH," + 3 safety margin
        estimated_coords_per_point = avg_coord_length + 2  # +2 for commas
        max_points_by_length = int(available_chars / estimated_coords_per_point)
        
        # Choose the smaller of calculated max or requested max
        optimal_size = min(max_points_by_length, max_batch_size, len(points))
        optimal_size = max(optimal_size, 1)  # Ensure at least 1 point
        
        print(f"Optimal batch size calculated: {optimal_size} (length-limited: {max_points_by_length})")
        return optimal_size

    def _get_socket(self, target='primary'):
        """Return socket object(s) for target: 'primary', 'secondary', or 'both'.

        Returns a tuple (primary_socket, secondary_socket) where missing sockets are None.
        """
        primary = self.socket
        secondary = getattr(self, 'socket2', None)
        if target == 'primary':
            return (primary, None)
        if target == 'secondary':
            return (None, secondary)
        # both
        return (primary, secondary)
    
    def send_pen_up(self, target='primary'):
        """Send pen up command (lift drawing tool)"""
        return self._send_command("PEN_UP\n", target=target)
    
    def send_pen_down(self, target='primary'):
        """Send pen down command (lower drawing tool)"""
        return self._send_command("PEN_DOWN\n", target=target)

    def send_stop(self, target='primary'):
        """Send stop command"""
        return self._send_command("STOP\n", target=target)
    
    def set_batch_mode(self, enabled):
        """
        Enable or disable batch mode for drawing commands.
        
        Args:
            enabled (bool): True for batch commands, False for individual moves
        """
        self.use_batch_mode = enabled
        mode_text = "batch" if enabled else "individual"
        print(f"Drawing mode set to: {mode_text}")

    def set_coordinate_system(self, center_origin):
        """
        Set coordinate system origin.
        
        Args:
            center_origin (bool): True for center at (0,0), False for corner at (0,0)
        """
        self.use_center_origin = center_origin
        origin_text = "center" if center_origin else "corner"
        print(f"Coordinate system set to: {origin_text} origin")

    def start_without_camera(self):
        """
        Send command to start robot without camera initialization.
        Just basic robot ready state without finding sheet.
        
        Returns:
            bool: True if robot responds with OK, False otherwise
        """
        print("Starting robot without camera (manual positioning)...")
        return self._send_command("READY\n", wait_response=True, timeout=self.START_COMMAND_TIMEOUT)

    def send_start(self):
        """
        Send START command with coordinate system awareness.
        
        The robot may take up to 90 seconds to respond as it performs:
        - System initialization
        - Axis homing and calibration
        - Safety checks
        - Tool setup
        - Camera-based sheet detection (with coordinate system setup)
        
        Returns:
            bool: True if robot responds with OK, False otherwise
        """
        if self.use_center_origin:
            print("Sending START command (center coordinates) - robot may take up to 90 seconds to initialize...")
            return self._send_command("START\n", wait_response=True, timeout=self.START_COMMAND_TIMEOUT)
        else:
            print("Sending START_CORNER command (corner coordinates) - robot may take up to 90 seconds to initialize...")
            return self._send_command("START_CORNER\n", wait_response=True, timeout=self.START_COMMAND_TIMEOUT)
    
    def _send_command(self, cmd, wait_response=True, timeout=None, target='primary'):
        """
        Internal command sender with configurable timeout.
        
        Args:
            cmd (str): Command to send
            wait_response (bool): Whether to wait for robot response
            timeout (float): Custom timeout in seconds. If None, uses RESPONSE_TIMEOUT
        
        Returns:
            bool: True if command successful (and OK received if waiting), False otherwise
        """
        # Helper to optionally send to a socket
        def _safe_send(sock, data):
            if not sock:
                return False
            try:
                sock.sendall(data.encode())
                return True
            except Exception as e:
                print(f"Send failed on socket: {e}")
                return False

        primary_sock, secondary_sock = self._get_socket(target)

        try:
            print(f"Sending: {cmd.strip()} to {target}")

            # Send to primary if requested
            if primary_sock:
                primary_sock.sendall(cmd.encode())

            # Send to secondary if requested
            if secondary_sock:
                secondary_sock.sendall(cmd.encode())

            # Only wait for response from primary socket
            if wait_response and primary_sock:
                if timeout is not None:
                    original_timeout = primary_sock.gettimeout()
                    primary_sock.settimeout(timeout)
                    print(f"Using extended timeout: {timeout}s for command response")

                try:
                    response = primary_sock.recv(1024).decode().strip()
                    print(f"Robot response: {response}")
                    success = response == "OK"

                    if timeout is not None:
                        primary_sock.settimeout(original_timeout)

                    return success

                except socket.timeout:
                    print(f"Command timeout after {timeout or self.RESPONSE_TIMEOUT}s - no response from robot")
                    if timeout is not None:
                        primary_sock.settimeout(original_timeout)
                    return False

            return True

        except Exception as e:
            print(f"Command failed: {e}")
            return False
    
    def disconnect(self):
        """Close both connections"""
        if self.socket:
            self.socket.close()
            print("Disconnected from ABB robot (port 1025)")
        if hasattr(self, 'socket2') and self.socket2:
            self.socket2.close()
            print("Disconnected from ABB robot (port 1026)")
    
    def draw_paths(self, drawing_points, move_delay=0.02, use_batching=None, batch_size=8, progress_callback=None):
        """
        Draw the provided drawing paths on the robot.
        
        Args:
            drawing_points: List of contours, each containing (x, y) coordinate tuples
            move_delay: Delay between moves for individual mode
            use_batching: Override batch mode setting (None = use current setting)
            batch_size: Points per batch when using batch mode
            progress_callback: Function to call with progress updates (current, total, overall_current, overall_total)
        """
        if not drawing_points:
            print("No points to draw.")
            return False
        
        if not self.socket:
            print("Not connected to robot. Use connect() first.")
            return False
        
        # Use override or current setting
        actual_batching = use_batching if use_batching is not None else self.use_batch_mode
        mode_text = "batch" if actual_batching else "individual"
        print(f"Starting to draw using {mode_text} mode...")
        
        try:
            # Start with pen up
            self.send_pen_up()
            time.sleep(0.02)
            
            if actual_batching:
                return self._draw_with_ultra_fast_mode(drawing_points, batch_size, progress_callback)
            else:
                return self._draw_with_individual_moves(drawing_points, move_delay)
                
        except KeyboardInterrupt:
            print("\nDrawing interrupted by user")
            self.send_pen_up()
            self.send_stop()
            return False
        except Exception as e:
            print(f"Error during drawing: {e}")
            self.send_pen_up()
            self.send_stop()
            return False

    def _draw_with_individual_moves(self, drawing_points, move_delay):
        """Draw using individual MOVE commands for each point"""
        print("Using individual move commands for maximum precision")
        
        for contour_idx, contour in enumerate(drawing_points):
            print(f"Drawing contour {contour_idx + 1}/{len(drawing_points)} ({len(contour)} points)")
            
            if len(contour) == 0:
                continue
            
            # Move to start of contour with pen up
            start_x, start_y = contour[0]
            if not self.send_move(start_x, start_y):
                print(f"Failed to move to start of contour {contour_idx + 1}")
                return False
            time.sleep(move_delay)
            
            # Put pen down to start drawing this contour
            self.send_pen_down()
            time.sleep(move_delay)
            
            # Draw each point individually
            for point_idx, (x, y) in enumerate(contour[1:], 1):
                if not self.send_move(x, y):
                    print(f"Failed to send point {point_idx + 1}")
                    return False
                
                if move_delay > 0:
                    time.sleep(move_delay)
            
            # Lift pen after finishing this contour
            self.send_pen_up()
            time.sleep(move_delay)
        
        # Send stop command when done
        self.send_stop()
        print("Individual move drawing completed!")
        return True


    

    def _draw_with_ultra_fast_mode(self, drawing_points, batch_size, progress_callback=None):
        """Ultra-fast drawing with maximum performance optimizations"""
        print("Using ultra-fast mode with path optimization and large batches")
        
        # Ensure pen starts in up position
        self.send_pen_up()
        time.sleep(0.02)
        
        # Calculate total points for overall progress tracking
        total_points = sum(len(contour) for contour in drawing_points)
        points_processed = 0
        
        current_position = None  # Track robot position
        
        for contour_idx, contour in enumerate(drawing_points):
            print(f"Drawing contour {contour_idx + 1}/{len(drawing_points)} ({len(contour)} points)")
            
            if len(contour) == 0:
                continue
            
            # Move to start of contour with pen up
            start_x, start_y = contour[0]
            if current_position:
                travel_distance = ((start_x - current_position[0])**2 + (start_y - current_position[1])**2)**0.5
                print(f"  Travel distance: {travel_distance:.1f}mm")
            
            if not self.send_move(start_x, start_y):
                print(f"Failed to move to start of contour {contour_idx + 1}")
                return False
            time.sleep(0.02)  # Ultra-minimal delay
            
            # Update progress for the first point (move to start)
            points_processed += 1
            if progress_callback:
                progress_callback(1, 1, points_processed, total_points)
            
            # Put pen down to start drawing this contour
            self.send_pen_down()
            time.sleep(0.02)  # Ultra-minimal delay
            
            # Use large batches with integer coordinates for remaining points
            remaining_points = contour[1:]
            if len(remaining_points) > 0:
                # Process in batches and update overall progress
                batch_size_to_use = min(batch_size, len(remaining_points))
                
                for i in range(0, len(remaining_points), batch_size_to_use):
                    batch = remaining_points[i:i + batch_size_to_use]
                    
                    # Send this batch
                    if len(batch) > 1:
                        if not self.send_batch_moves_ultra_fast(batch, len(batch)):
                            print(f"Failed to send batch moves for contour {contour_idx + 1}")
                            return False
                    else:
                        # Single point
                        x, y = batch[0]
                        if not self.send_move(x, y):
                            print(f"Failed to send final point")
                            return False
                    
                    # Update overall progress
                    points_processed += len(batch)
                    if progress_callback:
                        progress_callback(1, 1, points_processed, total_points)
            
            # Update current position to end of this contour
            current_position = contour[-1]
            
            # Lift pen after finishing this contour
            self.send_pen_up()
            time.sleep(0.02)  # Ultra-minimal delay between contours
        
        # Send stop command when done
        self.send_stop()
        print("Ultra-fast drawing with path optimization completed!")
        return True

    def send_batch_moves_ultra_fast(self, points, batch_size):
        """Ultra-fast batch moves with coordinate system conversion"""
        if not points:
            return True
            
        # Process points in large batches with coordinate conversion
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            
            # Format batch command - robot handles coordinate system
            coords = []
            for x, y in batch:
                coords.extend([f"{int(round(x))}", f"{int(round(y))}"])
            
            cmd = f"BATCH,{','.join(coords)}\n"
            
            # Check command length (80 char limit)
            if len(cmd) > 78:
                # Split and retry with smaller batches
                mid_point = len(batch) // 2
                if mid_point > 0:
                    if not self.send_batch_moves_ultra_fast(batch[:mid_point], mid_point):
                        return False
                    if not self.send_batch_moves_ultra_fast(batch[mid_point:], len(batch) - mid_point):
                        return False
                    continue
            
            # Send batch command
            if not self._send_command(cmd):
                print(f"Failed to send ultra-fast batch of {len(batch)} points")
                return False
            # No delay between ultra-fast batches
                    
        return True

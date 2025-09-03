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
import math


class RobotController:
    def send_wait(self, target='right'):
        """Send wait command to robot (pause execution until next command)"""
        return self._send_command("WAIT\n", target=target)
    def draw_paths_dual(self, right_actions, left_actions, move_delay=0.02, use_batching=None, batch_size=8, progress_callback=None):
        """
        Asynchronous dual-robot drawing: both robots draw contours in parallel, synchronizing after each contour (or wait action).
        Each robot starts its contour as soon as possible, and after finishing, waits for the other to finish before proceeding.
        Args:
            right_actions: List of contours or 'wait' for the right robot
            left_actions: List of contours or 'wait' for the left robot
            move_delay: Delay between moves for individual mode
            use_batching: Override batch mode setting (None = use current setting)
            batch_size: Points per batch when using batch mode
            progress_callback: Function to call with progress updates
        Returns:
            True if both robots finish successfully, False otherwise
        """
        if not self.socket or not self.socket2:
            print("Both robots must be connected (right:1025, left:1026). Use connect() first.")
            return False

        import threading
        from itertools import zip_longest
        actual_batching = use_batching if use_batching is not None else self.use_batch_mode
        mode_text = "batch" if actual_batching else "individual"
        print(f"Starting dual-robot drawing using {mode_text} mode with async contour sync...")

        barrier = threading.Barrier(2)
        results = {'right': True, 'left': True}

        # Prepare progress tracking for dual-arm: combined total points and steps
        total_batches = max(len(right_actions), len(left_actions)) if (right_actions or left_actions) else 0
        # Compute total_points across both action lists
        def _count_points(actions_list):
            s = 0
            for a in actions_list:
                if a and a != 'wait' and isinstance(a, (list, tuple)):
                    try:
                        s += len(a)
                    except Exception:
                        pass
            return s

        total_points = _count_points(right_actions) + _count_points(left_actions)
        points_sent = {'value': 0}
        points_lock = threading.Lock()

        def do_action_list(actions, target):
            for idx, action in enumerate(actions):
                # Check if drawing should stop
                if self.should_stop():
                    print(f"[{target}] Drawing stopped at action {idx + 1}/{len(actions)}")
                    results[target] = False
                    break
                    
                if not results['right'] if target == 'right' else not results['left']:
                    break
                ok = True
                if action == 'wait':
                    print(f"[{target}] Waiting...")
                    ok = self.send_wait(target=target)
                elif not action:
                    ok = True
                else:
                    try:
                        # Ensure PEN_UP acknowledged before moving
                        if not self.send_pen_up(target=target):
                            print(f"[{target}] Failed to send PEN_UP")
                            ok = False
                        else:
                            time.sleep(0.02)

                            if actual_batching:
                                contour = action
                                start_x, start_y = contour[0]

                                # Move to contour start
                                # Wait for peer retreat to complete (time-based)
                                try:
                                    self._wait_for_peer_retreat(target)
                                except Exception:
                                    pass
                                # If geometry-based collision avoidance is enabled, poll until safe
                                try:
                                    start_pt = (start_x, start_y)
                                    waited = 0.0
                                    while self._conflicts_with_peer(target, start_pt) and waited < float(self.collision_wait_timeout):
                                        time.sleep(float(self.collision_check_interval))
                                        waited += float(self.collision_check_interval)
                                except Exception:
                                    pass
                                # Use two-step transition to start (offset then real start)
                                if not self._transition_to_start(start_x, start_y, target=target):
                                    print(f"[{target}] Failed to transition to start of contour")
                                    ok = False
                                else:
                                    # Pen down to draw
                                        if not self.send_pen_down(target=target):
                                            print(f"[{target}] Failed to send PEN_DOWN")
                                            ok = False
                                        else:
                                            time.sleep(0.02)
                                            
                                            # Explicitly move to first point with pen down
                                            start_x, start_y = contour[0]
                                            if not self.send_move(start_x, start_y, target=target):
                                                print(f"[{target}] Failed to send explicit move to first point")
                                                ok = False
                                            else:
                                                if len(contour) > 1:
                                                    # send batches for remaining points; if successful, account for all contour points (including start)
                                                    if not self.send_batch_moves(contour[1:], batch_size=batch_size, target=target):
                                                        print(f"[{target}] Failed to send batch moves")
                                                        ok = False
                                                    else:
                                                        # Increment shared points_sent by full contour length
                                                        if progress_callback:
                                                            with points_lock:
                                                                points_sent['value'] += len(contour)
                                                                cur = points_sent['value']
                                                            try:
                                                                progress_callback(idx + 1, total_batches, cur, total_points)
                                                            except Exception:
                                                                pass
                                            # Lift pen after contour
                                            if not self.send_pen_up(target=target):
                                                print(f"[{target}] Failed to send PEN_UP (after contour)")
                                                ok = False
                                            else:
                                                # Notify robot between contours so RAPID can perform a retreat/back-off
                                                # Determine next contour start from the actions list if available
                                                next_start = None
                                                try:
                                                    if idx + 1 < len(actions):
                                                        nxt = actions[idx + 1]
                                                        if nxt and nxt != 'wait':
                                                            if isinstance(nxt, (list, tuple)) and len(nxt) > 0:
                                                                next_start = nxt[0]
                                                except Exception:
                                                    next_start = None
                                                self.send_between_command(target=target, next_start=next_start)
                                            time.sleep(0.02)

                            else:
                                contour = action
                                start_x, start_y = contour[0]

                                # Transition to start with side-specific X offset
                                try:
                                    self._wait_for_peer_retreat(target)
                                except Exception:
                                    pass
                                try:
                                    start_pt = (start_x, start_y)
                                    waited = 0.0
                                    while self._conflicts_with_peer(target, start_pt) and waited < float(self.collision_wait_timeout):
                                        time.sleep(float(self.collision_check_interval))
                                        waited += float(self.collision_check_interval)
                                except Exception:
                                    pass
                                if not self._transition_to_start(start_x, start_y, target=target):
                                    print(f"[{target}] Failed to transition to start of contour")
                                    ok = False
                                else:
                                    # Count the transition-to-start as a sent point (for progress)
                                    if progress_callback:
                                        with points_lock:
                                            points_sent['value'] += 1
                                            cur = points_sent['value']
                                        try:
                                            progress_callback(idx + 1, total_batches, cur, total_points)
                                        except Exception:
                                            pass

                                    if not self.send_pen_down(target=target):
                                        print(f"[{target}] Failed to send PEN_DOWN")
                                        ok = False
                                    else:
                                        time.sleep(move_delay)
                                        
                                        # Explicitly move to first point with pen down to ensure precise start
                                        start_x, start_y = contour[0]
                                        if not self.send_move(start_x, start_y, target=target):
                                            print(f"[{target}] Failed to send explicit move to first point")
                                            ok = False
                                        else:
                                            if move_delay > 0:
                                                time.sleep(move_delay)
                                            
                                            # Draw remaining points
                                            for x, y in contour[1:]:
                                                if not self.send_move(x, y, target=target):
                                                    print(f"[{target}] Failed to send point")
                                                    ok = False
                                                    break
                                                else:
                                                    # Increment progress per point sent
                                                    if progress_callback:
                                                        with points_lock:
                                                            points_sent['value'] += 1
                                                            cur = points_sent['value']
                                                        try:
                                                            progress_callback(idx + 1, total_batches, cur, total_points)
                                                        except Exception:
                                                            pass
                                                    if move_delay > 0:
                                                        time.sleep(move_delay)
                                        if not self.send_pen_up(target=target):
                                            print(f"[{target}] Failed to send PEN_UP (after contour)")
                                            ok = False
                                        else:
                                            # Send between-contour command to allow robot-side retreat
                                            next_start = None
                                            try:
                                                if idx + 1 < len(actions):
                                                    nxt = actions[idx + 1]
                                                    if nxt and nxt != 'wait':
                                                        if isinstance(nxt, (list, tuple)) and len(nxt) > 0:
                                                            next_start = nxt[0]
                                            except Exception:
                                                next_start = None
                                            self.send_between_command(target=target, next_start=next_start)
                                        time.sleep(move_delay)

                    except Exception as e:
                        print(f"[{target}] Error during drawing: {e}")
                        # Only send cleanup commands if not in emergency stop
                        if not self.should_stop():
                            try:
                                self.send_pen_up(target=target)
                            except Exception:
                                pass
                            try:
                                self.send_stop(target=target)
                            except Exception:
                                pass
                        ok = False
                if not ok:
                    if target == 'right':
                        results['right'] = False
                    else:
                        results['left'] = False
                    break
                try:
                    barrier.wait()
                except threading.BrokenBarrierError:
                    break
            # Only send final stop if not already in emergency stop
            if not self.should_stop():
                self.send_stop(target=target)

        # Pad shorter list with None for zip_longest
        max_len = max(len(right_actions), len(left_actions))
        right_padded = list(right_actions) + [None] * (max_len - len(right_actions))
        left_padded = list(left_actions) + [None] * (max_len - len(left_actions))

        t_right = threading.Thread(target=do_action_list, args=(right_padded, 'right'))
        t_left = threading.Thread(target=do_action_list, args=(left_padded, 'left'))
        t_right.start()
        t_left.start()
        t_right.join()
        t_left.join()

        if not results['right'] or not results['left']:
            print("Error in dual-robot drawing step.")
            return False
        print("Dual-robot drawing with async contour sync completed!")
        return True
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
    # Default transition offset in X (mm) applied before moving to contour start
    DEFAULT_TRANSITION_OFFSET_X = 50

    # Command response settings
    RESPONSE_TIMEOUT = 20.0
    START_COMMAND_TIMEOUT = 90.0  # Extended timeout for START command (robot initialization)
    MAX_RETRIES = 3
    # Default pause after robot reports RETREAT/OK to allow physical retreat (seconds)
    DEFAULT_POST_RETREAT_DELAY = 0.7
    
    def __init__(self, ip=DEFAULT_IP, port=DEFAULT_PORT, port_l=DEFAULT_PORT_L):
        """
        Initialize robot controller.
        
        Args:
            ip (str): Robot controller IP address
            port (int): TCP communication port for right robot
            port_l (int): TCP communication port for left robot (dual-arm mode)
        """
        self.ip = ip
        self.port = port
        self.port_l = port_l  # Left robot port for dual-arm mode
        self.socket = None
        self.socket2 = None  # For second port (left robot)
        self.use_batch_mode = True  # Default to batch mode for speed
        self.use_center_origin = True  # Default to center-based coordinates (current system)
        # Transition offset in X direction (positive moves to +X, negative to -X)
        self.transition_offset_x = self.DEFAULT_TRANSITION_OFFSET_X
        # Track last known robot positions for each target to enable safer routing
        self.current_position = {'right': None, 'left': None}
        # Workspace bounds (mm) - can be tuned via set_bounds
        self.bounds = {'xmin': -1000.0, 'xmax': 1000.0, 'ymin': -1000.0, 'ymax': 1000.0}
        # Pause after RETREAT/OK to allow physical retreat before other moves
        self.post_retreat_delay = self.DEFAULT_POST_RETREAT_DELAY
        # Track when an arm finished its retreat/positioning (seconds since epoch)
        self.last_retreat_done = {'right': 0.0, 'left': 0.0}
        # Stop check function for emergency stops
        self.stop_check = None
    
    def set_stop_check(self, stop_check_func):
        """
        Set a function that will be called to check if drawing should stop.
        
        Args:
            stop_check_func: A function that returns True to continue, False to stop
        """
        self.stop_check = stop_check_func
    
    def should_stop(self):
        """
        Check if drawing should stop.
        
        Returns:
            True if drawing should stop, False if it should continue
        """
        if self.stop_check is None:
            return False
        try:
            return not self.stop_check()
        except:
            return True  # If there's an error checking, assume we should stop
    def set_transition_offset_x(self, mm):
        """Set the transition X offset (mm). Positive values move toward +X for left arm, negative for right arm."""
        try:
            self.transition_offset_x = float(mm)
        except Exception:
            pass

    def set_bounds(self, xmin, xmax, ymin, ymax):
        """Set workspace bounds (mm) used to clamp intermediate safety moves."""
        try:
            self.bounds['xmin'] = float(xmin)
            self.bounds['xmax'] = float(xmax)
            self.bounds['ymin'] = float(ymin)
            self.bounds['ymax'] = float(ymax)
        except Exception:
            pass

    def set_collision_radius(self, mm):
        try:
            self.collision_radius = float(mm)
        except Exception:
            pass

    def set_collision_wait_timeout(self, seconds):
        try:
            self.collision_wait_timeout = float(seconds)
        except Exception:
            pass

    def _compute_intermediate_point(self, start_xy, target='right'):
        """Return the intermediate (post-retreat) X-offset point for a given start (x,y)."""
        try:
            nx, ny = start_xy
            off = float(self.transition_offset_x)
        except Exception:
            return None
        if target == 'right':
            x_off = -abs(off)
        else:
            x_off = abs(off)
        interm_x = nx + x_off
        interm_y = ny
        return self._clamp_to_bounds(interm_x, interm_y)

    def _conflicts_with_peer(self, target, start_xy):
        """Return True if the computed intermediate point conflicts with peer current position."""
        try:
            peer = 'left' if target == 'right' else 'right'
            peer_pos = self.current_position.get(peer)
            if not peer_pos:
                return False
            interm = self._compute_intermediate_point(start_xy, target=target)
            if interm is None:
                return False
            dx = interm[0] - float(peer_pos[0])
            dy = interm[1] - float(peer_pos[1])
            d = math.hypot(dx, dy)
            return d <= float(self.collision_radius)
        except Exception:
            return False

    def set_post_retreat_delay(self, seconds):
        """Set extra safety pause (seconds) after RETREAT OK before next moves."""
        try:
            self.post_retreat_delay = float(seconds)
        except Exception:
            pass

    def _wait_for_peer_retreat(self, target):
        """If peer arm recently requested retreat, wait until its post_retreat_delay has elapsed."""
        try:
            peer = 'left' if target == 'right' else 'right'
            ts = float(self.last_retreat_done.get(peer, 0.0) or 0.0)
            if ts <= 0:
                return
            safe_time = ts + float(getattr(self, 'post_retreat_delay', 0.0))
            now = time.time()
            wait = safe_time - now
            if wait > 0:
                print(f"[{target}] Waiting for peer {peer} retreat: sleeping {wait:.2f}s")
                time.sleep(wait)
        except Exception:
            return

    def _clamp_to_bounds(self, x, y):
        """Clamp (x,y) to configured workspace bounds and return the clamped tuple."""
        try:
            cx = max(self.bounds['xmin'], min(self.bounds['xmax'], float(x)))
            cy = max(self.bounds['ymin'], min(self.bounds['ymax'], float(y)))
            return (cx, cy)
        except Exception:
            return (x, y)

    def _contains_left_forbidden(self, points):
        """Return True if any point in `points` lies inside the left-arm forbidden rectangle.

        Forbidden rectangle (robot coords): x < 130 and y < 40
        """
        try:
            for x, y in points:
                if float(x) < 130.0 and float(y) < 40.0:
                    return True
        except Exception:
            pass
        return False

    def _transition_to_start(self, start_x, start_y, target='right'):
        """Perform a horizontal U-shaped transition to safely move between contours.
        
        The horizontal U-shape pattern:
        1. RETREAT already moved back horizontally (±50mm in X)
        2. Move to next contour's Y coordinate while staying back (horizontal leg of U)  
        3. Move forward to the actual start position (completing the U)
        
        This avoids drawing lines since PEN_UP/PEN_DOWN handle vertical movement.
        For `target=='right'` the offset is -transition_offset_x, for `target=='left'` it's +transition_offset_x.
        Returns True on success, False on failure.
        """
        # Determine side bias: right -> negative offset, left -> positive offset
        try:
            off = float(self.transition_offset_x)
        except Exception:
            off = float(self.DEFAULT_TRANSITION_OFFSET_X)

        if target == 'right':
            x_off = -abs(off)
        else:
            x_off = abs(off)

        # Step 2 of horizontal U: Move to next contour's Y coordinate while staying back
        # This creates the horizontal "bridge" of the U-shape
        back_position_x = start_x + x_off
        if not self.send_move(back_position_x, start_y, target=target):
            print(f"[{target}] Failed to move to back position at Y-level ({back_position_x:.1f}, {start_y:.1f})")
            return False
        time.sleep(0.02)
            
        # Step 3 of horizontal U: Move forward to the actual start position
        # This completes the U-shape horizontally
        if not self.send_move(start_x, start_y, target=target):
            print(f"[{target}] Failed to move to actual start ({start_x:.1f}, {start_y:.1f})")
            return False
        return True
    
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

            # Connect to second port (left robot)
            self.socket2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket2.settimeout(self.DEFAULT_TIMEOUT)
            self.socket2.connect((self.ip, self.port_l))
            print(f"Connected to ABB robot at {self.ip}:{self.port_l}")

            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            self.socket = None
            if hasattr(self, 'socket2') and self.socket2:
                self.socket2.close()
            self.socket2 = None
            return False
    
    def send_move(self, x, y, wait_response=True, target='right'):
        """Send movement command to robot with coordinate system awareness"""
        # Safety: block single MOVE commands to left if the coordinate is in left-forbidden area
        try:
            if target == 'left' and float(x) < 130.0 and float(y) < 40.0:
                print(f"Refusing MOVE to left for point ({x:.1f},{y:.1f}): inside left-forbidden rectangle (x<130,y<40)")
                return False
        except Exception:
            pass

        cmd = f"MOVE,{x:.2f},{y:.2f}\n"
        ok = self._send_command(cmd, wait_response, target=target)
        # Update last-known position for the target on success
        try:
            if ok:
                if target not in ('right', 'left'):
                    # If caller used 'both' treat it as right for tracking
                    tkey = 'right'
                else:
                    tkey = target
                self.current_position[tkey] = (float(x), float(y))
        except Exception:
            pass
        return ok
    
    def send_batch_moves(self, points, batch_size=3, max_batch_size=6, target='right'):
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
            
        print(f"Sending {len(points)} points with dynamic batch sizing (base: {batch_size}, max: {max_batch_size}) to {target}")
        
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

    def _get_socket(self, target='right'):
        """Return socket object(s) for target: 'right', 'left', or 'both'.

        Returns a tuple (right_socket, left_socket) where missing sockets are None.
        """
        right = self.socket
        left = getattr(self, 'socket2', None)
        if target == 'right':
            return (right, None)
        if target == 'left':
            return (None, left)
        # both
        return (right, left)
    
    def send_pen_up(self, target='right'):
        """Send pen up command (lift drawing tool)"""
        return self._send_command("PEN_UP\n", target=target)

    def send_between_command(self, cmd=None, target='right', wait_response=True, timeout=None, next_start=None):
        """Send a simple between-contour command for the robot to interpret.

        By default this sends "RETREAT\n". The robot RAPID/task should implement
        handling for this command (e.g. local back-off or move-to-edge).

        If `next_start` is provided as a tuple (x, y) this helper will, after
        receiving the robot ACK for the between-command, issue a MOVE to the
        intermediate point formed by (next_start_x +/- transition_offset_x, next_start_y).

        This puts the robot at the correct Y of the next contour while keeping
        the X offset (back-off) in the side-respected direction.
        """
        command = cmd if cmd is not None else "RETREAT\n"
        ok = self._send_command(command, wait_response=wait_response, timeout=timeout, target=target)

        # As soon as the robot ACKs the RETREAT command, record the timestamp so
        # peer threads can observe that a retreat was requested and wait.
        try:
            if ok and target in ('right', 'left'):
                self.last_retreat_done[target] = time.time()
        except Exception:
            pass

        # If the robot acknowledged and we were given a next contour start,
        # move to the intermediate offset point (x +/- offset, y) using a safer two-step route.
        if ok and next_start is not None:
            try:
                nx, ny = next_start
                try:
                    off = float(self.transition_offset_x)
                except Exception:
                    off = float(self.DEFAULT_TRANSITION_OFFSET_X)

                if target == 'right':
                    x_off = -abs(off)
                else:
                    x_off = abs(off)

                interm_x = nx + x_off
                interm_y = ny

                # Clamp intermediate target to workspace bounds
                interm_x, interm_y = self._clamp_to_bounds(interm_x, interm_y)

                # Attempt to use current known position for safer axis-separated routing
                cur = None
                try:
                    cur = self.current_position.get(target)
                except Exception:
                    cur = None

                if cur is None:
                    # No known current position - fallback to direct intermediate move
                    if not self.send_move(interm_x, interm_y, wait_response=True, target=target):
                        print(f"[{target}] Failed to move to intermediate post-retreat point ({interm_x:.1f}, {interm_y:.1f})")
                        return False
                else:
                    cur_x, cur_y = cur
                    # First move in Y to next contour Y while keeping current X (reduces diagonal sweeps)
                    step1_x, step1_y = self._clamp_to_bounds(cur_x, interm_y)
                    if not self.send_move(step1_x, step1_y, wait_response=True, target=target):
                        print(f"[{target}] Failed safety step to ({step1_x:.1f}, {step1_y:.1f})")
                        return False
                    # Then move in X to the intermediate offset X at correct Y
                    step2_x, step2_y = interm_x, interm_y
                    if not self.send_move(step2_x, step2_y, wait_response=True, target=target):
                        print(f"[{target}] Failed to move to intermediate post-retreat point ({step2_x:.1f}, {step2_y:.1f})")
                        return False
            except Exception as e:
                print(f"Error handling next_start in send_between_command: {e}")
                return False

    # (timestamp already set on ACK above)

        # After OK and any intermediate moves, give robot a moment to physically retreat
        try:
            if ok and getattr(self, 'post_retreat_delay', 0):
                time.sleep(float(self.post_retreat_delay))
        except Exception:
            pass

        return ok

    def send_pen_down(self, target='right'):
        """Send pen down command (lower drawing tool)"""
        return self._send_command("PEN_DOWN\n", target=target)

    def send_stop(self, target='right'):
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
    
    def _send_command(self, cmd, wait_response=True, timeout=None, target='right'):
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
        # Normalize: if primary is None but secondary exists for a single-target call
        # (e.g. target == 'left'), treat the available socket as primary.
        if primary_sock is None and secondary_sock is not None and target != 'both':
            primary_sock = secondary_sock
            secondary_sock = None

        try:
            print(f"Sending: {cmd.strip()} to {target}")

            # Send to primary if requested
            if primary_sock:
                primary_sock.sendall(cmd.encode())

            # Send to secondary if requested
            if secondary_sock:
                secondary_sock.sendall(cmd.encode())

            # Only wait for response(s) from socket(s)
            if wait_response and primary_sock:
                # Helper: receive a single line (terminated by \n) from a socket within timeout
                def _recv_line(sock, timeout_secs):
                    orig_to = sock.gettimeout()
                    try:
                        sock.settimeout(timeout_secs if timeout_secs is not None else self.RESPONSE_TIMEOUT)
                        data = b""
                        while True:
                            chunk = sock.recv(1024)
                            if not chunk:
                                # connection closed
                                break
                            data += chunk
                            if b"\n" in data or b"\r" in data:
                                break
                        try:
                            return data.decode(errors='ignore').strip()
                        except Exception:
                            return data.decode('utf-8', errors='ignore').strip()
                    finally:
                        try:
                            sock.settimeout(orig_to)
                        except Exception:
                            pass

                # If we sent to both sockets, wait for both responses
                if secondary_sock and (target == 'both' or target is None):
                    print("Waiting for responses from both robots...")
                    # Wait for primary
                    try:
                        resp1 = _recv_line(primary_sock, timeout)
                    except socket.timeout:
                        print(f"Primary socket timeout after {timeout or self.RESPONSE_TIMEOUT}s")
                        return False
                    # Wait for secondary
                    try:
                        resp2 = _recv_line(secondary_sock, timeout)
                    except socket.timeout:
                        print(f"Secondary socket timeout after {timeout or self.RESPONSE_TIMEOUT}s")
                        return False

                    print(f"Robot responses: primary='{resp1}', secondary='{resp2}'")
                    # Check responses based on command type
                    if cmd.strip() == 'STOP':
                        return (resp1 == 'STOPPED') and (resp2 == 'STOPPED')
                    else:
                        return (resp1 == 'OK') and (resp2 == 'OK')
                else:
                    # Single-socket target (primary only)
                    try:
                        resp = _recv_line(primary_sock, timeout)
                    except socket.timeout:
                        print(f"Command timeout after {timeout or self.RESPONSE_TIMEOUT}s - no response from robot")
                        return False

                    print(f"Robot response: {resp}")
                    # Check response based on command type
                    if cmd.strip() == 'STOP':
                        return resp == 'STOPPED'
                    else:
                        return resp == 'OK'

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
            # Only send cleanup commands if not in emergency stop
            if not self.should_stop():
                self.send_pen_up()
                self.send_stop()
            return False
        except Exception as e:
            print(f"Error during drawing: {e}")
            # Only send cleanup commands if not in emergency stop
            if not self.should_stop():
                self.send_pen_up()
                self.send_stop()
            return False

    def _draw_with_individual_moves(self, drawing_points, move_delay):
        """Draw using individual MOVE commands for each point"""
        print("Using individual move commands for maximum precision")
        
        for contour_idx, contour in enumerate(drawing_points):
            # Check if drawing should stop
            if self.should_stop():
                print(f"Drawing stopped at contour {contour_idx + 1}/{len(drawing_points)}")
                return False
                
            print(f"Drawing contour {contour_idx + 1}/{len(drawing_points)} ({len(contour)} points)")
            
            if len(contour) == 0:
                continue
            
            # Move to start of contour with pen up
            start_x, start_y = contour[0]
            # Transition to start using X offset strategy (right arm moves left first, left arm moves right first)
            if not self._transition_to_start(start_x, start_y):
                print(f"Failed to transition to start of contour {contour_idx + 1}")
                return False
            time.sleep(move_delay)
            
            # Put pen down to start drawing this contour
            self.send_pen_down()
            time.sleep(move_delay)
            
            # Explicitly move to first point with pen down to ensure precise start
            start_x, start_y = contour[0]
            if not self.send_move(start_x, start_y):
                print(f"Failed to send explicit move to first point")
                return False
            time.sleep(move_delay)
            
            # Draw each remaining point individually
            for point_idx, (x, y) in enumerate(contour[1:], 1):
                if not self.send_move(x, y):
                    print(f"Failed to send point {point_idx + 1}")
                    return False
                
                if move_delay > 0:
                    time.sleep(move_delay)
            
            # Lift pen after finishing this contour
            self.send_pen_up()
            # Send between-contour command so robot can retreat or reposition as implemented on the robot
            # If there's a next contour, move to its Y with side offset after retreat
            next_start = None
            if contour_idx + 1 < len(drawing_points) and len(drawing_points[contour_idx + 1]) > 0:
                next_start = drawing_points[contour_idx + 1][0]
            self.send_between_command(next_start=next_start)
            time.sleep(move_delay)
        
        # Send stop command when done (only if not already in emergency stop)
        if not self.should_stop():
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
            # Check if drawing should stop
            if self.should_stop():
                print(f"Drawing stopped at contour {contour_idx + 1}/{len(drawing_points)}")
                return False
                
            print(f"Drawing contour {contour_idx + 1}/{len(drawing_points)} ({len(contour)} points)")
            
            if len(contour) == 0:
                continue
            
            # Move to start of contour with pen up
            start_x, start_y = contour[0]
            if current_position:
                travel_distance = ((start_x - current_position[0])**2 + (start_y - current_position[1])**2)**0.5
                print(f"  Travel distance: {travel_distance:.1f}mm")
            
            # Transition to start using offset
            if not self._transition_to_start(start_x, start_y):
                print(f"Failed to transition to start of contour {contour_idx + 1}")
                return False
            time.sleep(0.02)  # Ultra-minimal delay
            
            # Update progress for the first point (move to start)
            points_processed += 1
            if progress_callback:
                progress_callback(1, 1, points_processed, total_points)
            
            # Put pen down to start drawing this contour
            self.send_pen_down()
            time.sleep(0.02)  # Ultra-minimal delay
            
            # Explicitly move to first point with pen down to ensure precise start
            start_x, start_y = contour[0]
            if not self.send_move(start_x, start_y):
                print(f"Failed to send explicit move to first point")
                return False
            time.sleep(0.02)
            
            # Use large batches with integer coordinates for remaining points
            remaining_points = contour[1:]
            if len(remaining_points) > 0:
                # Process in batches and update overall progress
                batch_size_to_use = min(batch_size, len(remaining_points))
                
                for i in range(0, len(remaining_points), batch_size_to_use):
                    batch = remaining_points[i:i + batch_size_to_use]
                    
                    # Safety: do not send to left if batch contains forbidden points
                    if self._contains_left_forbidden(batch):
                        print(f"Refusing ultra-fast batch for contour {contour_idx + 1}: contains left-forbidden points")
                        return False
                    # Send this batch
                    if len(batch) > 1:
                        if not self.send_batch_moves_ultra_fast(batch, len(batch), target='right' if self.socket else 'right'):
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
            # After retreat, move to next contour's Y with X offset if available
            next_start = None
            if contour_idx + 1 < len(drawing_points) and len(drawing_points[contour_idx + 1]) > 0:
                next_start = drawing_points[contour_idx + 1][0]
            # Send between-contour command which will also move to intermediate point if next_start provided
            self.send_between_command(next_start=next_start)
        
        # Send stop command when done (only if not already in emergency stop)
        if not self.should_stop():
            self.send_stop()
        print("Ultra-fast drawing with path optimization completed!")
        return True

    def send_batch_moves_ultra_fast(self, points, batch_size, target='right'):
        """Ultra-fast batch moves with coordinate system conversion"""
        if not points:
            return True
        # Safety: refuse to send to left if any point is in left-forbidden area
        if target == 'left' and self._contains_left_forbidden(points):
            print(f"Refusing to send ultra-fast batch to left: contains points inside left-forbidden rectangle (x<130,y<40)")
            return False
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
                    if not self.send_batch_moves_ultra_fast(batch[:mid_point], mid_point, target=target):
                        return False
                    if not self.send_batch_moves_ultra_fast(batch[mid_point:], len(batch) - mid_point, target=target):
                        return False
                    continue

            # Send batch command
            if not self._send_command(cmd, target=target):
                print(f"Failed to send ultra-fast batch of {len(batch)} points")
                return False
            # No delay between ultra-fast batches

        return True

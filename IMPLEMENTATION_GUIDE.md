# 🔧 Robot Drawing System - Technical Implementation Guide
**How Components Work Together - Internal Documentation**

---

## 🏗️ Core System Components

### 1. simple_gui.py - Main User Interface
**Purpose**: Provides the primary user interface and coordinates all system operations

#### Key Classes & Methods:
```python
class SimpleRobotGUI:
    def __init__(self):
        # Initialize GUI components, load configuration
        # Set up 2x2 expo mode interface
        # Initialize robot drawer with default settings
        
    def create_simple_interface(self):
        # Creates the main 2x2 grid layout:
        # [Take Photo] [Photo Preview]
        # [Style Select] [Start Drawing]
        
    def auto_process_image(self):
        # Automatically processes loaded images
        # Calls image_processor → coordinate_transformer → visualizer
        
    def start_robot_drawing(self):
        # Main drawing workflow:
        # 1. Validate connection and processed image
        # 2. Send START command based on coordinate system
        # 3. Execute drawing in background thread
        # 4. Handle progress updates and error recovery
```

#### Technical Features:
- **Configuration Management**: Automatic save/restore of user settings
- **Voice Integration**: Real-time Polish voice command processing
- **Progress Monitoring**: Live drawing progress with visual feedback
- **Error Handling**: Graceful recovery from robot communication errors
- **Thread Safety**: Proper synchronization between GUI and worker threads

---

### 2. robot_drawer.py - System Orchestrator
**Purpose**: Central coordinator that manages all subsystem interactions

#### Core Workflow:
```python
class RobotDrawer:
    def load_image(self, image_path, precision="high", enable_tsp=True):
        # 1. Process image using ImageProcessor
        contour_data = self.processor.load_and_process_image(
            image_path, precision, enable_tsp, detection_method
        )
        
        # 2. Transform to robot coordinates  
        self.drawing_points = self.transformer.contours_to_robot_coordinates(
            contour_data
        )
        
        # 3. Store visualization data
        self.image_data = self.processor.get_edges_for_visualization(
            image_path, detection_method
        )
        
    def draw(self, progress_callback=None):
        # Execute drawing on robot
        return self.robot.draw_paths(
            self.drawing_points, 
            progress_callback=progress_callback
        )
        
    def draw_dual(self, buffer_radius=40):
        # Dual-arm drawing with collision avoidance
        from coordinate_transformer import master_slave_assign_contours
        
        # Split contours between arms with safety buffers
        right_actions, left_actions = [], []
        remaining = self.drawing_points[:]
        
        while remaining:
            # Assign master/slave roles alternately
            master_role = 'right' if len(right_actions) % 2 == 0 else 'left'
            
            # Get safe assignment with forbidden zones
            master, slave, rest, _, forbidden = master_slave_assign_contours(
                remaining, master=master_role, buffer_radius=buffer_radius
            )
            
            # Add to appropriate action lists
            if master_role == 'right':
                right_actions.append(master)
                left_actions.append(slave if slave else 'wait')
            else:
                left_actions.append(master) 
                right_actions.append(slave if slave else 'wait')
                
            remaining = rest
            
        # Execute synchronized dual-arm drawing
        return self.robot.draw_paths_dual(right_actions, left_actions)
```

---

### 3. image_processor.py - Image to Path Conversion
**Purpose**: Converts digital images into robot-drawable coordinate paths

#### Image Processing Pipeline:
```python
def extract_edge_following_path(self, image_path, precision="high", 
                               detection_method="threshold"):
    # 1. Load and preprocess image
    image = cv2.imread(image_path)
    image = cv2.rotate(image, cv2.ROTATE_180)  # Flip for robot orientation
    
    # 2. Add white border padding (prevents edge artifacts)
    image = cv2.copyMakeBorder(image, 20, 20, 20, 20, 
                              cv2.BORDER_CONSTANT, value=[255, 255, 255])
    
    # 3. Convert to grayscale and blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 3)
    gray = cv2.medianBlur(gray, 5)
    
    # 4. Apply selected edge detection method
    if detection_method == "canny":
        edges = cv2.Canny(gray, 50, 100)
        edges = self._thin_edges(edges)  # Single-pixel width
    elif detection_method == "adaptive":
        # Dynamic parameters based on precision
        block_size = self.ADAPTIVE_PRECISION_ADJUSTMENTS[precision]["block_size"]
        c_value = self.ADAPTIVE_PRECISION_ADJUSTMENTS[precision]["c"]
        edges = cv2.adaptiveThreshold(gray, 255, 
                                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, block_size, c_value)
    else:  # threshold (default)
        ret, edges = cv2.threshold(gray, 220, 255, 
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 5. Find and filter contours
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, 
                                  cv2.CHAIN_APPROX_SIMPLE)
    
    # 6. Filter by minimum length and simplify
    simplified_contours = []
    for contour in contours:
        if len(contour) >= self.MIN_CONTOUR_LENGTH:
            # Douglas-Peucker simplification
            epsilon = cv2.arcLength(contour, True) * precision_factor
            simplified = cv2.approxPolyDP(contour, epsilon, True)
            simplified_contours.append(simplified)
    
    # 7. TSP optimization (if enabled)
    if self.enable_tsp:
        simplified_contours = self._tsp_optimize_order(simplified_contours)
    
    return {
        'contours': simplified_contours,
        'image_shape': edges.shape,
        'simplification_factor': precision_factor
    }
```

#### Edge Detection Methods Explained:

**Canny Edge Detection**:
- Best for: General-purpose images with clear edges
- Process: Gradient calculation → Non-maximum suppression → Hysteresis thresholding
- Output: Clean, single-pixel width edges

**Adaptive Threshold**:
- Best for: Images with varying lighting conditions
- Process: Local threshold calculation using Gaussian-weighted neighborhood
- Output: Binary image adapted to local brightness variations

**Binary Threshold + OTSU**:
- Best for: High-contrast images, scanned documents
- Process: Automatic optimal threshold selection using OTSU algorithm
- Output: Clean binary separation between foreground/background

---

### 4. coordinate_transformer.py - Robot Coordinate Mapping
**Purpose**: Transforms image pixel coordinates to robot workspace coordinates

#### Coordinate System Implementation:
```python
class CoordinateTransformer:
    def contours_to_robot_coordinates(self, contour_data):
        # Get image dimensions
        image_height, image_width = contour_data['image_shape']
        
        robot_contours = []
        for contour in contour_data['contours']:
            robot_points = []
            
            for point in contour:
                # Extract pixel coordinates
                px, py = point[0]  # OpenCV format: [[x,y]]
                
                if self.use_center_origin:
                    # Center-based: (0,0) at workspace center
                    # Transform: pixel [0,width] → robot [-max_x/2, +max_x/2]
                    robot_x = ((px / image_width) - 0.5) * self.max_x
                    robot_y = ((py / image_height) - 0.5) * self.max_y
                else:
                    # Corner-based: (0,0) at top-left corner
                    # Transform: pixel [0,width] → robot [margin, max_x-margin]
                    effective_width = self.max_x - 2 * self.margin_x
                    effective_height = self.max_y - 2 * self.margin_y
                    
                    robot_x = (px / image_width) * effective_width + self.margin_x
                    robot_y = (py / image_height) * effective_height + self.margin_y
                
                robot_points.append((robot_x, robot_y))
            
            # Apply smoothing if enabled
            if self.enable_smoothing:
                robot_points = self._apply_smoothing(robot_points)
            
            robot_contours.append(robot_points)
        
        return robot_contours
```

#### Dual-Arm Task Assignment:
```python
def master_slave_assign_contours(contours, master, buffer_radius=40):
    # 1. Select master contour based on arm preference
    if master == 'left':
        # Left arm: prioritize leftmost contours
        # CRITICAL: Avoid left-forbidden rectangle (0,0)→(130,40)
        for contour in sorted(contours, key=lambda c: contour_center_x(c)):
            if not _contour_in_left_forbidden(contour):
                master_contour = contour
                break
        else:
            # Force switch to right arm if no safe contour found
            master = 'right'
            master_contour = sorted(contours, key=contour_center_x)[-1]
    else:
        # Right arm: prioritize rightmost contours (no restrictions)
        master_contour = sorted(contours, key=contour_center_x)[-1]
    
    # 2. Create forbidden zones around master contour
    forbidden_circles = [Point(x, y).buffer(buffer_radius) 
                        for x, y in master_contour]
    master_forbidden_area = unary_union(forbidden_circles)
    
    # 3. Add trailing forbidden zones to prevent collisions
    # Create wide rectangular "tail" extending from master area
    bounds = master_forbidden_area.bounds
    if master == 'right':
        # Right arm: extend forbidden area leftward
        tail_polygon = box(bounds[0] - tail_width, bounds[1], 
                          bounds[0], bounds[3])
    else:
        # Left arm: extend forbidden area rightward  
        tail_polygon = box(bounds[2], bounds[1],
                          bounds[2] + tail_width, bounds[3])
    
    complete_forbidden_area = unary_union([master_forbidden_area, tail_polygon])
    
    # 4. Find slave contour that doesn't conflict with forbidden area
    slave_contour = None
    remaining_contours = []
    
    for contour in contours:
        if contour != master_contour:
            if not contour_overlaps_forbidden(contour, complete_forbidden_area):
                if slave_contour is None:
                    slave_contour = contour
                else:
                    remaining_contours.append(contour)
            else:
                remaining_contours.append(contour)
    
    return master_contour, slave_contour, remaining_contours, [], complete_forbidden_area
```

---

### 5. robot_communication.py - Network Protocol Implementation
**Purpose**: Handles TCP/IP communication with ABB YuMi robot controllers

#### Connection Management:
```python
class RobotController:
    def connect(self):
        # Primary robot connection (right arm)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10.0)
        self.socket.connect((self.ip, self.port))
        
        # Secondary robot connection (left arm, dual-arm mode)
        if self.port_l and self.port_l != self.port:
            self.socket_l = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_l.settimeout(10.0)
            self.socket_l.connect((self.ip, self.port_l))
        
        print(f"Connected to robot at {self.ip}:{self.port}")
        return True
        
    def _send_command(self, cmd, wait_response=True, timeout=None, target='right'):
        # Select appropriate socket based on target
        sock = self.socket if target == 'right' else self.socket_l
        
        if target == 'both':
            # Send to both sockets simultaneously
            success = True
            success &= self._send_command(cmd, wait_response, timeout, 'right')
            success &= self._send_command(cmd, wait_response, timeout, 'left')
            return success
        
        try:
            # Send command with timeout
            sock.sendall(cmd.encode('utf-8'))
            
            if wait_response:
                sock.settimeout(timeout or self.COMMAND_TIMEOUT)
                response = sock.recv(1024).decode('utf-8').strip()
                return response == "OK"
            return True
            
        except (socket.timeout, socket.error) as e:
            print(f"Communication error with {target} arm: {e}")
            return False
```

#### Drawing Command Protocols:

**Individual Move Mode** (Maximum Precision):
```python
def _draw_with_individual_moves(self, drawing_points, move_delay):
    for contour_idx, contour in enumerate(drawing_points):
        # Move to start with pen up
        start_x, start_y = contour[0]
        if not self._transition_to_start(start_x, start_y):
            return False
            
        # Lower pen and start drawing
        self.send_pen_down()
        
        # Send each point individually
        for x, y in contour:
            if not self.send_move(x, y):
                return False
            time.sleep(move_delay)
        
        # Lift pen and prepare for next contour
        self.send_pen_up()
        self.send_between_command()
```

**Batch Mode** (High Speed):
```python
def send_batch_moves(self, points, batch_size=3, target='right'):
    # Split points into optimal batch sizes
    for i in range(0, len(points), batch_size):
        batch = points[i:i + batch_size]
        
        # Format coordinates for RAPID string limitations
        coords = []
        for x, y in batch:
            coords.extend([f"{x:.1f}", f"{y:.1f}"])
        
        cmd = f"BATCH,{','.join(coords)}\n"
        
        # Ensure command fits in 80-character RAPID limit
        if len(cmd) > 78:
            # Split oversized batch recursively
            mid = len(batch) // 2
            self.send_batch_moves(batch[:mid], batch_size=mid, target=target)
            self.send_batch_moves(batch[mid:], batch_size=len(batch)-mid, target=target)
        else:
            if not self._send_command(cmd, target=target):
                return False
    return True
```

**Dual-Arm Synchronized Drawing**:
```python
def draw_paths_dual(self, right_actions, left_actions, progress_callback=None):
    import threading
    
    # Shared state for synchronization
    barrier = threading.Barrier(2)
    results = {'right': True, 'left': True}
    points_sent = {'value': 0}
    points_lock = threading.Lock()
    
    def do_action_list(actions, target):
        for idx, action in enumerate(actions):
            if action == 'wait':
                # Synchronization point - wait for other arm
                barrier.wait()
                continue
            elif action is None:
                # No action for this arm - wait for synchronization
                barrier.wait()
                continue
            else:
                # Execute drawing contour
                contour = action
                
                # Collision avoidance protocols
                self._wait_for_peer_retreat(target)
                if self._conflicts_with_peer(target, contour[0]):
                    # Wait for safe positioning
                    time.sleep(self.collision_check_interval)
                
                # Execute drawing sequence
                if not self._transition_to_start(contour[0][0], contour[0][1], target):
                    results[target] = False
                    break
                    
                self.send_pen_down(target=target)
                
                # Draw contour points
                for x, y in contour:
                    if not self.send_move(x, y, target=target):
                        results[target] = False
                        break
                    
                    # Update shared progress counter
                    with points_lock:
                        points_sent['value'] += 1
                        if progress_callback:
                            progress_callback(points_sent['value'])
                
                self.send_pen_up(target=target)
                self.send_between_command(target=target)
                
                # Synchronization point - both arms wait here
                barrier.wait()
    
    # Start both arm threads
    t_right = threading.Thread(target=do_action_list, args=(right_actions, 'right'))
    t_left = threading.Thread(target=do_action_list, args=(left_actions, 'left'))
    
    t_right.start()
    t_left.start()
    t_right.join()
    t_left.join()
    
    return results['right'] and results['left']
```

---

### 6. voice_commands.py - Speech Recognition
**Purpose**: Real-time Polish voice command recognition using VOSK

#### Voice Processing Pipeline:
```python
class VoiceCommandListener:
    def _run(self):
        # Load VOSK Polish model
        model = Model("vosk-model-small-pl-0.22")
        rec = KaldiRecognizer(model, 16000)
        
        # Real-time audio capture
        with sd.RawInputStream(samplerate=16000, blocksize=8000, 
                              dtype='int16', channels=1, 
                              callback=self._audio_callback):
            
            while not self._stop_event.is_set():
                # Get audio data from queue
                data = self._q.get(timeout=0.1)
                
                # Process audio chunk
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").lower().strip()
                    
                    # Check against command list
                    if text in self.commands:
                        print(f"✅ Command recognized: {text}")
                        if self.callback:
                            # Thread-safe callback to GUI
                            self.callback(text)
                    else:
                        print(f"Heard: '{text}' (ignored)")
```

#### Voice Command Mapping:
```python
VOICE_COMMANDS = {
    "połącz": "toggle_connection",      # Connect/disconnect robot
    "start": "start_robot_drawing",     # Begin drawing process  
    "stop": "emergency_stop",           # Emergency stop all operations
    "uchwyć": "get_picture_from_robot", # Capture photo from robot camera
    "portret": "convert_to_face_drawing", # Switch to portrait processing mode
    "karykatura": "convert_to_caricature", # Switch to caricature mode
    "podgląd": "update_robot_preview"   # Show/update drawing preview
}
```

---

### 7. visualizer.py - Real-time Visualization
**Purpose**: Provides matplotlib-based visualization of drawing paths and progress

#### Visualization Components:
```python
class DrawingVisualizer:
    def show_robot_preview(self, drawing_points, use_center_origin=True):
        # Create figure with proper aspect ratio
        max_x, max_y = self.transformer.max_x, self.transformer.max_y
        aspect_ratio = max_x / max_y
        fig_width = 8.0
        fig_height = fig_width / aspect_ratio
        
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        
        # Set coordinate system
        if use_center_origin:
            ax.set_xlim(-max_x/2, max_x/2)
            ax.set_ylim(-max_y/2, max_y/2)
            # Draw center axes
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
        else:
            ax.set_xlim(0, max_x)
            ax.set_ylim(0, max_y)
        
        # Draw workspace boundary
        if use_center_origin:
            boundary = plt.Rectangle((-max_x/2, -max_y/2), max_x, max_y,
                                   fill=False, edgecolor='black', linestyle='--')
        else:
            boundary = plt.Rectangle((0, 0), max_x, max_y,
                                   fill=False, edgecolor='black', linestyle='--')
        ax.add_patch(boundary)
        
        # Draw drawing paths with different colors
        colors = plt.cm.tab20(np.linspace(0, 1, len(drawing_points)))
        
        for i, path in enumerate(drawing_points):
            if path:
                xs, ys = zip(*path)
                ax.plot(xs, ys, color=colors[i], linewidth=1.5,
                       marker='o', markersize=2, alpha=0.8)
        
        # Invert Y-axis to match robot coordinate system
        ax.invert_yaxis()
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_title(f'Robot Drawing Preview ({len(drawing_points)} paths)')
        
        plt.tight_layout()
        plt.show()
        
    def animate_drawing_progress(self, drawing_points, progress_callback=None):
        # Real-time animation of drawing progress
        fig, ax = plt.subplots()
        lines = []
        
        # Initialize empty lines for each path
        for i, path in enumerate(drawing_points):
            line, = ax.plot([], [], linewidth=2)
            lines.append(line)
        
        def update_frame(frame):
            # Update lines based on current progress
            current_point = 0
            for i, (path, line) in enumerate(zip(drawing_points, lines)):
                if frame >= current_point:
                    points_to_show = min(frame - current_point, len(path))
                    if points_to_show > 0:
                        xs, ys = zip(*path[:points_to_show])
                        line.set_data(xs, ys)
                current_point += len(path)
            
            if progress_callback:
                progress_callback(frame, total_points)
            
            return lines
        
        total_points = sum(len(path) for path in drawing_points)
        ani = FuncAnimation(fig, update_frame, frames=total_points,
                          interval=50, blit=True, repeat=False)
        
        plt.show()
        return ani
```

---

## 🔄 Complete System Workflow

### 1. System Initialization
```python
# GUI starts and loads configuration
app = SimpleRobotGUI()
app.config = load_config("robot_gui_config.json")

# Initialize robot drawer with saved settings
app.drawer = RobotDrawer(
    ip=app.config["robot_ip"],
    port=int(app.config["robot_port"]),
    max_x=app.config["max_x"],
    max_y=app.config["max_y"],
    enable_tsp=app.config["enable_tsp"],
    use_center_origin=app.config["use_center_origin"]
)

# Start voice command listener (background thread)
app.voice_listener = VoiceCommandListener(callback=app._on_voice_command)
app.voice_listener.start()
```

### 2. Image Processing Workflow
```python
# User selects image or creates drawing
if drawing_mode == "load":
    image_path = filedialog.askopenfilename()
elif drawing_mode == "draw":
    image_path = create_canvas_drawing()
elif drawing_mode == "text":
    image_path = generate_from_text_prompt()

# Process image with selected settings
success = app.drawer.load_image(
    image_path,
    precision=app.quality_var.get(),
    enable_tsp=app.enable_tsp.get(),
    detection_method=app.detection_method.get()
)

# Update GUI with preview
if success:
    app.update_preview_display()
    app.enable_drawing_buttons()
```

### 3. Robot Connection & Drawing
```python
# Connect to robot
if app.drawer.connect():
    app.update_connection_status("Connected")
    
    # Configure robot based on coordinate system
    if app.use_center_origin.get():
        start_command = "START"  # Center-based coordinates
    else:
        start_command = "START_CORNER"  # Corner-based coordinates
    
    # Execute drawing
    if app.dual_arm_mode.get():
        # Dual-arm drawing with collision avoidance
        success = app.drawer.draw_dual(
            buffer_radius=app.forbidden_buffer_var.get(),
            progress_callback=app.update_progress
        )
    else:
        # Single-arm drawing
        success = app.drawer.draw(
            progress_callback=app.update_progress
        )
    
    # Handle completion
    if success:
        app.show_completion_message()
    else:
        app.handle_drawing_error()
```

### 4. Error Handling & Recovery
```python
def handle_communication_error(self, error):
    print(f"Communication error: {error}")
    
    # Attempt reconnection
    for attempt in range(3):
        try:
            self.drawer.disconnect()
            time.sleep(1.0)
            if self.drawer.connect():
                print(f"Reconnected on attempt {attempt + 1}")
                return True
        except Exception as e:
            print(f"Reconnection attempt {attempt + 1} failed: {e}")
    
    # Fall back to safe state
    self.update_connection_status("Connection Lost")
    self.disable_drawing_buttons()
    return False
    
def emergency_stop(self):
    """Immediate system shutdown with safety protocols"""
    self.drawing_active = False
    
    # Stop robot operations
    try:
        self.drawer.robot.send_pen_up(target='both')
        self.drawer.robot.send_stop(target='both')
    except Exception:
        pass  # Best effort - don't raise exceptions during emergency
    
    # Disconnect safely
    try:
        self.drawer.disconnect()
    except Exception:
        pass
    
    # Update GUI state
    self.update_connection_status("Emergency Stop")
    self.reset_drawing_interface()
    print("🛑 Emergency stop completed")
```

---

## 📊 Performance Optimization Techniques

### 1. Image Processing Optimizations
```python
# Memory-efficient image processing
def optimize_image_processing(image_path):
    # Process in chunks for large images
    image = cv2.imread(image_path)
    
    # Downscale if image is too large (>2MB)
    if image.nbytes > 2 * 1024 * 1024:
        scale_factor = 0.5
        image = cv2.resize(image, None, fx=scale_factor, fy=scale_factor)
        print(f"Downscaled large image by {scale_factor}")
    
    return image

# Adaptive precision based on image complexity
def auto_select_precision(contour_count):
    if contour_count > 1000:
        return "low"      # Fast processing for complex images
    elif contour_count > 500:
        return "medium"   # Balanced for moderate complexity
    else:
        return "high"     # Maximum quality for simple images
```

### 2. Network Communication Optimizations
```python
# Dynamic batch sizing based on coordinate complexity
def calculate_optimal_batch_size(points):
    # Analyze coordinate variation to determine optimal batch size
    coord_variance = calculate_coordinate_variance(points)
    
    if coord_variance < 10.0:
        return 6  # Low variation - use larger batches
    elif coord_variance < 50.0:
        return 4  # Medium variation - balanced batches
    else:
        return 2  # High variation - smaller batches for precision

# Connection pooling for dual-arm operations
class ConnectionPool:
    def __init__(self):
        self.connections = {}
        self.connection_lock = threading.Lock()
    
    def get_connection(self, target):
        with self.connection_lock:
            if target not in self.connections:
                self.connections[target] = create_socket_connection(target)
            return self.connections[target]
```

### 3. Memory Management
```python
# Automatic garbage collection for large operations
def process_with_memory_management(operation):
    import gc
    
    try:
        result = operation()
        
        # Force garbage collection after memory-intensive operations
        gc.collect()
        
        return result
    except MemoryError:
        # Clear caches and retry once
        clear_image_cache()
        gc.collect()
        return operation()

# Image cache management
class ImageCache:
    def __init__(self, max_size_mb=100):
        self.cache = {}
        self.max_size = max_size_mb * 1024 * 1024
        self.current_size = 0
    
    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        return None
    
    def put(self, key, image_data):
        size = image_data.nbytes
        
        # Evict old entries if needed
        while self.current_size + size > self.max_size and self.cache:
            oldest_key = next(iter(self.cache))
            self.evict(oldest_key)
        
        self.cache[key] = image_data
        self.current_size += size
```

---

## 🛡️ Safety Protocols Implementation

### 1. Collision Avoidance (Dual-Arm)
```python
def _conflicts_with_peer(self, target, point):
    """Check if point conflicts with peer arm's current position"""
    try:
        peer_target = 'left' if target == 'right' else 'right'
        
        # Get peer's last known position
        peer_pos = self.last_positions.get(peer_target)
        if not peer_pos:
            return False  # No conflict if peer position unknown
        
        # Calculate distance between positions
        distance = math.sqrt((point[0] - peer_pos[0])**2 + 
                           (point[1] - peer_pos[1])**2)
        
        # Check against collision radius
        return distance < self.collision_radius
        
    except Exception:
        return False  # Assume no conflict on error

def _wait_for_peer_retreat(self, target):
    """Wait for peer arm to complete retreat after contour"""
    retreat_delay = getattr(self, 'post_retreat_delay', 0.7)
    
    peer_target = 'left' if target == 'right' else 'right'
    last_retreat = self.last_retreat_times.get(peer_target, 0)
    
    # Calculate time since peer's last retreat
    time_since_retreat = time.time() - last_retreat
    
    if time_since_retreat < retreat_delay:
        wait_time = retreat_delay - time_since_retreat
        print(f"[{target}] Waiting {wait_time:.2f}s for {peer_target} retreat")
        time.sleep(wait_time)
```

### 2. Network Error Recovery
```python
def robust_send_command(self, cmd, max_retries=3, target='right'):
    """Send command with automatic retry and error recovery"""
    for attempt in range(max_retries):
        try:
            if self._send_command(cmd, target=target):
                return True
                
        except socket.timeout:
            print(f"Timeout on attempt {attempt + 1}, retrying...")
            
        except socket.error as e:
            print(f"Socket error on attempt {attempt + 1}: {e}")
            
            # Attempt to reconnect on socket errors
            if attempt < max_retries - 1:
                try:
                    self.disconnect()
                    time.sleep(1.0)
                    self.connect()
                except Exception:
                    pass  # Continue to next retry
        
        except Exception as e:
            print(f"Unexpected error on attempt {attempt + 1}: {e}")
        
        # Exponential backoff between retries
        if attempt < max_retries - 1:
            time.sleep(0.5 * (2 ** attempt))
    
    # All retries failed
    print(f"Command failed after {max_retries} attempts: {cmd}")
    return False
```

### 3. Data Validation
```python
def validate_drawing_data(self, drawing_points):
    """Comprehensive validation of drawing data before execution"""
    errors = []
    
    # Check basic structure
    if not drawing_points or not isinstance(drawing_points, list):
        errors.append("Invalid drawing data structure")
        return errors
    
    # Validate each contour
    for i, contour in enumerate(drawing_points):
        if not contour:
            errors.append(f"Empty contour at index {i}")
            continue
            
        # Validate coordinate ranges
        for j, point in enumerate(contour):
            if len(point) != 2:
                errors.append(f"Invalid point format at contour {i}, point {j}")
                continue
                
            x, y = point
            
            # Check workspace bounds
            if not (0 <= x <= self.max_x):
                errors.append(f"X coordinate {x} out of bounds at contour {i}, point {j}")
            
            if not (0 <= y <= self.max_y):
                errors.append(f"Y coordinate {y} out of bounds at contour {i}, point {j}")
            
            # Check for reasonable coordinate values
            if abs(x) > 1000 or abs(y) > 1000:
                errors.append(f"Suspicious coordinate values at contour {i}, point {j}: ({x}, {y})")
    
    return errors
```

---

This technical implementation guide provides the detailed "how it works" documentation that complements the high-level technical documentation. It shows the actual code patterns, algorithms, and implementation details that make the system function reliably in production.

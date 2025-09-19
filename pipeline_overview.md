# Robot Drawing System Pipeline Overview - Extremely Detailed

This document provides an extremely detailed, step-by-step breakdown of the entire function call pipeline in the Robot Drawing System project, from user interaction through robot execution completion.

## System Architecture Overview

The system consists of 6 main modules:
- `simple_gui.py`: Main GUI interface and orchestration
- `robot_drawer.py`: High-level drawing orchestration
- `image_processor.py`: Image processing and edge detection
- `coordinate_transformer.py`: Coordinate transformation and optimization
- `robot_communication.py`: Low-level robot TCP/IP communication
- `voice_commands.py`: Voice recognition and command processing
- `visualizer.py`: Data visualization and plotting

## Detailed Pipeline Flow

### Phase 1: Application Initialization

#### GUI Startup (`simple_gui.py`)
1. `SimpleRobotGUI.__init__()`:
   - Creates Tkinter root window
   - Loads configuration from `robot_gui_config.json` via `_load_config()`
   - Initializes `RobotDrawer` instance with default parameters (290x210mm workspace, center origin, TSP enabled)
   - Sets up voice command listener with `VoiceCommandListener`
   - Calls `create_simple_interface()` to build UI
   - Starts connection status update loop with `root.after(100, self._update_connection_display)`

#### Voice System Initialization (`voice_commands.py`)
2. `VoiceCommandListener.__init__()`:
   - Sets up VOSK model path (handles both development and packaged environments)
   - Initializes audio queue and threading components
   - Prepares callback system for recognized commands

### Phase 2: Image Acquisition

#### Camera/Image Input Methods

**Method A: Robot Camera (`simple_gui.py`)**
1. User clicks "1. TAKE PICTURE" → `get_picture_from_robot()`
2. `get_picture_from_robot()` → `ready_robot_without_camera()` → `RobotController.start_without_camera()`
3. `RobotController.start_without_camera()` → `_send_command("READY\n")` to robot
4. Robot responds with "OK" after initialization
5. `get_picture_from_robot()` → `_get_picture_thread()` (background thread)
6. `_get_picture_thread()` → `RobotController.send_start()` → `_send_command("START\n")` or `START_CORNER\n` based on coordinate system
7. Robot performs positioning and sends "OK"
8. `RobotController.send_start()` returns success
9. `_get_picture_thread()` → gets picture from camera `robot_ftp_downloader.py`
10. `_load_robot_image()` processes downloaded image
11. `auto_process_image()` → `_start_auto_processing()` → `process_image()`

**Method B: File Upload (`simple_gui.py`)**
1. User clicks file selection → `browse_image()`
2. `filedialog.askopenfilename()` opens file picker
3. `browse_image()` → `load_preview_image()` → `PIL.Image.open()` loads image
4. `load_preview_image()` → `ImageTk.PhotoImage()` creates Tkinter-compatible image
5. `preview_label.configure(image=photo_image)` displays preview
6. `auto_process_image()` → `_start_auto_processing()` → `process_image()`

**Method C: Text-to-Image Generation (`simple_gui.py`)**
1. User enters text → `quick_text_generate()` → `_text_generation_thread()` (background)
2. `_text_generation_thread()` → AI image generation (implementation not shown)
3. Success → `_text_generation_success()` → `_auto_process_generated_image()`

**Method D: Canvas Drawing (`simple_gui.py`)**
1. User draws on canvas → mouse events trigger `start_canvas_drawing()`, `draw_on_canvas()`, `stop_canvas_drawing()`
2. `save_drawing()` → `PIL.ImageGrab.grab()` captures canvas
3. `use_drawing()` → `load_preview_image()` processes captured image

### Phase 3: Image Processing Pipeline

#### Main Processing (`simple_gui.py` → `robot_drawer.py` → `image_processor.py`)
1. `process_image()` → `_process_thread()` (background processing)
2. `_process_thread()` → `RobotDrawer.load_image()` with current settings:
   - `precision`: "high", "medium", "low", etc.
   - `enable_tsp`: Boolean from GUI checkbox
   - `detection_method`: "canny", "threshold", "adaptive"
   - `logo_settings`: Dictionary with enabled/corner/size
   - `protect_logo`: True for logo processing

#### Image Processing Details (`image_processor.py`)
3. `ImageProcessor.load_and_process_image()` → `extract_edge_following_path()`
4. `extract_edge_following_path()`:
   - `cv2.imread()` loads image
   - `cv2.rotate(ROTATE_180)` flips image 180°
   - `cv2.mirror` mirrors it horizontally
   - **Border Padding**: `cv2.copyMakeBorder()` adds white padding (unless `protect_logo=True`)
   - `cv2.cvtColor(BGR2GRAY)` converts to grayscale
   - `cv2.GaussianBlur()` + `cv2.medianBlur()` noise reduction

5. **Edge Detection Methods**:
   - **Canny**: `cv2.Canny()` → `_thin_edges()` morphological thinning → `cv2.morphologyEx(CLOSE)`
   - **Threshold**: `cv2.threshold(THRESH_BINARY + THRESH_OTSU)`
   - **Adaptive**: `cv2.adaptiveThreshold(ADAPTIVE_THRESH_GAUSSIAN_C)` with precision-based parameters

6. **Contour Extraction**:
   - `cv2.findContours(RETR_LIST, CHAIN_APPROX_SIMPLE)` finds contours
   - **Filtering**: Remove contours < `MIN_CONTOUR_LENGTH` (10) or < area threshold (adaptive)
   - **Border Filtering**: `_is_border_contour()` removes contours touching image edges (unless `protect_logo=True`)

7. **Contour Simplification**:
   - `cv2.approxPolyDP()` with adaptive epsilon based on precision and image properties
   - Resolution-based factor: 1000000px → 3.0, 500000px → 2.0, etc.
   - Scale factor normalization: `min(2.0, max(0.5, scale * 1000))`
   - Minimum epsilon: 0.5px, Maximum: perimeter * 0.1

8. **Path Optimization** (if `enable_tsp=True`):
   - Contours sorted by length (longest first)
   - Returns `{'contours': simplified_paths, 'image_shape': edges.shape, 'simplification_factor': factor}`

#### Coordinate Transformation (`coordinate_transformer.py`)
9. `CoordinateTransformer.contours_to_robot_coordinates()`:
   - Calculates scale: `min(scale_x, scale_y)` where `scale_x = effective_x / width`
   - `effective_x = max_x - 2*margin_x`, `effective_y = max_y - 2*margin_y`
   - Centers image: `final_offset_x = effective_offset_x + margin_x`
   - **Coordinate System Conversion**:
     - **Center Origin**: `robot_x = (x * scale) + final_offset_x - (max_x / 2)`
     - **Corner Origin**: `robot_x = (x * scale) + final_offset_x`
     - Y-axis flip: `robot_y = ((height - y) * scale) + final_offset_y - (max_y / 2)`

10. **Path Smoothing** (if enabled):
    - **Bezier**: `_smooth_path_bezier()` with quadratic curves
    - **Catmull-Rom**: `_smooth_path_catmull_rom()` with cubic splines

11. **Point Filtering**: `_filter_min_distance()` removes points closer than `MIN_DISTANCE_THRESHOLD` (1.0mm)

#### Logo Processing (if enabled)
13. `RobotDrawer.generate_logo_coordinates()`:
   - Loads `logo_short.png`
   - `ImageProcessor.extract_edge_following_path()` with `protect_logo=True`
   - Scales logo to `size_mm` while maintaining aspect ratio
   - Positions at top-right corner with 5mm margin
   - **Logo Flipping**: `x = logo_x_offset + logo_width_mm - (px * scale_factor)` (horizontal mirror)
   - Coordinate system conversion (center/corner origin)
   - Minimum distance filtering
   - Appends logo contours to main drawing points

### Phase 4: Style Processing (Portrait/Carricature)

#### Portrait Mode (`simple_gui.py` → `convert_to_lineart.py`)
1. User selects portrait → `set_style_and_convert("portrait")`
2. `convert_to_face_drawing()` → `_face_drawing_thread()` (background)
3. `_face_drawing_thread()` → AI face drawing generation
4. Success → `_face_drawing_success()` → `load_preview_image()` → `auto_process_image()`

#### Caricature Mode (`simple_gui.py`→ `convert_to_lineart.py)
1. User selects caricature → `set_style_and_convert("caricature")`
2. `convert_to_caricature()` → `_caricature_thread()` (background)
3. `_caricature_thread()` → AI caricature generation 
4. Success → `_caricature_success()` → `load_preview_image()` → `auto_process_image()`

### Phase 5: Robot Connection and Preparation

#### Connection Management (`simple_gui.py` → `robot_communication.py`)
1. User clicks connection toggle → `toggle_connection()`
2. `toggle_connection()` → `_connect_thread()` (background)
3. `_connect_thread()` → `RobotController.connect()`
4. `RobotController.connect()`:
   - `socket.socket(AF_INET, SOCK_STREAM)` creates sockets
   - `socket.connect((ip, port))` connects to port 1025 (right arm)
   - `socket.connect((ip, port_l))` connects to port 1026 (left arm)
   - Returns success status

#### Robot Initialization
5. `RobotController.send_start()` or `start_without_camera()`:
   - Sends "START\n" or "START_CORNER\n" based on coordinate system
   - Robot performs: positioning
   - Robot responds "OK" after ~2 seconds

### Phase 6: Drawing Execution

#### Single-Arm Drawing (`simple_gui.py` → `robot_drawer.py` → `robot_communication.py`)
1. User clicks "4. START DRAWING" → `start_drawing()` → `start_robot_drawing()`
2. `start_robot_drawing()` → `RobotDrawer.draw()` with progress callback
3. `RobotDrawer.draw()` → `RobotController.draw_paths()` with batch mode
4. `RobotController.draw_paths()` → `_draw_with_ultra_fast_mode()` (if batch enabled)

#### Batch Drawing (`robot_communication.py`)
5. `_draw_with_ultra_fast_mode()`:
   - **Pen Management**: `send_pen_up()` (already up), `time.sleep(0.02)`
   - **Per Contour Loop**:
     - `should_stop()` check for emergency stop
     - `_transition_to_start()`: Horizontal U-shape movement
       - `send_between_command("RETREAT\n")` moves back horizontally (±80mm X)
       - `send_move()` to Y-level of next contour start
       - `send_move()` forward to actual start position
     - `send_pen_down()`, `time.sleep(0.02)`
     - `send_move()` to first point with pen down
     - **Batch Processing**: `send_batch_moves_ultra_fast()` for remaining points
       - Groups points into batches (dynamic sizing based on coordinate length)
       - `send_batch_moves()` → `_send_command(f"BATCH,{coords}\n")`
       - 80-character command limit handling with batch splitting
     - `send_pen_up()`, `send_between_command(next_start)` for retreat
   - **Progress Tracking**: Updates via `progress_callback(current_batch, total_batches, points_sent, total_points)`

#### Dual-Arm Drawing (`robot_drawer.py` → `robot_communication.py`)
6. `RobotDrawer.draw_dual()` (alternative path):
   - `master_slave_assign_contours()` assigns contours to right/left arms
   - Creates forbidden zones around master contour with circular buffers + tail extension
   - `RobotController.draw_paths_dual()` with threading
   - **Threaded Execution**: `t_right` and `t_left` threads with `threading.Barrier(2)` synchronization
   - **Per-Step Processing**:
     - Collision avoidance: `_conflicts_with_peer()`, `_wait_for_peer_retreat()`
     - `_transition_to_start()` with side-specific X offsets
     - Simultaneous contour drawing with barrier synchronization
     - WAIT commands for synchronization between arms

### Phase 7: Voice Command Processing

#### Voice Recognition (`voice_commands.py`)
1. `VoiceCommandListener.start()` → `_run()` in background thread
2. `sd.RawInputStream()` captures audio at 16kHz
3. `KaldiRecognizer.AcceptWaveform()` processes audio chunks
4. `json.loads(result)` extracts recognized text
5. If text in `commands` list → `callback(text)`

#### Command Dispatch (`simple_gui.py`)
6. `_on_voice_command()` → `_handle_command()` (dispatched to main thread)
7. **Command Mapping**:
   - "połącz" → `toggle_connection()`
   - "start" → `start_drawing()`
   - "stop" → `emergency_stop()`
   - "akcja" → `get_picture_from_robot()`
   - "kamera" → `show_camera_preview()`
   - "portret" → portrait selection
   - "karykatura" → caricature selection
   - "podgląd" → `open_detailed_path_window()`

### Phase 8: Visualization and Monitoring

#### Preview Systems (`visualizer.py`)
1. `DrawingVisualizer.plot_preview()`:
   - `matplotlib.pyplot.figure()` creates plot
   - Plots each contour with different colors
   - Sets up centered coordinate system: `xlim(-max_x/2, max_x/2)`
   - `invert_yaxis()` so (0,0) is top-left
   - Draws workspace border and center markers

2. `show_processing_steps()`:
   - Three-panel plot: Original → Edges → Robot Preview
   - `cv2.cvtColor(BGR2RGB)` for proper color display

#### Real-time Progress (`simple_gui.py`)
3. Progress callbacks update:
   - `bottom_progress_bar['value']` for visual progress
   - `progress_indicator` text updates
   - Status messages in `status_text`

### Phase 9: Error Handling and Cleanup

#### Error Scenarios
1. **Connection Failures**: `RobotController.connect()` → `_connection_failed()` → UI updates
2. **Processing Errors**: `_process_failed()` → error dialogs
3. **Drawing Errors**: `_draw_failed()` → cleanup commands
4. **Emergency Stop**: `emergency_stop()` → `RobotController.send_stop()` on both arms

#### Cleanup Operations
1. `SimpleRobotGUI._on_close()`:
   - `VoiceCommandListener.stop()`
   - `RobotController.disconnect()` → `send_stop()` → `socket.close()`
   - Configuration saving via `_save_config()`

## Configuration Management

#### Settings Persistence (`simple_gui.py`)
- `_load_config()`: JSON loading with error handling
- `_save_config()`: Serializes current GUI state to `robot_gui_config.json`
- Settings include: robot IP/port, camera index, coordinate system, margins, quality, detection method, TSP, batch mode, logo settings, etc.

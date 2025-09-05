# 🤖 Robot Drawing System - Comprehensive Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Design](#ar├── 🔊 AI & External Services
│   ├── voice_commands.py          # Voice recognition (VOSK Polish)
│   ├── convert_to_lineart.py      # OpenAI DALL-E integration
│   └── robot_ftp_downloader.py    # Local camera capture utility
│
├── 🎬 Animation & Helpers
│   ├── matplotlib_anim_helper.py      # Path-by-path animation
│   └── matplotlib_anim_point_helper.py # Point-by-point animation
│
├── 📊 Data & Configuration
│   ├── robot_gui_config.json      # Persistent configuration
│   ├── image.png / out.png        # Sample/temp images
│   ├── logo_short.png             # Logo overlay file
│   └── line_art_catalog/          # Generated artwork archive
│       ├── 20250901_153825_minimalist/
│       ├── 20250902_131242_caricature/
│       └── ... (timestamped folders)
│
├── 🤖 RAPID Robot Programs
│   ├── Right_arm.mod             # ABB RAPID code for right arm
│   └── Left_arm.mod              # ABB RAPID code for left arm
│
├── 🔊 Voice Recognition Model
│   └── vosk-model-small-pl-0.22/  # Polish speech recognition
│       ├── README
│       └── am/ (acoustic model files)
│
└── 📚 Documentation
    └── COMPREHENSIVE_DOCUMENTATION.md # This file)
3. [Module Documentation](#module-documentation)
4. [System Requirements](#system-requirements)
5. [Installation & Setup](#installation--setup)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Usage Examples](#usage-examples)
9. [Troubleshooting](#troubleshooting)
10. [Development Guide](#development-guide)

---

## Project Overview

The **Robot Drawing System** is a comprehensive Python-based application that enables ABB YuMi IRB 14000 dual-arm industrial robots to create artistic drawings from digital images. The system provides a complete pipeline from image processing to robot control, featuring an intuitive GUI and support for multiple input methods.

### 🎯 Key Features

- **Multi-Input Support**: Load images, draw on canvas, or generate from text prompts
- **Dual-Arm Operation**: Simultaneous operation of both robot arms with collision avoidance
- **Advanced Image Processing**: Edge detection, contour extraction, and path optimization
- **Real-time Visualization**: Preview and animation of drawing paths
- **Voice Control**: Polish voice commands for hands-free operation
- **AI Integration**: Text-to-image generation using OpenAI's DALL-E
- **Quality Controls**: Multiple precision levels and optimization algorithms

### 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Simple GUI    │────│  Robot Drawer   │────│ Robot Controller│
│  (User Inter-   │    │  (Orchestrator) │    │ (TCP/IP Comm)  │
│   face Layer)   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐             │
         │              │ Image Processor │             │
         │              │ (Edge Detection)│             │
         │              └─────────────────┘             │
         │                       │                       │
         │              ┌─────────────────┐             │
         │              │  Coordinate     │             │
         │              │  Transformer    │             │
         │              │ (Path Smoothing)│             │
         │              └─────────────────┘             │
         │                                               │
         │              ┌─────────────────┐             │
         └──────────────│   Visualizer    │             │
                        │ (Preview/Plot)  │             │
                        └─────────────────┘             │
                                                        │
┌─────────────────┐    ┌─────────────────┐             │
│ Voice Commands  │    │  Convert to     │             │
│ (VOSK Polish)   │    │  Line Art       │             │
│                 │    │ (OpenAI API)    │             │
└─────────────────┘    └─────────────────┘             │
                                                        │
                        ┌─────────────────┐             │
                        │ ABB YuMi Robot  │◄────────────┘
                        │  (RAPID Code)   │
                        │ Port 1025/1026  │
                        └─────────────────┘
```

---

## Architecture & Design

### 📋 Design Principles

1. **Modular Architecture**: Each component handles a specific responsibility
2. **Clean Separation**: GUI, processing, and robot control are loosely coupled
3. **Error Handling**: Comprehensive error handling and recovery mechanisms
4. **Real-time Feedback**: Progress tracking and status updates throughout operations
5. **Safety First**: Collision avoidance and workspace bounds checking
6. **Performance Optimization**: Batch processing and optimized path algorithms

### 🔧 Core Components

#### 1. **SimpleRobotGUI** (`simple_gui.py`)
- **Purpose**: Main user interface and application entry point
- **Responsibilities**: 
  - User interaction management
  - Configuration persistence
  - Drawing canvas functionality
  - Progress tracking and status display
  - Voice command integration

#### 2. **RobotDrawer** (`robot_drawer.py`)
- **Purpose**: Main orchestrator class
- **Responsibilities**:
  - Coordinates all subsystems
  - Manages drawing workflow
  - Handles dual-arm mode logic
  - Provides simplified API for GUI

#### 3. **RobotController** (`robot_communication.py`)
- **Purpose**: TCP/IP communication with ABB robots
- **Responsibilities**:
  - Socket management and connection handling
  - Command sending and response validation
  - Batch processing for performance
  - Dual-arm synchronization

#### 4. **ImageProcessor** (`image_processor.py`)
- **Purpose**: Image analysis and path extraction
- **Responsibilities**:
  - Edge detection (Canny, Threshold, Adaptive)
  - Contour extraction and simplification
  - Logo placement and protection

#### 5. **CoordinateTransformer** (`coordinate_transformer.py`)
- **Purpose**: Coordinate system management
- **Responsibilities**:
  - Image-to-robot coordinate conversion
  - Path smoothing (Bézier, Catmull-Rom)
  - Margin handling and bounds checking
  - Dual-arm path assignment

#### 6. **DrawingVisualizer** (`visualizer.py`)
- **Purpose**: Preview and visualization
- **Responsibilities**:
  - Matplotlib-based plotting
  - Real-time animation
  - Processing step visualization
  - Coordinate system display

---

## Module Documentation

### 📁 File Structure

```
moje_skrypty/
├── 🎨 Main Application
│   ├── simple_gui.py              # Main GUI application
│   └── robot_drawer.py            # Core orchestrator
│
├── 🤖 Robot Control
│   ├── robot_communication.py     # TCP/IP communication
│   ├── Right_arm.mod             # RAPID code for right arm
│   └── Left_arm.mod              # RAPID code for left arm
│
├── 🖼️ Image Processing
│   ├── image_processor.py         # Edge detection & contour extraction
│   ├── coordinate_transformer.py  # Coordinate transformation
│   └── visualizer.py             # Plotting and visualization
│
├── 🔊 AI & External Services
│   ├── voice_commands.py          # Voice recognition (VOSK)
│   ├── convert_to_lineart.py      # OpenAI DALL-E integration
│   └── robot_ftp_downloader.py    # Camera capture utility
│
├── 🎬 Animation & Helpers
│   ├── matplotlib_anim_helper.py      # Path-by-path animation
│   └── matplotlib_anim_point_helper.py # Point-by-point animation
│
├── 📊 Data & Configuration
│   ├── robot_gui_config.json      # Persistent configuration
│   ├── image.png                  # Sample/temp images
│   └── line_art_catalog/          # Generated artwork archive
│
└── 📚 Documentation
    ├── USER_MANUAL.md             # User guide
    ├── QUICK_REFERENCE.md         # Quick start guide
    └── COMPREHENSIVE_DOCUMENTATION.md # This file
```

### 📦 Dependencies

```python
# Core GUI and Image Processing
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import cv2
import numpy as np

# Scientific Computing and Visualization
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation

# Coordinate Processing
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

# Network and System
import socket
import threading
import queue
import time
import os
import json

# Voice Recognition
import sounddevice as sd
from vosk import Model, KaldiRecognizer

# AI Integration
from openai import OpenAI
```

---

## System Requirements

### 💻 Hardware Requirements

- **OS**: Windows 10/11 (64-bit)
- **Network**: Ethernet
- **Camera**: Any usb camera/laptop
- **Audio**: Microphone  for voice commands

### 🤖 Robot Requirements

#### ABB YuMi IRB 14000
- **Controller**: IRC5 with RobotStudio
- **Software**: RobotWare 6.0 or higher
- **Network**: TCP/IP connectivity
- **Workspace**: Minimum 300mm × 220mm drawing area
- **Tools**: Pen/marker holding gripper

#### Network Configuration
- **Robot IP**: 192.168.125.1 (default)
- **Right Arm Port**: 1025
- **Left Arm Port**: 1026
- **Communication**: TCP socket protocol

---

## Installation & Setup

### 🔧 Python Environment Setup

1. **Install Python 3.8+**
   ```bash
   python --version  # Verify installation
   ```

2. **Install Required Packages**
   ```bash
   pip install tkinter pillow opencv-python matplotlib numpy shapely
   pip install sounddevice vosk openai
   ```

3. **Download VOSK Model** (for Polish voice commands)
   ```bash
   # Download vosk-model-small-pl-0.22.zip
   # Extract to project directory
   ```

### 🤖 Robot Setup

1. **Load RAPID Modules**
   - Copy `Right_arm.mod` to right arm controller
   - Copy `Left_arm.mod` to left arm controller
   - Set auto-start in RobotStudio
   - Add your points and tools not inlcuded in this repository

2. **Network Configuration**
   ```
   Robot IP: 192.168.125.1
   ```

3. **Workspace Calibration**
   - Define drawing coordinate system
   - Set pen tool TCP (Tool Center Point)
   - Calibrate work object for drawing surface

### 🚀 First Run

1. **Start the Application**
   ```bash
   cd "path_to_project"
   python simple_gui.py
   ```

2. **Verify Connection**
   - Click "🔌 Connect Robot"
   - Check status indicator turns green
   - Test with simple shape from templates

---

## Configuration

### ⚙️ Configuration File (`robot_gui_config.json`)

The system automatically saves and loads configuration settings:

```json
{
  "robot_ip": "192.168.125.1",
  "robot_port": "1025",
  "robot_port_l": "1026",
  "use_center_origin": true,
  "quality_var": "high",
  "detection_method": "threshold",
  "enable_tsp": true,
  "use_batch_mode": true,
  "dual_arm_mode": false,
  "max_x": 290,
  "max_y": 210,
  "margin_x": 10,
  "margin_y": 10,
  "enable_logo": false,
  "logo_size": 20,
  "enable_frame_filtering": false,
  "forbidden_buffer": 40,
  "drawing_mode": "load",
  "brush_size": 5
}
```

### 🎛️ Key Settings Explained

#### Robot Connection
- **robot_ip**: IP address of robot controller
- **robot_port**: Right arm communication port
- **robot_port_l**: Left arm communication port (dual-arm mode)

#### Drawing Parameters
- **max_x/max_y**: Robot workspace dimensions (mm)
- **margin_x/margin_y**: Safety margins from workspace edges (mm)
- **use_center_origin**: Coordinate system origin (center vs corner)

#### Processing Options
- **quality_var**: Edge detection precision ("highest", "high", "medium", "low")
- **detection_method**: Algorithm ("threshold", "canny", "adaptive")
- **enable_tsp**: Traveling Salesman Problem optimization
- **use_batch_mode**: Batch command sending for performance

#### Dual-Arm Mode
- **dual_arm_mode**: Enable simultaneous dual-arm operation
- **forbidden_buffer**: Collision avoidance buffer radius (mm)

---

## API Reference

### 🔌 RobotDrawer Class

Main orchestrator providing simplified API for robot drawing operations.

#### Constructor
```python
RobotDrawer(ip="192.168.125.1", port=1025, port_l=None,
           max_x=290, max_y=210, enable_smoothing=True, 
           smoothing_type="bezier", enable_tsp=True, 
           use_center_origin=True, margin_x=10, margin_y=10)
```

#### Core Methods

##### Image Loading and Processing
```python
def load_image(self, image_path, precision="high", enable_tsp=None, 
               detection_method="threshold", logo_settings=None, 
               protect_logo=True)
```
- Loads and processes image for robot drawing
- Returns: Boolean success status

##### Robot Connection
```python
def connect(self) -> bool
def disconnect(self) -> None
def set_coordinate_system(self, use_center_origin: bool) -> None
```

##### Drawing Execution
```python
def draw(self, progress_callback=None) -> bool
def draw_dual(self, buffer_radius=40, buffer_x=10, buffer_y=70, 
              progress_callback=None) -> bool
```

##### Visualization
```python
def preview_points(self, max_display=50) -> None
def plot_preview(self) -> None
def show_processing_steps(self, image_path) -> None
```

### 🤖 RobotController Class

Low-level robot communication and control.

#### Connection Management
```python
def connect(self) -> bool
def disconnect(self) -> None
```

#### Movement Commands
```python
def send_move(self, x: float, y: float, wait_response=True, target='right') -> bool
def send_batch_moves(self, points: list, batch_size=3, max_batch_size=6, target='right') -> bool
```

#### Tool Control
```python
def send_pen_up(self, target='right') -> bool
def send_pen_down(self, target='right') -> bool
def send_start(self) -> bool
def send_stop(self, target='right') -> bool
```

#### Dual-Arm Operations
```python
def draw_paths_dual(self, right_actions: list, left_actions: list, 
                   move_delay=0.02, use_batching=None, batch_size=8, 
                   progress_callback=None) -> bool
```

### 🖼️ ImageProcessor Class

Image analysis and path extraction.

#### Processing Methods
```python
def load_and_process_image(self, image_path: str, precision="high", 
                          enable_tsp=None, detection_method="threshold", 
                          protect_logo=False) -> list
```

#### Detection Algorithms
- **Threshold**: Binary thresholding for clean line art
- **Canny**: Edge detection for photographic images  
- **Adaptive**: Adaptive thresholding for varying lighting

### 🔄 CoordinateTransformer Class

Coordinate system management and path optimization.

#### Transformation Methods
```python
def transform_paths(self, contours: list, image_shape: tuple) -> list
def smooth_path(self, path: list, method="bezier") -> list
```

#### Coordinate Systems
- **Center Origin**: (0,0) at drawing area center
- **Corner Origin**: (0,0) at top-left corner

#### Dual-Arm Path Assignment
The transformer includes sophisticated algorithms for assigning contours to robot arms:

```python
def master_slave_assign_contours(contours, master, buffer_radius=40, buffer_x=10, buffer_y=70):
    """
    Assigns contours to master and slave arms with collision avoidance.
    Uses shapely polygons for precise overlap detection.
    """
```

#### Features:
- **Collision Avoidance**: Circular buffer zones around active arm
- **Forbidden Area Handling**: Left arm cannot reach (0,0)-(130,40) zone  
- **Optimized Assignment**: Prioritizes contours by position for each arm
- **Safety Extensions**: Tail regions prevent workspace conflicts

---

### 🤖 ABB RAPID Robot Programs

The system includes RAPID modules for both robot arms:

#### Right_arm.mod (Port 1025)
- **Module**: DrawingModule
- **Main Procedure**: Initializes server on port 1025
- **Commands Supported**:
  - `START` / `START_CORNER` - Initialize coordinate system
  - `MOVE,x,y` - Move to coordinates
  - `BATCH,x1,y1,x2,y2,...` - Batch movement (up to 15 points)
  - `PEN_UP` / `PEN_DOWN` - Tool control
  - `STOP` - Return to safe position

#### Left_arm.mod (Port 1026)  
- **Module**: Module1
- **Main Procedure**: Initializes server on port 1026
- **Forbidden Zone**: Cannot reach coordinates (0,0) to (130,40) mm
- **Same command set** as right arm

#### Key RAPID Parameters:
```rapid
! Z-axis positions for pen control
CONST num z_down := 0;         ! Pen touching paper
CONST num z_up := -10;         ! Pen lifted

! Movement speeds (optimized for quality)
CONST speeddata move_speed := v1500;   ! Drawing speed
CONST speeddata fast_speed := v1500;   ! Transition speed

! Precision settings
CONST zonedata move_zone := z0;        ! Precise positioning
CONST num max_batch_size := 30;       ! Batch performance
```

#### Coordinate Systems:
- **Center Origin**: (0,0) at drawing area center
- **Corner Origin**: (0,0) at top-left corner
- **Workspace**: 290mm × 210mm (A4 size)
- **Safety Margins**: 10mm default from edges

---

## Usage Examples

### 🎨 Basic Drawing Workflow

```python
from robot_drawer import RobotDrawer

# Initialize robot drawer
drawer = RobotDrawer(ip="192.168.125.1", max_x=290, max_y=210)

# Connect to robot
if drawer.connect():
    print("Robot connected successfully!")
    
    # Load and process image
    if drawer.load_image("sample_image.png", precision="high"):
        print("Image processed successfully!")
        
        # Preview the drawing paths
        drawer.plot_preview()
        
        # Start drawing
        if drawer.draw():
            print("Drawing completed!")
        else:
            print("Drawing failed!")
    
    # Disconnect when done
    drawer.disconnect()
```

### 🤖 Dual-Arm Drawing

```python
# Enable dual-arm mode
drawer = RobotDrawer(ip="192.168.125.1", port=1025, port_l=1026)

if drawer.connect():
    drawer.load_image("complex_image.png", precision="high")
    
    # Dual-arm drawing with collision avoidance
    success = drawer.draw_dual(buffer_radius=50)
    
    if success:
        print("Dual-arm drawing completed!")
```

### 🔊 Voice Control Integration

The system supports Polish voice commands using the VOSK speech recognition engine:

#### Available Commands:
- **"start"** - Start drawing
- **"stop"** - Emergency stop  
- **"uchwyć"** - Take picture (from camera)
- **"połącz"** - Connect to robot
- **"karykatura"** - Switch to caricature mode
- **"portret"** - Switch to portrait mode

#### Implementation:
```python
from voice_commands import VoiceCommandListener

def handle_voice_command(command):
    if command == "start":
        drawer.draw()
    elif command == "stop":
        drawer.send_stop()
    elif command == "połącz":  # "connect" in Polish
        drawer.connect()
    elif command == "uchwyć":  # "capture" in Polish
        # Trigger camera capture
        pass

# Start voice listener
listener = VoiceCommandListener(callback=handle_voice_command)
listener.start()
```

#### Requirements:
- VOSK model: `vosk-model-small-pl-0.22`
- Microphone input device
- Sounddevice Python library

### 📷 Camera Integration

The `robot_ftp_downloader.py` module provides local camera capture functionality:

#### RobotCameraCapture Class
```python
class RobotCameraCapture:
    def capture_image(self, camera_index=0, local_path="image.png", 
                     timeout=1.0, fast=False, resolution=(640, 480), 
                     attempts=3):
        """
        Capture single frame from local camera.
        
        Args:
            camera_index: OS camera index (0 for default)
            local_path: Output file path
            timeout: Maximum capture time
            fast: Enable fast mode with lower resolution
            resolution: Camera resolution when fast=True
            attempts: Number of capture attempts
        """
```

#### Features:
- **Multiple Camera Support**: Specify camera index for multi-camera setups
- **Fast Mode**: Reduced resolution for quick captures
- **Timeout Handling**: Prevents hanging on camera issues
- **Cross-Platform**: Works with DirectShow (Windows) and generic backends
- **Error Recovery**: Multiple attempts with graceful failure handling

#### Usage Examples:
```python
# Basic capture
cam = RobotCameraCapture()
success = cam.capture_image()

# Fast capture with custom resolution
success = cam.capture_image(fast=True, resolution=(320, 240))

# Multi-camera setup
success = cam.capture_image(camera_index=1, local_path="camera2.png")
```

The system integrates with OpenAI's DALL-E for text-to-image generation and line art conversion:

#### Text-to-Image Generation:
```python
from convert_to_lineart import generate_image_from_text, convert_to_lineart

# Generate image from text prompt
generated_path = generate_image_from_text("A minimalist portrait of a cat")

# Convert to line art suitable for robot drawing
line_art_path = convert_to_lineart(generated_path, prompt_type="minimalist")

# Draw with robot
drawer.load_image(line_art_path)
drawer.draw()
```

#### Available Styles:
- **minimalist**: Clean, simple line art with uniform stroke thickness
- **caricature**: Exaggerated features for humorous effect

#### Line Art Catalog System:
The system automatically organizes generated artwork:
```
line_art_catalog/
├── 20250901_153825_minimalist/
│   ├── input_original.png
│   ├── output_minimalist_lineart.png
│   └── conversion_info.txt
├── 20250902_131242_caricature/
│   ├── input_original.png
│   ├── output_caricature_lineart.png
│   └── conversion_info.txt
└── ...
```

Each folder contains:
- **Input file**: Original source image
- **Output file**: Processed line art
- **Metadata**: Conversion parameters and timestamps

---

## Troubleshooting

### 🔧 Common Issues

#### Connection Problems

**Issue**: Robot not connecting
```
Solutions:
1. Verify IP address (default: 192.168.125.1)
2. Check network cable connection
3. Ensure RAPID modules are loaded and running
4. Verify firewall settings allow TCP connections
5. Test with ping command: ping 192.168.125.1
```

**Issue**: Timeout during START command
```
Solutions:
1. Wait up to 90 seconds for robot initialization
2. Check robot status lights
3. Verify work object calibration
4. Ensure drawing surface is properly positioned
```

#### Drawing Quality Issues

**Issue**: Rough or jagged lines
```
Solutions:
1. Increase quality setting to "high" or "highest"
2. Enable path smoothing with Bézier curves
3. Reduce drawing speed in robot settings
4. Check pen/tool calibration
```

**Issue**: Missing drawing elements
```
Solutions:
1. Adjust detection method (try "adaptive" for varied lighting)
2. Lower precision factor for more detail capture
3. Disable frame filtering if enabled
4. Check image contrast and clarity
```

#### Performance Issues

**Issue**: Slow drawing speed
```
Solutions:
1. Enable batch mode for faster communication
2. Use dual-arm mode for parallel processing
3. Reduce precision for faster processing
4. Enable TSP optimization for shorter paths
```

### 📊 Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `CONNECTION_FAILED` | Cannot establish TCP connection | Check network and robot status |
| `INVALID_COORDINATES` | Coordinates outside workspace | Adjust margins or image scaling |
| `TIMEOUT_ERROR` | Robot response timeout | Increase timeout or check robot status |
| `BATCH_SIZE_ERROR` | Batch command too long | Reduce batch size or point density |
| `COLLISION_DETECTED` | Dual-arm collision risk | Increase buffer radius |


#### Drawing Progress Callbacks
```python
def progress_callback(current_batch, total_batches, points_sent, total_points):
    """Real-time progress updates during drawing operations"""
    progress_percent = (points_sent / total_points) * 100
    print(f"Progress: {progress_percent:.1f}% ({points_sent}/{total_points} points)")
```

#### Timing Analysis
```python
# Drawing duration tracking
start_time = time.time()
success = drawer.draw(progress_callback=progress_callback)
elapsed_time = time.time() - start_time
print(f"Drawing completed in {elapsed_time:.2f} seconds")
```

#### Batch Optimization
- **Default Batch Size**: 8 points per command
- **Maximum Batch Size**: 15 points (RAPID string limit)
- **Adaptive Sizing**: Based on coordinate complexity
- **Ultra-Fast Mode**: Optimized for performance

### 🔧 Configuration Persistence

All settings are automatically saved to `robot_gui_config.json`:

```json
{
  "robot_ip": "192.168.125.1",
  "robot_port": "1025", 
  "robot_port_l": "1026",
  "use_center_origin": true,
  "quality_var": "high",
  "detection_method": "threshold",
  "enable_tsp": true,
  "use_batch_mode": true,
  "dual_arm_mode": false,
  "max_x": 290,
  "max_y": 210,
  "margin_x": 10,
  "margin_y": 10,
  "forbidden_buffer": 40,
  "drawing_mode": "load",
  "brush_size": 5,
  "enable_logo": false,
  "logo_size": 20,
  "enable_frame_filtering": false
}
```

The configuration is loaded on startup and saved on exit, preserving user preferences across sessions.

---

#### Memory Management
- Use generators for large datasets
- Clear matplotlib figures after use
- Close file handles properly
- Monitor memory usage during long operations

### 🔐 Security Considerations

#### Network Security
- Use dedicated network for robot communication
- Keep robot firmware updated

#### Input Validation
```python
def validate_coordinates(x: float, y: float, max_x: float, max_y: float) -> bool:
    """Validate coordinates are within workspace bounds."""
    return (-max_x/2 <= x <= max_x/2) and (-max_y/2 <= y <= max_y/2)
```


### 📚 Additional Resources
- [ABB YuMi Documentation](https://new.abb.com/products/robotics/yumi)
- [OpenCV Tutorials](https://opencv-python-tutroals.readthedocs.io/)
- [Matplotlib Documentation](https://matplotlib.org/stable/contents.html)
- [VOSK Speech Recognition](https://alphacephei.com/vosk/)

---


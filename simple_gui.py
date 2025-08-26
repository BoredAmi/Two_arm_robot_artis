"""
Simple, user-friendly GUI for Robot Drawing System.

This module provides a clean, intuitive graphical interface for the Robot Drawing System.
It offers two main input methods:
1. Load image files (JPG, PNG, BMP, etc.)
2. Create drawings using an interactive canvas

Features:
- Real-time image processing and preview
- Robot connection management
- Progress tracking during drawing operations
- Template shapes for quick testing
- TSP optimization controls
- Quality/precision settings

The GUI is designed to be accessible to users of all technical levels while providing
access to advanced features for power users.

Version: 1.0
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import subprocess
import os
from PIL import Image, ImageTk
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from robot_drawer import RobotDrawer


class SimpleRobotGUI:
    """
    Main GUI class for the Robot Drawing System.
    
    Provides a clean, step-by-step interface for:
    - Image loading and drawing creation
    - Robot connection management  
    - Image processing with quality controls
    - Real-time drawing progress tracking
    """
    
    # Default robot connection settings
    DEFAULT_ROBOT_IP = "192.168.125.1"
    DEFAULT_ROBOT_PORT = "1025"
    
    # UI dimensions and colors
    WINDOW_WIDTH = 900
    WINDOW_HEIGHT = 700
    PREVIEW_WIDTH = 300
    PREVIEW_HEIGHT = 200
    
    # Color scheme
    COLORS = {
        'background': '#f5f5f5',
        'section_bg': 'white',
        'header_bg': '#2196F3',
        'header_text': 'white',
        'button_connect': '#FF9800',
        'button_draw': '#4CAF50',
        'button_stop': '#f44336',
        'button_templates': '#607D8B',
        'button_canvas': '#9C27B0',
        'status_bg': '#e0e0e0'
    }
    
    def __init__(self):
        """Initialize the GUI application."""
        import json
        import os
        self.config_path = "robot_gui_config.json"
        self.config = self._load_config()

        self.root = tk.Tk()
        self.root.title("Robot Drawing System")
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.configure(bg=self.COLORS['background'])

        # Initialize robot drawer with TSP enabled by default and default dimensions
        self.drawer = RobotDrawer(max_x=290, max_y=210, enable_tsp=True, use_center_origin=True, margin_x=10, margin_y=10)

        # Initialize state variables
        self._init_variables()

        # Override defaults with config values if present
        if self.config.get("robot_ip"):
            self.robot_ip.set(self.config["robot_ip"])
        if self.config.get("robot_port"):
            self.robot_port.set(self.config["robot_port"])
        if self.config.get("use_center_origin") is not None:
            self.use_center_origin.set(self.config["use_center_origin"])
        if self.config.get("enable_logo") is not None:
            self.enable_logo.set(self.config["enable_logo"])
        if self.config.get("logo_size") is not None:
            self.logo_size.set(self.config["logo_size"])
        if self.config.get("max_x") is not None:
            self.max_x.set(self.config["max_x"])
        if self.config.get("max_y") is not None:
            self.max_y.set(self.config["max_y"])
        if self.config.get("margin_x") is not None:
            self.margin_x.set(self.config["margin_x"])
        if self.config.get("margin_y") is not None:
            self.margin_y.set(self.config["margin_y"])

        # Create the user interface
        self.create_simple_interface()

    def _load_config(self):
        try:
            import json, os
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self):
        try:
            import json
            config = {
                "robot_ip": self.robot_ip.get(),
                "robot_port": self.robot_port.get(),
                "use_center_origin": self.use_center_origin.get(),
                "enable_logo": self.enable_logo.get(),
                "logo_size": self.logo_size.get(),
                "max_x": self.max_x.get(),
                "max_y": self.max_y.get(),
                "margin_x": self.margin_x.get(),
                "margin_y": self.margin_y.get()
            }
            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass
    
    def _init_variables(self):
        """Initialize all GUI state variables."""
        # File and drawing state
        self.image_path = tk.StringVar()
        self.drawing_mode = tk.StringVar(value="load")  # "load" or "draw"
        
        # Robot connection
        self.robot_ip = tk.StringVar(value=self.DEFAULT_ROBOT_IP)
        self.robot_port = tk.StringVar(value=self.DEFAULT_ROBOT_PORT)
        self.is_connected = False
        
        # Processing state
        self.status_text = tk.StringVar(value="Ready")
        self.quality_var = tk.StringVar(value="high")
        self.detection_method = tk.StringVar(value="threshold")  # Default to threshold for performance
        self.enable_tsp = tk.BooleanVar(value=True)
        self.use_batch_mode = tk.BooleanVar(value=True)  # Default to batch mode for speed
        self.use_center_origin = tk.BooleanVar(value=True)  # Default to center-based coordinates
        self.is_processed = False
        
        # Logo settings
        self.enable_logo = tk.BooleanVar(value=False)  # Logo disabled by default
        self.logo_size = tk.IntVar(value=20)  # Logo size in mm
        
        # Drawing dimensions (mm)
        self.max_x = tk.IntVar(value=290)  # Default robot workspace width
        self.max_y = tk.IntVar(value=210)  # Default robot workspace height
        
        # Drawing margins (mm)
        self.margin_x = tk.IntVar(value=10)  # Default horizontal margin
        self.margin_y = tk.IntVar(value=10)  # Default vertical margin
        
        # Drawing canvas state
        self.brush_size = tk.IntVar(value=3)
        self.drawing_canvas = None
        self.drawing_data = []
        self.last_x = None
        self.last_y = None
        self.drawing_image = None
        self.temp_drawing_path = None
        
        # Drawing operation state
        self.drawing_active = False
    
    def create_simple_interface(self):
        """Create a clean, step-by-step interface."""
        # Main container with padding
        main_frame = tk.Frame(self.root, bg=self.COLORS['background'], padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Application title
        title_label = tk.Label(main_frame, text="Robot Drawing System", 
                              font=('Arial', 18, 'bold'), 
                              bg=self.COLORS['background'], fg='#333')
        title_label.pack(pady=(0, 30))
        
        # Create main workflow sections
        self.create_step_section(main_frame, "1. Choose Your Image or Draw", self.create_image_section)
        self.create_step_section(main_frame, "2. Connect to Robot", self.create_connection_section)
        self.create_step_section(main_frame, "3. Preview & Send to Robot", self.create_action_section)
        
        # Status bar at bottom
        self.create_status_bar(main_frame)
    
    def create_step_section(self, parent, title, content_func):
        """
        Create a clean step section with header and content.
        
        Args:
            parent: Parent widget
            title (str): Section title text
            content_func: Function to create section content
        """
        # Step container with border
        step_frame = tk.Frame(parent, bg=self.COLORS['section_bg'], relief='solid', bd=1)
        step_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Step header with colored background
        header_frame = tk.Frame(step_frame, bg=self.COLORS['header_bg'], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(header_frame, text=title, 
                               font=('Arial', 12, 'bold'), 
                               bg=self.COLORS['header_bg'], 
                               fg=self.COLORS['header_text'])
        header_label.pack(expand=True)
        
        # Step content area
        content_frame = tk.Frame(step_frame, bg=self.COLORS['section_bg'], padx=20, pady=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        content_func(content_frame)
    
    def create_image_section(self, parent):
        """Create image selection section"""
        # Mode selection
        mode_frame = tk.Frame(parent, bg='white')
        mode_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(mode_frame, text="Choose Method:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        tk.Radiobutton(mode_frame, text="📁 Load Image File", variable=self.drawing_mode, 
                      value="load", bg='white', font=('Arial', 10),
                      activebackground='white', command=self.on_mode_change).pack(side=tk.LEFT, padx=(10, 20))
        
        tk.Radiobutton(mode_frame, text="🎨 Draw Your Own", variable=self.drawing_mode, 
                      value="draw", bg='white', font=('Arial', 10),
                      activebackground='white', command=self.on_mode_change).pack(side=tk.LEFT)
        
        # File selection section
        self.file_section = tk.Frame(parent, bg='white')
        self.file_section.pack(fill=tk.X, pady=(0, 10))
        
        # Current file display
        self.file_label = tk.Label(self.file_section, text="No image selected", 
                                  font=('Arial', 10), bg='white', fg='#666', 
                                  anchor='w', width=50)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Browse button
        browse_btn = tk.Button(self.file_section, text="Browse Images", 
                              command=self.browse_image,
                              bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
                              relief='flat', padx=20, pady=8, cursor='hand2')
        browse_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Drawing section
        self.draw_section = tk.Frame(parent, bg='white')
        self.draw_section.pack(fill=tk.X, pady=(0, 10))
        
        # Drawing controls row
        draw_controls = tk.Frame(self.draw_section, bg='white')
        draw_controls.pack()
        
        draw_btn = tk.Button(draw_controls, text="🎨 Open Drawing Canvas", 
                            command=self.open_drawing_window,
                            bg='#9C27B0', fg='white', font=('Arial', 11, 'bold'),
                            relief='flat', padx=25, pady=10, cursor='hand2')
        draw_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Templates button
        templates_btn = tk.Button(draw_controls, text="📋 Templates", 
                                 command=self.show_templates,
                                 bg='#607D8B', fg='white', font=('Arial', 10, 'bold'),
                                 relief='flat', padx=15, pady=10, cursor='hand2')
        templates_btn.pack(side=tk.LEFT)
        
        # Initially hide draw section
        self.draw_section.pack_forget()
        
        # Quality selector
        quality_frame = tk.Frame(parent, bg='white')
        quality_frame.pack(fill=tk.X)
        
        tk.Label(quality_frame, text="Quality:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        self.quality_var = tk.StringVar(value="high")
        for i, (text, value) in enumerate([("Standard", "medium"), ("High", "high"), ("Ultra", "highest")]):
            rb = tk.Radiobutton(quality_frame, text=text, variable=self.quality_var, 
                               value=value, bg='white', font=('Arial', 9),
                               activebackground='white', command=self.on_quality_change)
            rb.pack(side=tk.LEFT, padx=(10, 0))
        
        # Detection method selector
        detection_frame = tk.Frame(parent, bg='white')
        detection_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(detection_frame, text="Detection Method:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        for i, (text, value) in enumerate([("Adaptive", "adaptive"), ("Threshold", "threshold"), ("Canny Edge", "canny"), ("Canny+Fill", "canny_filled")]):
            rb = tk.Radiobutton(detection_frame, text=text, variable=self.detection_method, 
                               value=value, bg='white', font=('Arial', 9),
                               activebackground='white', command=self.on_detection_method_change)
            rb.pack(side=tk.LEFT, padx=(10, 0))
        
        # TSP optimization and batch mode selector (combined row)
        tsp_batch_frame = tk.Frame(parent, bg='white')
        tsp_batch_frame.pack(fill=tk.X, pady=(10, 0))
        
        # TSP section
        tk.Label(tsp_batch_frame, text="Path Optimization:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        tsp_checkbox = tk.Checkbutton(tsp_batch_frame, text="Enable TSP (shorter paths)", 
                                     variable=self.enable_tsp, bg='white', font=('Arial', 9),
                                     activebackground='white', command=self.on_tsp_change)
        tsp_checkbox.pack(side=tk.LEFT, padx=(10, 20))
        
        # Batch mode section (same row)
        tk.Label(tsp_batch_frame, text="Drawing Mode:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT, padx=(20, 0))
        
        batch_checkbox = tk.Checkbutton(tsp_batch_frame, text="Batch Commands (faster)", 
                                       variable=self.use_batch_mode, bg='white', font=('Arial', 9),
                                       activebackground='white', command=self.on_batch_mode_change)
        batch_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        
        # Coordinate system and logo settings (combined row)
        coord_logo_frame = tk.Frame(parent, bg='white')
        coord_logo_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Coordinate system section
        tk.Label(coord_logo_frame, text="Coordinate System:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        coord_checkbox = tk.Checkbutton(coord_logo_frame, text="Center Origin", 
                                       variable=self.use_center_origin, bg='white', font=('Arial', 9),
                                       activebackground='white', command=self.on_coordinate_system_change)
        coord_checkbox.pack(side=tk.LEFT, padx=(10, 20))
        
        # Logo section (same row)
        tk.Label(coord_logo_frame, text="Logo:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT, padx=(20, 0))
        
        logo_checkbox = tk.Checkbutton(coord_logo_frame, text="Add logo_short.png", 
                                      variable=self.enable_logo, bg='white', font=('Arial', 9),
                                      activebackground='white', command=self.on_logo_setting_change)
        logo_checkbox.pack(side=tk.LEFT, padx=(10, 10))
        
        # Logo size selector (same row)
        tk.Label(coord_logo_frame, text="Size:", font=('Arial', 9), 
                bg='white').pack(side=tk.LEFT, padx=(5, 5))
        
        logo_size_spinbox = tk.Spinbox(coord_logo_frame, from_=10, to=50, width=4, 
                                      textvariable=self.logo_size, font=('Arial', 9),
                                      command=self.on_logo_setting_change)
        logo_size_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Label(coord_logo_frame, text="mm", font=('Arial', 9), 
                bg='white').pack(side=tk.LEFT)

        # Drawing dimensions selector
        dimensions_frame = tk.Frame(parent, bg='white')
        dimensions_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(dimensions_frame, text="Drawing Area (mm):", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        # X dimension
        x_frame = tk.Frame(dimensions_frame, bg='white')
        x_frame.pack(side=tk.LEFT, padx=(10, 5))
        
        tk.Label(x_frame, text="Width:", font=('Arial', 9), bg='white').pack(side=tk.LEFT)
        x_spinbox = tk.Spinbox(x_frame, from_=50, to=500, textvariable=self.max_x, 
                              width=6, font=('Arial', 9), command=self.on_dimensions_change)
        x_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        x_spinbox.bind('<KeyRelease>', lambda e: self.on_dimensions_change())
        x_spinbox.bind('<FocusOut>', lambda e: self.on_dimensions_change())
        
        # Y dimension
        y_frame = tk.Frame(dimensions_frame, bg='white')
        y_frame.pack(side=tk.LEFT, padx=(10, 5))
        
        tk.Label(y_frame, text="Height:", font=('Arial', 9), bg='white').pack(side=tk.LEFT)
        y_spinbox = tk.Spinbox(y_frame, from_=50, to=400, textvariable=self.max_y, 
                              width=6, font=('Arial', 9), command=self.on_dimensions_change)
        y_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        y_spinbox.bind('<KeyRelease>', lambda e: self.on_dimensions_change())
        y_spinbox.bind('<FocusOut>', lambda e: self.on_dimensions_change())
        
        # Preset buttons
        preset_frame = tk.Frame(dimensions_frame, bg='white')
        preset_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        presets = [("A4", 290, 210), ("A5", 210, 148), ("Custom", None, None)]
        for text, width, height in presets:
            if width and height:
                preset_btn = tk.Button(preset_frame, text=text, 
                                     command=lambda w=width, h=height: self.set_dimension_preset(w, h),
                                     bg='#e0e0e0', font=('Arial', 8), relief='flat', 
                                     padx=8, pady=2, cursor='hand2')
                preset_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # Margins selector
        margins_frame = tk.Frame(parent, bg='white')
        margins_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(margins_frame, text="Safety Margins (mm):", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        # X margin
        margin_x_frame = tk.Frame(margins_frame, bg='white')
        margin_x_frame.pack(side=tk.LEFT, padx=(10, 5))
        
        tk.Label(margin_x_frame, text="Horizontal:", font=('Arial', 9), bg='white').pack(side=tk.LEFT)
        margin_x_spinbox = tk.Spinbox(margin_x_frame, from_=0, to=50, textvariable=self.margin_x, 
                                     width=4, font=('Arial', 9), command=self.on_margins_change)
        margin_x_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        margin_x_spinbox.bind('<KeyRelease>', lambda e: self.on_margins_change())
        margin_x_spinbox.bind('<FocusOut>', lambda e: self.on_margins_change())
        
        # Y margin
        margin_y_frame = tk.Frame(margins_frame, bg='white')
        margin_y_frame.pack(side=tk.LEFT, padx=(10, 5))
        
        tk.Label(margin_y_frame, text="Vertical:", font=('Arial', 9), bg='white').pack(side=tk.LEFT)
        margin_y_spinbox = tk.Spinbox(margin_y_frame, from_=0, to=50, textvariable=self.margin_y, 
                                     width=4, font=('Arial', 9), command=self.on_margins_change)
        margin_y_spinbox.pack(side=tk.LEFT, padx=(5, 0))
        margin_y_spinbox.bind('<KeyRelease>', lambda e: self.on_margins_change())
        margin_y_spinbox.bind('<FocusOut>', lambda e: self.on_margins_change())
        
        # Margin preset buttons
        margin_preset_frame = tk.Frame(margins_frame, bg='white')
        margin_preset_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        margin_presets = [("None", 0, 0), ("Small", 5, 5), ("Medium", 10, 10), ("Large", 15, 15)]
        for text, margin_x, margin_y in margin_presets:
            margin_preset_btn = tk.Button(margin_preset_frame, text=text, 
                                        command=lambda mx=margin_x, my=margin_y: self.set_margin_preset(mx, my),
                                        bg='#e0e0e0', font=('Arial', 8), relief='flat', 
                                        padx=8, pady=2, cursor='hand2')
            margin_preset_btn.pack(side=tk.LEFT, padx=(2, 0))
    
    def create_connection_section(self, parent):
        """Create robot connection section"""
        # Connection settings
        conn_frame = tk.Frame(parent, bg='white')
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        # IP Address
        tk.Label(conn_frame, text="Robot IP:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        ip_entry = tk.Entry(conn_frame, textvariable=self.robot_ip, 
                           font=('Arial', 10), width=15, relief='solid', bd=1)
        ip_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        # Port
        tk.Label(conn_frame, text="Port:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        port_entry = tk.Entry(conn_frame, textvariable=self.robot_port, 
                             font=('Arial', 10), width=8, relief='solid', bd=1)
        port_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        # Connect button
        self.connect_btn = tk.Button(conn_frame, text="Connect", 
                                    command=self.toggle_connection,
                                    bg='#FF9800', fg='white', font=('Arial', 10, 'bold'),
                                    relief='flat', padx=20, pady=6, cursor='hand2')
        self.connect_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Get Picture button
        self.get_pic_btn = tk.Button(conn_frame, text="📷 Get Picture", 
                                    command=self.get_picture_from_robot,
                                    bg='#9C27B0', fg='white', font=('Arial', 10, 'bold'),
                                    relief='flat', padx=15, pady=6, cursor='hand2',
                                    state='disabled')
        self.get_pic_btn.pack(side=tk.RIGHT)
        
        # Connection status
        self.conn_status_label = tk.Label(parent, text="⚫ Not Connected", 
                                         font=('Arial', 10), bg='white', fg='#f44336')
        self.conn_status_label.pack(anchor='w')
    
    def create_action_section(self, parent):
        """Create preview and action section"""
        # Preview area
        preview_frame = tk.Frame(parent, bg='white')
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        # Three panels: left preview, middle actions, right preview
        left_panel = tk.Frame(preview_frame, bg='white')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Middle panel for buttons and progress
        middle_panel = tk.Frame(preview_frame, bg='white', width=180)
        middle_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        middle_panel.pack_propagate(False)
        
        right_panel = tk.Frame(preview_frame, bg='white')
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Original image preview (left)
        tk.Label(left_panel, text="Original Image", font=('Arial', 10, 'bold'), 
                bg='white').pack(pady=(0, 5))
        
        self.original_canvas = tk.Canvas(left_panel, bg='#f8f8f8', 
                                        width=300, height=200, relief='solid', bd=1)
        self.original_canvas.pack()
        self.original_canvas.create_text(150, 100, text="No image loaded", 
                                        font=('Arial', 10), fill='#999')
        
        # Middle panel content (buttons and progress)
        # Face Drawing button
        self.face_drawing_btn = tk.Button(middle_panel, text="👤 Face\nDrawing", 
                                         command=self.convert_to_face_drawing,
                                         bg='#E91E63', fg='white', font=('Arial', 9, 'bold'),
                                         relief='flat', padx=15, pady=10, cursor='hand2',
                                         state='disabled', width=12)
        self.face_drawing_btn.pack(pady=(20, 5))

        # Caricature button
        self.caricature_btn = tk.Button(middle_panel, text="🎭 Caricature", 
                                       command=self.convert_to_caricature,
                                       bg='#FF9800', fg='white', font=('Arial', 9, 'bold'),
                                       relief='flat', padx=15, pady=10, cursor='hand2',
                                       state='disabled', width=12)
        self.caricature_btn.pack(pady=5)

        # Draw button
        self.draw_btn = tk.Button(middle_panel, text="🎨 Start\nDrawing", 
                                 command=self.start_robot_drawing,
                                 bg='#4CAF50', fg='white', font=('Arial', 9, 'bold'),
                                 relief='flat', padx=15, pady=10, cursor='hand2',
                                 state='disabled', width=12)
        self.draw_btn.pack(pady=5)

        # Zoom viewer button
        zoom_btn = tk.Button(middle_panel, text="🔍 Zoom\nViewer",
                            command=self.open_detailed_path_window,
                            bg='#607D8B', fg='white', font=('Arial', 9, 'bold'),
                            relief='flat', padx=15, pady=10, cursor='hand2',
                            width=12)
        zoom_btn.pack(pady=5)
        
        # Emergency stop button (initially hidden)
        self.stop_btn = tk.Button(middle_panel, text="⏹ Stop", 
                                 command=self.emergency_stop,
                                 bg='#f44336', fg='white', font=('Arial', 9, 'bold'),
                                 relief='flat', padx=15, pady=8, width=12)
        
        self.drawing_active = False
        
        # Robot path preview
        tk.Label(right_panel, text="Robot Drawing Path", font=('Arial', 10, 'bold'), 
                bg='white').pack(pady=(0, 5))
        
        # Matplotlib figure for robot path with dynamic coordinate system
        # Calculate figure size to match drawing area aspect ratio
        drawing_aspect_ratio = self.max_x.get() / self.max_y.get()
        fig_width = 4.0
        fig_height = fig_width / drawing_aspect_ratio
        # Limit height to reasonable range
        fig_height = min(4.0, max(2.0, fig_height))
        
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=75, facecolor='white')
        self.ax = self.fig.add_subplot(111)
        
        self.canvas_widget = FigureCanvasTkAgg(self.fig, right_panel)
        self.canvas_widget.get_tk_widget().pack()
        
        # Initialize the preview with correct coordinate system
        self.update_robot_preview()

    # ---------------------- Zoom / Detailed Viewer ----------------------
    # Removed embedded scroll/double-click zoom; only dedicated viewer retained

    def open_detailed_path_window(self):
        """Open a larger, dedicated window with full zoom & pan controls."""
        if hasattr(self, 'detail_window') and self.detail_window.winfo_exists():
            self.detail_window.lift()
            return
        self.detail_window = tk.Toplevel(self.root)
        self.detail_window.title("Detailed Path Viewer")
        self.detail_window.geometry("900x600")
        self.detail_window.configure(bg='white')

        # Figure with correct aspect ratio
        max_x = self.max_x.get(); max_y = self.max_y.get()
        drawing_aspect_ratio = max_x / max_y
        fig_width = 8.0
        fig_height = fig_width / drawing_aspect_ratio
        # Limit height to reasonable range for the detailed viewer
        fig_height = min(8.0, max(4.0, fig_height))
        
        fig = Figure(figsize=(fig_width, fig_height), dpi=100, facecolor='white')
        ax = fig.add_subplot(111)
        
        # Set coordinate system based on user selection
        use_center = self.use_center_origin.get()
        
        if use_center:
            # Center-based coordinate system (0,0 at center)
            ax.set_xlim(-max_x/2, max_x/2)
            ax.set_ylim(-max_y/2, max_y/2)
            origin_text = "Center (0,0)"
            boundary_x = [-max_x/2, max_x/2, max_x/2, -max_x/2, -max_x/2]
            boundary_y = [-max_y/2, -max_y/2, max_y/2, max_y/2, -max_y/2]
            # Draw center axes
            ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            # Effective drawing area with margins
            margin_x = self.margin_x.get()
            margin_y = self.margin_y.get()
            effective_boundary_x = [-(max_x/2-margin_x), (max_x/2-margin_x), (max_x/2-margin_x), -(max_x/2-margin_x), -(max_x/2-margin_x)]
            effective_boundary_y = [-(max_y/2-margin_y), -(max_y/2-margin_y), (max_y/2-margin_y), (max_y/2-margin_y), -(max_y/2-margin_y)]
        else:
            # Corner-based coordinate system (0,0 at corner)
            ax.set_xlim(0, max_x)
            ax.set_ylim(0, max_y)
            origin_text = "Corner (0,0)"
            boundary_x = [0, max_x, max_x, 0, 0]
            boundary_y = [0, 0, max_y, max_y, 0]
            # Effective drawing area with margins
            margin_x = self.margin_x.get()
            margin_y = self.margin_y.get()
            effective_boundary_x = [margin_x, max_x-margin_x, max_x-margin_x, margin_x, margin_x]
            effective_boundary_y = [margin_y, margin_y, max_y-margin_y, max_y-margin_y, margin_y]
        
        ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)')
        ax.grid(True, alpha=0.3)
        
        # Set equal aspect ratio so 1mm = 1mm visually
        ax.set_aspect('equal', adjustable='box')
        
        # Boundary
        ax.plot(boundary_x, boundary_y, 'k--', linewidth=2, alpha=0.5, label='Workspace Area')
        
        # Show effective drawing area if margins are applied
        if margin_x > 0 or margin_y > 0:
            ax.plot(effective_boundary_x, effective_boundary_y, 'g-', linewidth=1.5, alpha=0.7, label='Drawing Area (with margins)')

        from matplotlib_anim_helper import animate_paths
        import matplotlib.pyplot as plt
        import numpy as np
        if self.drawer.drawing_points:
            colors = plt.cm.tab20(np.linspace(0, 1, len(self.drawer.drawing_points)))
            for i, path in enumerate(self.drawer.drawing_points):
                if path:
                    xs = [p[0] for p in path]; ys = [p[1] for p in path]
                    ax.plot(xs, ys, '-', color=colors[i], linewidth=1)
            total_points = sum(len(p) for p in self.drawer.drawing_points)
            coord_info = "center" if use_center else "corner"
            margin_info = f" (margins: {self.margin_x.get()}x{self.margin_y.get()}mm)" if self.margin_x.get() > 0 or self.margin_y.get() > 0 else ""
            ax.set_title(f'{len(self.drawer.drawing_points)} paths, {total_points} points ({coord_info} origin{margin_info})')
        else:
            text_x = 0 if use_center else max_x/2
            text_y = 0 if use_center else max_y/2
            coord_info = "center" if use_center else "corner"
            ax.text(text_x, text_y, f'No path generated\n(0,0) at {coord_info}', ha='center', va='center', color='#666')

        canvas = FigureCanvasTkAgg(fig, self.detail_window)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar = NavigationToolbar2Tk(canvas, self.detail_window)
        toolbar.update()
        canvas.mpl_connect('scroll_event', lambda e: self._detail_scroll_zoom(e, ax, canvas))

        # --- Animation Button ---
        def start_animation():
            ax.clear()
            # Redraw static elements (axes, boundaries, etc.)
            ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='box')
            ax.plot(boundary_x, boundary_y, 'k--', linewidth=2, alpha=0.5, label='Workspace Area')
            if margin_x > 0 or margin_y > 0:
                ax.plot(effective_boundary_x, effective_boundary_y, 'g-', linewidth=1.5, alpha=0.7, label='Drawing Area (with margins)')
            # Animate paths
            print(f"[DEBUG] Number of paths: {len(self.drawer.drawing_points)}")
            print(f"[DEBUG] Type of drawing_points: {type(self.drawer.drawing_points)}")
            if self.drawer.drawing_points:
                for idx, p in enumerate(self.drawer.drawing_points):
                    print(f"[DEBUG] Path {idx}: type={type(p)}, length={len(p)}")
            else:
                print("[DEBUG] drawing_points is empty or None")
            if self.drawer.drawing_points and any(len(p) > 0 for p in self.drawer.drawing_points):
                colors = plt.cm.tab20(np.linspace(0, 1, len(self.drawer.drawing_points)))
                # Store animation object to prevent garbage collection
                self._current_anim = animate_paths(
                    ax, self.drawer.drawing_points, colors=colors, interval=200,
                    on_frame=lambda f: canvas.draw_idle())
                canvas.draw_idle()
            else:
                import tkinter.messagebox as mb
                msg = f"No paths to animate. drawing_points type: {type(self.drawer.drawing_points)}, length: {len(self.drawer.drawing_points) if self.drawer.drawing_points is not None else 'None'}\nContent: {self.drawer.drawing_points}"
                mb.showwarning("No Paths to Animate", msg)
                ax.text(0, 0, 'No path data to animate!', ha='center', va='center', color='red', fontsize=14)
            canvas.draw_idle()

        anim_btn = tk.Button(self.detail_window, text="Animate Paths", command=start_animation, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))

        anim_btn.pack(side=tk.TOP, pady=8)

        # --- Point-by-point Animation Button ---
        def start_point_animation():
            ax.clear()
            ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)')
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='box')
            ax.plot(boundary_x, boundary_y, 'k--', linewidth=2, alpha=0.5, label='Workspace Area')
            if margin_x > 0 or margin_y > 0:
                ax.plot(effective_boundary_x, effective_boundary_y, 'g-', linewidth=1.5, alpha=0.7, label='Drawing Area (with margins)')
            if self.drawer.drawing_points and any(len(p) > 0 for p in self.drawer.drawing_points):
                from matplotlib_anim_point_helper import animate_points
                colors = plt.cm.tab20(np.linspace(0, 1, len(self.drawer.drawing_points)))
                self._current_anim = animate_points(
                    ax, self.drawer.drawing_points, colors=colors, interval=1,
                    on_frame=lambda f: canvas.draw_idle())
                canvas.draw_idle()
            else:
                import tkinter.messagebox as mb
                msg = f"No points to animate. drawing_points type: {type(self.drawer.drawing_points)}, length: {len(self.drawer.drawing_points) if self.drawer.drawing_points is not None else 'None'}\nContent: {self.drawer.drawing_points}"
                mb.showwarning("No Points to Animate", msg)
                ax.text(0, 0, 'No point data to animate!', ha='center', va='center', color='red', fontsize=14)
            canvas.draw_idle()

        anim_point_btn = tk.Button(self.detail_window, text="Animate Point by Point (fast)", command=start_point_animation, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        anim_point_btn.pack(side=tk.TOP, pady=4)

    def _detail_scroll_zoom(self, event, ax, canvas):
        """Scroll zoom inside detailed viewer."""
        if event.inaxes != ax:
            return
        scale = 1.25 if event.button == 'up' else 1/1.25
        xlim = ax.get_xlim(); ylim = ax.get_ylim()
        xdata = event.xdata if event.xdata is not None else (xlim[0]+xlim[1])/2
        ydata = event.ydata if event.ydata is not None else (ylim[0]+ylim[1])/2
        new_w = (xlim[1]-xlim[0]) / scale
        new_h = (ylim[1]-ylim[0]) / scale
        min_span = 2
        if new_w < min_span or new_h < min_span:
            return
        ax.set_xlim([xdata - new_w/2, xdata + new_w/2])
        ax.set_ylim([ydata - new_h/2, ydata + new_h/2])
        canvas.draw_idle()
    
    def create_status_bar(self, parent):
        """Create simple status bar with integrated progress bar"""
        status_frame = tk.Frame(parent, bg='#e0e0e0', height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, textvariable=self.status_text, 
                                    font=('Arial', 9), bg='#e0e0e0', anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        
        # Progress bar container (initially hidden)
        self.progress_container = tk.Frame(status_frame, bg='#e0e0e0')
        
        # Minimalistic progress bar
        self.bottom_progress_bar = ttk.Progressbar(
            self.progress_container, 
            mode='determinate', 
            length=200
        )
        self.bottom_progress_bar.pack(side=tk.LEFT, padx=(5, 5))
        
        # Progress text
        self.bottom_progress_label = tk.Label(
            self.progress_container, 
            text="", 
            font=('Arial', 8), 
            bg='#e0e0e0'
        )
        self.bottom_progress_label.pack(side=tk.LEFT, padx=(5, 10))
        
        # Progress indicator (for non-progress states)
        self.progress_indicator = tk.Label(status_frame, text="", 
                                          font=('Arial', 9), bg='#e0e0e0')
        self.progress_indicator.pack(side=tk.RIGHT, padx=10)
    
    def on_mode_change(self):
        """Handle mode selection change"""
        if self.drawing_mode.get() == "load":
            self.file_section.pack(fill=tk.X, pady=(0, 10))
            self.draw_section.pack_forget()
            # Clear drawing path when switching to file mode
            self.temp_drawing_path = None
            # Reset to no image if no file is selected
            if not self.image_path.get():
                self.file_label.config(text="No image selected", fg='#666')
                self.draw_btn.config(state='disabled')
                self.face_drawing_btn.config(state='disabled')  # Disable face drawing button
                self.original_canvas.delete("all")
                self.original_canvas.create_text(150, 100, text="No image loaded", 
                                                font=('Arial', 10), fill='#999')
        else:
            self.file_section.pack_forget()
            self.draw_section.pack(fill=tk.X, pady=(0, 10))
            # Clear file path when switching to draw mode
            self.image_path.set("")
            self.draw_btn.config(state='disabled')
            self.face_drawing_btn.config(state='disabled')  # Disable face drawing button
            self.original_canvas.delete("all")
            self.original_canvas.create_text(150, 100, text="No image loaded", 
                                            font=('Arial', 10), fill='#999')
    
    def on_quality_change(self):
        """Handle quality setting change"""
        # Only reprocess if we have an image/drawing loaded
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            self.status_text.set("Quality changed - reprocessing...")
            self.auto_process_image()
    
    def on_tsp_change(self):
        """Handle TSP optimization setting change"""
        # Preserve existing connection if any
        old_robot = None
        old_ip = None
        old_port = None
        was_connected = False
        
        if hasattr(self.drawer, 'robot') and self.drawer.robot and self.drawer.robot.socket:
            old_robot = self.drawer.robot
            old_ip = self.drawer.ip
            old_port = self.drawer.port
            was_connected = True
        
        # Update the drawer's TSP setting with coordinate system
        self.drawer = RobotDrawer(
            max_x=self.max_x.get(), 
            max_y=self.max_y.get(), 
            enable_tsp=self.enable_tsp.get(),
            use_center_origin=self.use_center_origin.get(),
            margin_x=self.margin_x.get(),
            margin_y=self.margin_y.get()
        )
        
        # Restore connection if it existed
        if was_connected and old_robot:
            self.drawer.robot = old_robot
            self.drawer.ip = old_ip
            self.drawer.port = old_port
        
        # Only reprocess if we have an image/drawing loaded
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            tsp_status = "enabled" if self.enable_tsp.get() else "disabled"
            self.status_text.set(f"TSP optimization {tsp_status} - reprocessing...")
            self.auto_process_image()
    
    def on_batch_mode_change(self):
        """Handle batch mode setting change"""
        if hasattr(self.drawer, 'robot') and self.drawer.robot:
            self.drawer.robot.set_batch_mode(self.use_batch_mode.get())
        
        mode_text = "batch" if self.use_batch_mode.get() else "individual"
        print(f"Drawing mode set to: {mode_text}")
    
    def on_coordinate_system_change(self):
        """Handle coordinate system setting change"""
        # Update robot communication if connected
        if hasattr(self.drawer, 'robot') and self.drawer.robot:
            self.drawer.robot.set_coordinate_system(self.use_center_origin.get())
        
        # Update robot drawer coordinate system
        if hasattr(self.drawer, 'set_coordinate_system'):
            self.drawer.set_coordinate_system(self.use_center_origin.get())
        
        origin_text = "center" if self.use_center_origin.get() else "corner"
        print(f"Coordinate system set to: {origin_text} origin")
        
        # Update preview to show correct coordinate system
        self.update_robot_preview()
        
        # If we have a processed image, update the coordinates
        if self.is_processed:
            current_path = None
            if self.drawing_mode.get() == "draw":
                if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                    current_path = self.temp_drawing_path
            else:
                if self.image_path.get():
                    current_path = self.image_path.get()
            
            if current_path:
                self.status_text.set(f"Coordinate system changed to {origin_text} - reprocessing...")
                self.auto_process_image()
    
    def on_detection_method_change(self):
        """Handle detection method setting change"""
        # Only reprocess if we have an image/drawing loaded
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            method_names = {"adaptive": "Adaptive", "threshold": "Threshold", "canny": "Canny Edge", "canny_filled": "Canny+Fill"}
            method_name = method_names.get(self.detection_method.get(), "Unknown")
            self.status_text.set(f"Detection method changed to {method_name} - reprocessing...")
            self.auto_process_image()
    
    def on_logo_setting_change(self):
        """Handle logo setting changes"""
        if self.enable_logo.get():
            self.status_text.set(f"Logo enabled (Size: {self.logo_size.get()}mm)")
        else:
            self.status_text.set("Logo disabled")
        
        # Reprocess if we have an image/drawing loaded
        current_path = None
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            self.auto_process_image()
    
    def on_dimensions_change(self):
        """Handle drawing dimensions change"""
        # Preserve existing connection if any
        old_robot = None
        old_ip = None
        old_port = None
        was_connected = False
        
        if hasattr(self.drawer, 'robot') and self.drawer.robot and self.drawer.robot.socket:
            old_robot = self.drawer.robot
            old_ip = self.drawer.ip
            old_port = self.drawer.port
            was_connected = True
        
        # Update the drawer with new dimensions and coordinate system
        self.drawer = RobotDrawer(
            max_x=self.max_x.get(), 
            max_y=self.max_y.get(), 
            enable_tsp=self.enable_tsp.get(),
            use_center_origin=self.use_center_origin.get(),
            margin_x=self.margin_x.get(),
            margin_y=self.margin_y.get()
        )
        
        # Restore connection if it existed
        if was_connected and old_robot:
            self.drawer.robot = old_robot
            self.drawer.ip = old_ip
            self.drawer.port = old_port
        
        # Update the preview plot dimensions
        self.update_robot_preview()
        
        # Only reprocess if we have an image/drawing loaded
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            self.status_text.set(f"Drawing area changed to {self.max_x.get()}x{self.max_y.get()}mm - reprocessing...")
            self.auto_process_image()
    
    def set_dimension_preset(self, width, height):
        """Set dimensions to a preset value"""
        self.max_x.set(width)
        self.max_y.set(height)
        self.on_dimensions_change()
    
    def set_margin_preset(self, margin_x, margin_y):
        """Set margins to a preset value"""
        self.margin_x.set(margin_x)
        self.margin_y.set(margin_y)
        self.on_margins_change()
    
    def on_margins_change(self):
        """Handle margin setting change"""
        # Recreate drawer with new margins while preserving connection
        self._recreate_drawer_with_margins()
        
        # Update preview
        self.update_robot_preview()
        
        # Reprocess if image is loaded
        current_path = None
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            self.status_text.set(f"Margins changed to {self.margin_x.get()}x{self.margin_y.get()}mm - reprocessing...")
            self.auto_process_image()
    
    def _recreate_drawer_with_margins(self):
        """Recreate robot drawer with new margin settings while preserving connection"""
        # Preserve existing connection if any
        old_robot = None
        old_ip = None
        old_port = None
        was_connected = False
        
        if hasattr(self.drawer, 'robot') and self.drawer.robot and self.drawer.robot.socket:
            old_robot = self.drawer.robot
            old_ip = self.drawer.ip
            old_port = self.drawer.port
            was_connected = True
        
        # Create new drawer with margins
        self.drawer = RobotDrawer(
            max_x=self.max_x.get(), 
            max_y=self.max_y.get(), 
            enable_tsp=self.enable_tsp.get(),
            use_center_origin=self.use_center_origin.get(),
            margin_x=self.margin_x.get(),
            margin_y=self.margin_y.get()
        )
        
        # Restore connection if it existed
        if was_connected and old_robot:
            self.drawer.robot = old_robot
            self.drawer.ip = old_ip
            self.drawer.port = old_port
    
    def open_drawing_window(self):
        """Open the drawing canvas window"""
        if hasattr(self, 'drawing_window') and self.drawing_window.winfo_exists():
            self.drawing_window.lift()
            return
            
        self.drawing_window = tk.Toplevel(self.root)
        self.drawing_window.title("🎨 Drawing Canvas")
        self.drawing_window.geometry("700x600")
        self.drawing_window.configure(bg='#f0f0f0')
        
        # Drawing controls frame
        controls_frame = tk.Frame(self.drawing_window, bg='#f0f0f0', height=60)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)
        controls_frame.pack_propagate(False)
        
        # Brush size control
        tk.Label(controls_frame, text="Brush Size:", bg='#f0f0f0', 
                font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 5))
        
        self.brush_size_scale = tk.Scale(controls_frame, from_=1, to=20, 
                                        orient=tk.HORIZONTAL, length=100,
                                        variable=self.brush_size, bg='#f0f0f0')
        self.brush_size_scale.pack(side=tk.LEFT, padx=(0, 20))
        
        # Action buttons
        clear_btn = tk.Button(controls_frame, text="🗑️ Clear", command=self.clear_canvas,
                             bg='#f44336', fg='white', font=('Arial', 10, 'bold'),
                             relief='flat', padx=15, pady=5)
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        save_btn = tk.Button(controls_frame, text="💾 Save Drawing", command=self.save_drawing,
                            bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'),
                            relief='flat', padx=15, pady=5)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        use_btn = tk.Button(controls_frame, text="✅ Use Drawing", command=self.use_drawing,
                           bg='#2196F3', fg='white', font=('Arial', 10, 'bold'),
                           relief='flat', padx=15, pady=5)
        use_btn.pack(side=tk.LEFT)
        
        # Canvas frame
        canvas_frame = tk.Frame(self.drawing_window, bg='white', relief='sunken', bd=2)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Create canvas
        self.drawing_canvas = tk.Canvas(canvas_frame, bg='white', cursor='pencil')
        self.drawing_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Initialize drawing state
        self.last_x = None
        self.last_y = None
        
        # Bind canvas events
        self.drawing_canvas.bind('<Button-1>', self.start_canvas_drawing)
        self.drawing_canvas.bind('<B1-Motion>', self.draw_on_canvas)
        self.drawing_canvas.bind('<ButtonRelease-1>', self.stop_canvas_drawing)
        
        # Focus the window
        self.drawing_window.focus_set()
    
    def show_templates(self):
        """Show template selection window"""
        template_window = tk.Toplevel(self.root)
        template_window.title("📋 Drawing Templates")
        template_window.geometry("400x300")
        template_window.configure(bg='#f0f0f0')
        
        # Title
        tk.Label(template_window, text="Choose a Template", 
                font=('Arial', 14, 'bold'), bg='#f0f0f0').pack(pady=10)
        
        # Templates list
        templates_frame = tk.Frame(template_window, bg='#f0f0f0')
        templates_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        templates = [
            ("⭕ Circle", self.create_circle_template),
            ("⬜ Square", self.create_square_template),
            ("🔺 Triangle", self.create_triangle_template),
            ("⭐ Star", self.create_star_template),
            ("💖 Heart", self.create_heart_template),
            ("🌊 Spiral", self.create_spiral_template)
        ]
        
        for i, (name, func) in enumerate(templates):
            btn = tk.Button(templates_frame, text=name, command=func,
                           bg='white', font=('Arial', 11), relief='solid', bd=1,
                           padx=20, pady=10, cursor='hand2', width=20)
            btn.pack(pady=5)
        
        # Close button
        tk.Button(template_window, text="Close", command=template_window.destroy,
                 bg='#f44336', fg='white', font=('Arial', 10, 'bold'),
                 relief='flat', padx=20, pady=8).pack(pady=10)
    
    def create_circle_template(self):
        """Create a circle template"""
        self.create_template_image("circle")
    
    def create_square_template(self):
        """Create a square template"""
        self.create_template_image("square")
    
    def create_triangle_template(self):
        """Create a triangle template"""
        self.create_template_image("triangle")
    
    def create_star_template(self):
        """Create a star template"""
        self.create_template_image("star")
    
    def create_heart_template(self):
        """Create a heart template"""
        self.create_template_image("heart")
    
    def create_spiral_template(self):
        """Create a spiral template"""
        self.create_template_image("spiral")
    
    def create_template_image(self, shape):
        """Create template image for given shape"""
        import tempfile
        import math
        from PIL import Image, ImageDraw
        
        try:
            # Create 400x400 white image
            img = Image.new('RGB', (400, 400), 'white')
            draw = ImageDraw.Draw(img)
            
            center_x, center_y = 200, 200
            size = 150
            
            if shape == "circle":
                draw.ellipse([center_x-size, center_y-size, center_x+size, center_y+size], 
                           outline='black', width=3)
            
            elif shape == "square":
                draw.rectangle([center_x-size, center_y-size, center_x+size, center_y+size], 
                             outline='black', width=3)
            
            elif shape == "triangle":
                points = [
                    (center_x, center_y-size),
                    (center_x-size*0.866, center_y+size//2),
                    (center_x+size*0.866, center_y+size//2),
                    (center_x, center_y-size)
                ]
                draw.line(points, fill='black', width=3)
            
            elif shape == "star":
                points = []
                for i in range(10):
                    angle = i * math.pi / 5
                    radius = size if i % 2 == 0 else size // 2
                    x = center_x + radius * math.cos(angle - math.pi/2)
                    y = center_y + radius * math.sin(angle - math.pi/2)
                    points.append((x, y))
                points.append(points[0])  # Close the shape
                draw.line(points, fill='black', width=3)
            
            elif shape == "heart":
                # Simple heart shape using curves
                for t in range(0, 628, 5):  # 0 to 2π in steps
                    angle = t / 100.0
                    x = 16 * math.sin(angle)**3
                    y = 13 * math.cos(angle) - 5 * math.cos(2*angle) - 2 * math.cos(3*angle) - math.cos(4*angle)
                    px = center_x + x * 8
                    py = center_y - y * 8
                    
                    if t > 0:
                        draw.line([prev_x, prev_y, px, py], fill='black', width=3)
                    prev_x, prev_y = px, py
            
            elif shape == "spiral":
                points = []
                for i in range(0, 720, 5):  # 2 full rotations
                    angle = math.radians(i)
                    radius = i / 720.0 * size
                    x = center_x + radius * math.cos(angle)
                    y = center_y + radius * math.sin(angle)
                    points.append((x, y))
                
                for i in range(len(points)-1):
                    draw.line([points[i], points[i+1]], fill='black', width=3)
            
            # Save template
            self.temp_drawing_path = os.path.join(tempfile.gettempdir(), f"template_{shape}.png")
            img.save(self.temp_drawing_path)
            
            # Update UI
            self.image_path.set(self.temp_drawing_path)
            self.file_label.config(text=f"Template: {shape.title()}")
            
            # Enable face drawing button when template is loaded
            self.face_drawing_btn.config(state='normal')
            self.caricature_btn.config(state='normal')
            
            self.status_text.set(f"{shape.title()} template loaded - processing...")
            
            # Load preview
            self.load_preview_image()
            
            # Process automatically
            self.auto_process_image()
            
            messagebox.showinfo("Template Created", f"{shape.title()} template loaded successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create template: {e}")
    
    def start_canvas_drawing(self, event):
        """Start drawing on canvas"""
        self.last_x = event.x
        self.last_y = event.y
    
    def draw_on_canvas(self, event):
        """Draw on canvas"""
        if self.last_x and self.last_y:
            self.drawing_canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                width=self.brush_size.get(), fill='black',
                capstyle=tk.ROUND, smooth=tk.TRUE
            )
        self.last_x = event.x
        self.last_y = event.y
    
    def stop_canvas_drawing(self, event):
        """Stop drawing"""
        self.last_x = None
        self.last_y = None
    
    def clear_canvas(self):
        """Clear the drawing canvas"""
        if hasattr(self, 'drawing_canvas'):
            self.drawing_canvas.delete("all")
    
    def save_drawing(self):
        """Save the current drawing"""
        if not hasattr(self, 'drawing_canvas'):
            return
            
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            title="Save Drawing"
        )
        
        if filename:
            # Get canvas dimensions
            canvas_width = self.drawing_canvas.winfo_width()
            canvas_height = self.drawing_canvas.winfo_height()
            
            # Create image from canvas
            try:
                import cv2
                import numpy as np
                from PIL import Image, ImageDraw
                
                # Create a white image
                img = Image.new('RGB', (canvas_width, canvas_height), 'white')
                draw = ImageDraw.Draw(img)
                
                # Get all canvas items and draw them
                for item in self.drawing_canvas.find_all():
                    coords = self.drawing_canvas.coords(item)
                    if len(coords) >= 4:
                        width = float(self.drawing_canvas.itemcget(item, 'width') or 1)
                        width = int(width)  # Convert float to int
                        for i in range(0, len(coords)-2, 2):
                            draw.line([coords[i], coords[i+1], coords[i+2], coords[i+3]], 
                                    fill='black', width=width)
                
                # Save the image
                img.save(filename)
                messagebox.showinfo("Success", f"Drawing saved as {filename}")
                
            except ImportError:
                messagebox.showerror("Error", "PIL library required for saving drawings")
    
    def use_drawing(self):
        """Use the current drawing as input"""
        if not hasattr(self, 'drawing_canvas'):
            return
            
        try:
            # Get canvas dimensions
            canvas_width = self.drawing_canvas.winfo_width()
            canvas_height = self.drawing_canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                messagebox.showwarning("Warning", "Please draw something first!")
                return
            
            # Create temporary file
            import tempfile
            from PIL import Image, ImageDraw
            
            # Create a white image
            img = Image.new('RGB', (canvas_width, canvas_height), 'white')
            draw = ImageDraw.Draw(img)
            
            # Get all canvas items and draw them
            items_found = False
            for item in self.drawing_canvas.find_all():
                coords = self.drawing_canvas.coords(item)
                if len(coords) >= 4:
                    items_found = True
                    width = float(self.drawing_canvas.itemcget(item, 'width') or 1)
                    width = int(width)  # Convert float to int
                    for i in range(0, len(coords)-2, 2):
                        draw.line([coords[i], coords[i+1], coords[i+2], coords[i+3]], 
                                fill='black', width=width)
            
            if not items_found:
                messagebox.showwarning("Warning", "Please draw something first!")
                return
            
            # Save to temporary file
            self.temp_drawing_path = os.path.join(tempfile.gettempdir(), "temp_drawing.png")
            img.save(self.temp_drawing_path)
            
            # Update UI
            self.image_path.set(self.temp_drawing_path)
            self.file_label.config(text=f"Drawing: {os.path.basename(self.temp_drawing_path)}")
            
            # Enable face drawing button when drawing is created
            self.face_drawing_btn.config(state='normal')
            self.caricature_btn.config(state='normal')
            
            self.status_text.set("Drawing ready! Processing...")
            
            # Load preview of the drawing
            self.load_preview_image()
            
            # Automatically process the drawing
            self.auto_process_image()
            
            # Close drawing window
            self.drawing_window.destroy()
            
        except ImportError:
            messagebox.showerror("Error", "PIL library required for processing drawings")
        except Exception as e:
            messagebox.showerror("Error", f"Error processing drawing: {str(e)}")

    def browse_image(self):
        """
        Browse for image file using file dialog.
        
        Automatically loads and processes the selected image.
        """
        filetypes = [
            ("Image files", "*.jpg *.jpeg *.png *.bmp"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Select Image File",
            filetypes=filetypes
        )
        
        if filename:
            self.image_path.set(filename)
            self.file_label.config(text=f"Selected: {filename.split('/')[-1]}", fg='#333')
            
            # Enable face drawing button when image is loaded
            self.face_drawing_btn.config(state='normal')
            self.caricature_btn.config(state='normal')
            
            self.load_preview_image()
            self.status_text.set("Image loaded - processing...")
            # Automatically process the image
            self.auto_process_image()
    
    def load_preview_image(self):
        """
        Load and display preview image in the original image canvas.
        
        Resizes the image to fit the preview area while maintaining aspect ratio.
        """
        try:
            # Load with OpenCV
            image = cv2.imread(self.image_path.get())
            if image is None:
                return
            
            # Convert BGR to RGB for display
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Resize for preview while maintaining aspect ratio
            h, w = image_rgb.shape[:2]
            scale = min(self.PREVIEW_WIDTH/w, self.PREVIEW_HEIGHT/h)
            new_w, new_h = int(w*scale), int(h*scale)
            image_resized = cv2.resize(image_rgb, (new_w, new_h))
            
            # Convert to PhotoImage for tkinter
            pil_image = Image.fromarray(image_resized)
            self.preview_image = ImageTk.PhotoImage(pil_image)
            
            # Display centered in canvas
            self.original_canvas.delete("all")
            x = (self.PREVIEW_WIDTH - new_w) // 2
            y = (self.PREVIEW_HEIGHT - new_h) // 2
            self.original_canvas.create_image(x, y, anchor=tk.NW, image=self.preview_image)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def toggle_connection(self):
        """Toggle robot connection"""
        self._save_config()
        if not self.is_connected:
            # Connect
            self.status_text.set("Connecting to robot...")
            self.connect_btn.config(state='disabled')
            thread = threading.Thread(target=self._connect_thread)
            thread.daemon = True
            thread.start()
        else:
            # Disconnect
            self.drawer.disconnect()
            self.is_connected = False
            self.connect_btn.config(text="Connect", bg='#FF9800')
            self.conn_status_label.config(text="⚫ Not Connected", fg='#f44336')
            self.get_pic_btn.config(state='disabled')  # Disable get picture button
            self.status_text.set("Disconnected from robot")
    
    def _connect_thread(self):
        """Connect in background thread"""
        try:
            ip = self.robot_ip.get().strip()
            port = int(self.robot_port.get().strip())
            
            # Create new drawer with custom connection
            self.drawer = RobotDrawer(
                ip=ip, 
                port=port, 
                max_x=self.max_x.get(), 
                max_y=self.max_y.get(), 
                enable_tsp=self.enable_tsp.get(),
                use_center_origin=self.use_center_origin.get(),
                margin_x=self.margin_x.get(),
                margin_y=self.margin_y.get()
            )
            success = self.drawer.connect()
            
            if success:
                self.root.after(0, self._connection_success)
            else:
                self.root.after(0, self._connection_failed)
        except Exception as e:
            self.root.after(0, lambda: self._connection_error(str(e)))
    
    def _connection_success(self):
        """Handle successful connection"""
        self.is_connected = True
        self.connect_btn.config(text="Disconnect", bg='#f44336', state='normal')
        self.conn_status_label.config(text="🟢 Connected", fg='#4CAF50')
        self.get_pic_btn.config(state='normal')  # Enable get picture button
        
        # Apply current settings to robot
        if hasattr(self.drawer, 'robot') and self.drawer.robot:
            self.drawer.robot.set_batch_mode(self.use_batch_mode.get())
            self.drawer.robot.set_coordinate_system(self.use_center_origin.get())
        
        self.status_text.set("Connected to robot successfully")
    
    def _connection_failed(self):
        """Handle connection failure"""
        self.connect_btn.config(state='normal')
        self.get_pic_btn.config(state='disabled')  # Disable get picture button
        self.status_text.set("Failed to connect to robot")
        messagebox.showerror("Connection Error", "Could not connect to robot. Please check IP and port.")
    
    def _connection_error(self, error):
        """Handle connection error"""
        self.connect_btn.config(state='normal')
        self.get_pic_btn.config(state='disabled')  # Disable get picture button
        self.status_text.set("Connection error")
        messagebox.showerror("Error", f"Connection error: {error}")
    
    def get_picture_from_robot(self):
        """Get picture from robot camera"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to robot first")
            return
        
        self.status_text.set("Getting picture from robot...")
        self.get_pic_btn.config(state='disabled')
        
        thread = threading.Thread(target=self._get_picture_thread)
        thread.daemon = True
        thread.start()
    
    def ready_robot_without_camera(self):
        """Ready robot without camera initialization"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to robot first")
            return
        
        self.status_text.set("Preparing robot without camera...")
        self.ready_btn.config(state='disabled')
        
        thread = threading.Thread(target=self._ready_robot_thread)
        thread.daemon = True
        thread.start()
    
    def _ready_robot_thread(self):
        """Ready robot without camera in background thread"""
        try:
            # Send READY command to robot
            if self.drawer.robot and self.drawer.robot.socket:
                success = self.drawer.robot.start_without_camera()
                
                if success:
                    self.root.after(0, self._ready_robot_success)
                else:
                    self.root.after(0, self._ready_robot_failed)
            else:
                self.root.after(0, self._ready_robot_failed)
                
        except Exception as e:
            self.root.after(0, lambda: self._ready_robot_error(str(e)))
    
    def _ready_robot_success(self):
        """Handle successful robot ready"""
        self.ready_btn.config(state='normal')
        self.status_text.set("Robot ready for manual positioning - place paper and start drawing!")
        messagebox.showinfo("Success", "Robot is ready! Please manually position your paper in the workspace.")
    
    def _ready_robot_failed(self):
        """Handle robot ready failure"""
        self.ready_btn.config(state='normal')
        self.status_text.set("Failed to ready robot")
        messagebox.showerror("Error", "Failed to ready robot. Please check connection.")
    
    def _ready_robot_error(self, error):
        """Handle robot ready error"""
        self.ready_btn.config(state='normal')
        self.status_text.set("Robot ready error")
        messagebox.showerror("Error", f"Robot ready error: {error}")

    def _get_picture_thread(self):
        """Get picture from robot in background thread"""
        import subprocess
        import os
        
        try:
            # Send get_pic command to robot and wait for OK response
            if self.drawer.robot and self.drawer.robot.socket:
                print("Sending get_pic command...")
                success = self.drawer.robot._send_command("get_pic\n", wait_response=True)
                
                if not success:
                    print("Failed to send get_pic command")
                    self.root.after(0, self._get_picture_failed)
                    return
                
                print("Robot confirmed picture taken (OK received)")
                
                # Delete old image.bmp if it exists
                image_path = os.path.join(os.getcwd(), "image.bmp")
                if os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                        print("Deleted old image.bmp")
                    except Exception as e:
                        print(f"Could not delete old image.bmp: {e}")
                
                # Now run bruh.py to download the fresh image
                downloader_path = os.path.join(os.getcwd(), "robot_ftp_downloader.py")
                if os.path.exists(downloader_path):
                    print("Running robot_ftp_downloader.py to download image...")
                    try:
                        result = subprocess.run(["python", "robot_ftp_downloader.py"], 
                                              capture_output=True, text=True, 
                                              cwd=os.getcwd(), timeout=30)
                        
                        if result.returncode == 0:
                            print("robot_ftp_downloader.py completed successfully")
                        else:
                            print(f"robot_ftp_downloader.py failed: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        print("robot_ftp_downloader.py timed out")
                    except Exception as e:
                        print(f"robot_ftp_downloader.py error: {e}")
                
                # Check if fresh image exists and load it
                if os.path.exists(image_path):
                    print("Fresh image.bmp found, loading...")
                    self.root.after(0, lambda: self._load_robot_image(image_path))
                else:
                    print("No image.bmp found after robot_ftp_downloader.py")
                    self.root.after(0, self._get_picture_no_image)
            else:
                self.root.after(0, self._get_picture_failed)
                
        except Exception as e:
            print(f"Get picture error: {e}")
            self.root.after(0, lambda: self._get_picture_error(str(e)))
    
    def _load_robot_image(self, image_path):
        """Load the robot image into the GUI"""
        try:
            # Switch to load mode if not already
            self.drawing_mode.set("load")
            self.on_mode_change()
            
            # Set the image path
            self.image_path.set(image_path)
            self.file_label.config(text="Robot Camera: image.bmp", fg='#333')
            
            # Enable face drawing button when robot image is loaded
            self.face_drawing_btn.config(state='normal')
            self.caricature_btn.config(state='normal')
            
            # Load preview
            self.load_preview_image()
            
            # Automatically process the image
            self.status_text.set("Robot image loaded - processing...")
            self.auto_process_image()
            
            self.get_pic_btn.config(state='normal')
            messagebox.showinfo("Success", "Picture captured from robot camera!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load robot image: {e}")
            self.get_pic_btn.config(state='normal')
            self.status_text.set("Failed to load robot image")
    
    def _get_picture_failed(self):
        """Handle get picture failure"""
        self.get_pic_btn.config(state='normal')
        self.status_text.set("Failed to get picture from robot")
        messagebox.showerror("Error", "Failed to send get_pic command to robot")
    
    def _get_picture_no_image(self):
        """Handle case where image.bmp doesn't exist"""
        self.get_pic_btn.config(state='normal')
        self.status_text.set("No image received from robot")
        messagebox.showwarning("Warning", "No image.bmp file found after running robot_ftp_downloader.py")
    
    def _get_picture_error(self, error):
        """Handle get picture error"""
        self.get_pic_btn.config(state='normal')
        self.status_text.set("Get picture error")
        messagebox.showerror("Error", f"Get picture error: {error}")
    
    def auto_process_image(self):
        """Automatically process the selected image or drawing"""
        # Small delay to let UI update
        self.root.after(100, self._start_auto_processing)
    
    def _start_auto_processing(self):
        """Start automatic processing"""
        self.progress_indicator.config(text="⏳ Processing...")
        
        thread = threading.Thread(target=self._process_thread)
        thread.daemon = True
        thread.start()
    
    def process_image(self):
        """Process the selected image or drawing"""
        # Determine current path based on mode
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            # In draw mode, use drawing path
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            # In load mode, use file path
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if not current_path:
            if self.drawing_mode.get() == "draw":
                messagebox.showwarning("Warning", "Please create a drawing first")
            else:
                messagebox.showwarning("Warning", "Please select an image first")
            return
        
        self.status_text.set("Processing image...")
        self.process_btn.config(state='disabled')
        self.progress_indicator.config(text="⏳ Processing...")
        
        thread = threading.Thread(target=self._process_thread)
        thread.daemon = True
        thread.start()
    
    def _process_thread(self):
        """Process image in background"""
        try:
            # Determine current path based on mode (same logic as process_image)
            current_path = None
            
            if self.drawing_mode.get() == "draw":
                # In draw mode, use drawing path
                if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                    current_path = self.temp_drawing_path
            else:
                # In load mode, use file path
                if self.image_path.get():
                    current_path = self.image_path.get()
            
            if not current_path:
                self.root.after(0, self._process_failed)
                return
            
            # Prepare logo settings
            logo_settings = {
                'enabled': self.enable_logo.get(),
                'corner': 'bottom_right',  # Always use bottom_right corner
                'size': self.logo_size.get()
            }
            
            success = self.drawer.load_image(
                current_path,
                precision=self.quality_var.get(),
                detection_method=self.detection_method.get(),
                logo_settings=logo_settings
            )
            
            if success:
                self.root.after(0, self._process_success)
            else:
                self.root.after(0, self._process_failed)
        except Exception as e:
            self.root.after(0, lambda: self._process_error(str(e)))
    
    def _process_success(self):
        """Handle successful processing"""
        self.is_processed = True
        self.progress_indicator.config(text="✅ Ready to Draw")
        self.status_text.set("Image processed successfully - ready to draw!")
        
        if self.is_connected:
            self.draw_btn.config(state='normal')
        
        # Enable face drawing button when image is processed
        self.face_drawing_btn.config(state='normal')
        self.caricature_btn.config(state='normal')
        
        # Update robot path preview
        self.update_robot_preview()
    
    def _process_failed(self):
        """Handle processing failure"""
        self.progress_indicator.config(text="❌ Failed")
        self.status_text.set("Processing failed")
        messagebox.showerror("Error", "Failed to process image")
    
    def _process_error(self, error):
        """Handle processing error"""
        self.progress_indicator.config(text="❌ Error")
        self.status_text.set("Processing error")
        messagebox.showerror("Error", f"Processing error: {error}")
    
    def update_robot_preview(self):
        """Update robot path preview with current coordinate system"""
        try:
            # Check if we need to recreate the figure with new aspect ratio
            max_x = self.max_x.get()
            max_y = self.max_y.get()
            new_aspect_ratio = max_x / max_y
            
            # Get current figure size and calculate current aspect ratio
            current_fig_size = self.fig.get_size_inches()
            current_aspect_ratio = current_fig_size[0] / current_fig_size[1]
            
            # If aspect ratios are significantly different, recreate the figure
            if abs(new_aspect_ratio - current_aspect_ratio) > 0.1:
                # Calculate new figure size to match drawing area aspect ratio
                fig_width = 4.0
                fig_height = fig_width / new_aspect_ratio
                # Limit height to reasonable range
                fig_height = min(4.0, max(2.0, fig_height))
                
                # Recreate the figure with correct aspect ratio
                self.fig.set_size_inches(fig_width, fig_height)
            
            self.ax.clear()
            
            # Set coordinate system based on user selection
            use_center = self.use_center_origin.get()
            
            if use_center:
                # Center-based coordinate system (0,0 at center)
                self.ax.set_xlim(-max_x/2, max_x/2)
                self.ax.set_ylim(-max_y/2, max_y/2)
                origin_text = "Center (0,0)"
                origin_x, origin_y = 0, 0
            else:
                # Corner-based coordinate system (0,0 at corner)
                self.ax.set_xlim(0, max_x)
                self.ax.set_ylim(0, max_y)
                origin_text = "Corner (0,0)"
                origin_x, origin_y = 0, 0
            
            self.ax.set_xlabel('X (mm)', fontsize=9)
            self.ax.set_ylabel('Y (mm)', fontsize=9)
            self.ax.grid(True, alpha=0.3)
            
            # Set equal aspect ratio so 1mm = 1mm visually
            self.ax.set_aspect('equal', adjustable='box')
            
            # Draw center axes only for center coordinate system
            if use_center:
                self.ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
                self.ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            
            # Draw drawing area boundary
            if use_center:
                boundary_x = [-max_x/2, max_x/2, max_x/2, -max_x/2, -max_x/2]
                boundary_y = [-max_y/2, -max_y/2, max_y/2, max_y/2, -max_y/2]
                # Draw margin boundaries (effective drawing area)
                margin_x = self.margin_x.get()
                margin_y = self.margin_y.get()
                effective_boundary_x = [-(max_x/2-margin_x), (max_x/2-margin_x), (max_x/2-margin_x), -(max_x/2-margin_x), -(max_x/2-margin_x)]
                effective_boundary_y = [-(max_y/2-margin_y), -(max_y/2-margin_y), (max_y/2-margin_y), (max_y/2-margin_y), -(max_y/2-margin_y)]
            else:
                boundary_x = [0, max_x, max_x, 0, 0]
                boundary_y = [0, 0, max_y, max_y, 0]
                # Draw margin boundaries (effective drawing area)
                margin_x = self.margin_x.get()
                margin_y = self.margin_y.get()
                effective_boundary_x = [margin_x, max_x-margin_x, max_x-margin_x, margin_x, margin_x]
                effective_boundary_y = [margin_y, margin_y, max_y-margin_y, max_y-margin_y, margin_y]
            
            self.ax.plot(boundary_x, boundary_y, 'k--', linewidth=2, alpha=0.5, label='Workspace Area')
            
            # Show effective drawing area (after margins) in green
            if margin_x > 0 or margin_y > 0:
                self.ax.plot(effective_boundary_x, effective_boundary_y, 'g-', linewidth=1.5, alpha=0.7, label='Drawing Area (with margins)')
            
            # Mark origin point
            self.ax.plot(origin_x, origin_y, 'r+', markersize=8, markeredgewidth=2, label=origin_text)
            
            if not self.drawer.drawing_points:
                # Position text based on coordinate system
                text_x = 0 if use_center else max_x/2
                text_y = 0 if use_center else max_y/2
                coord_info = "center" if use_center else "corner"
                self.ax.text(text_x, text_y, f'No path generated\n(0,0) at {coord_info}', 
                           ha='center', va='center', fontsize=9, color='#999')
                self.fig.tight_layout()
                self.canvas_widget.draw()
                return
            
            # Plot paths (coordinates should already be in the correct system from transformer)
            colors = plt.cm.tab10(np.linspace(0, 1, len(self.drawer.drawing_points)))
            
            for i, path in enumerate(self.drawer.drawing_points):
                if len(path) > 0:
                    x_coords = [p[0] for p in path]
                    y_coords = [p[1] for p in path]
                    self.ax.plot(x_coords, y_coords, 'o-', color=colors[i], 
                               linewidth=2, markersize=1.5)
            
            total_points = sum(len(path) for path in self.drawer.drawing_points)
            coord_info = "center" if use_center else "corner"
            margin_info = f" (margins: {self.margin_x.get()}x{self.margin_y.get()}mm)" if self.margin_x.get() > 0 or self.margin_y.get() > 0 else ""
            
            self.ax.set_title(f'{len(self.drawer.drawing_points)} paths, {total_points} points ({coord_info} origin{margin_info})', 
                            fontsize=10)
            
            self.fig.tight_layout()
            self.canvas_widget.draw()
            
        except Exception as e:
            print(f"Preview error: {e}")
    
    def start_robot_drawing(self):
        """Start the robot drawing process"""
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to robot first")
            return
        
        if not self.is_processed:
            messagebox.showwarning("Warning", "Please process an image first")
            return
        
        # Calculate estimated time
        total_points = sum(len(path) for path in self.drawer.drawing_points)
        
        # Determine which command will be sent based on coordinate system
        coord_system = "center" if self.use_center_origin.get() else "corner"
        command_type = "START" if self.use_center_origin.get() else "START_CORNER"
        
        # Confirm
        result = messagebox.askyesno(
            "Start Drawing", 
            f"Start drawing {len(self.drawer.drawing_points)} paths with {total_points} points?\n\n"
            f"Using ultra-fast mode with path optimization\n"
            f"Coordinate system: {coord_system} origin\n"
            f"Robot command: {command_type}\n\n"
            "The robot may take up to 90 seconds to initialize before beginning movement."
        )
        
        if result:
            import time
            self._draw_start_time = time.time()
            # Update robot with current coordinate system before starting
            if hasattr(self.drawer, 'robot') and self.drawer.robot:
                self.drawer.robot.set_coordinate_system(self.use_center_origin.get())
            # Show progress elements in status bar
            self.progress_container.pack(side=tk.RIGHT, before=self.progress_indicator)
            self.stop_btn.pack(pady=(10, 0))
            self.drawing_active = True
            self.status_text.set(f"Initializing robot with {coord_system} coordinates ({command_type})...")
            self.draw_btn.config(state='disabled')
            self.progress_indicator.config(text="🤖 Initializing...")
            # Setup progress tracking
            total_points = sum(len(path) for path in self.drawer.drawing_points)
            self.bottom_progress_bar.config(maximum=total_points)
            self.bottom_progress_bar.config(value=0)
            self.bottom_progress_label.config(text=f"0 / {total_points} points")
            thread = threading.Thread(target=self._draw_thread)
            thread.daemon = True
            thread.start()
    
    def emergency_stop(self):
        """Emergency stop the drawing process"""
        if self.drawing_active:
            self.drawing_active = False
            try:
                # Send emergency stop to robot
                if self.drawer.robot and self.drawer.robot.socket:
                    self.drawer.send_pen_up()  # Lift pen first
                    self.drawer.send_stop()    # Send stop command
                    self.status_text.set("Emergency stop sent to robot")
                else:
                    self.status_text.set("Drawing stopped (no robot connection)")
                messagebox.showinfo("Stop", "Drawing process stopped and robot commands halted")
            except Exception as e:
                messagebox.showerror("Error", f"Could not stop robot: {e}")
                self.status_text.set("Stop command failed")
            
            # Hide progress elements
            self.progress_container.pack_forget()
            self.stop_btn.pack_forget()
            self.draw_btn.config(state='normal')
            self.progress_indicator.config(text="⏹ Stopped")
    
    def _draw_thread(self):
        """
        Execute drawing in background with real robot synchronization.
        
        Protocol:
        1. Send "START" command and wait for "OK" response
        2. Begin drawing sequence (PEN_UP, MOVE, PEN_DOWN, MOVE, etc.)
        3. Send "STOP" command when complete
        """
        try:
            # Check robot connection
            if not self.drawer.robot or not self.drawer.robot.socket:
                raise Exception("No robot connection")
            
            # Send START command and wait for OK response
            coord_system = "center" if self.use_center_origin.get() else "corner"
            command_type = "START" if self.use_center_origin.get() else "START_CORNER"
            
            print(f"Sending {command_type} command to robot...")
            self.root.after(0, lambda: self.status_text.set(f"Sending {command_type} command to robot..."))
            
            success = self.drawer.robot.send_start()  # This automatically chooses START vs START_CORNER
            if not success:
                print(f"Robot did not respond with OK to {command_type} command")
                raise Exception(f"Failed to receive OK response from robot after {command_type} command. Robot may not be ready.")
            
            print(f"Robot confirmed {command_type} command (OK received) - beginning drawing sequence...")
            self.root.after(0, lambda: self.status_text.set("Robot ready - starting drawing sequence..."))
            
            # Track progress
            total_points = sum(len(path) for path in self.drawer.drawing_points)
            current_point = 0
            
            print("Starting robot drawing with progress tracking...")
            
            try:
                # Update status to show drawing has begun
                self.root.after(0, lambda: self.status_text.set("Drawing in progress..."))
                self.root.after(0, lambda: self.progress_indicator.config(text="🎨 Drawing..."))
                
                # Use optimized drawing with real batch progress tracking
                print("Starting ultra-fast drawing with batch progress tracking...")
                
                # Create progress callback that updates GUI
                def progress_callback(current_batch, total_batches, points_sent, total_points):
                    if self.drawing_active:  # Only update if drawing is still active
                        percent = (points_sent / total_points) * 100 if total_points > 0 else 0
                        self.root.after(0, self._update_progress, points_sent, total_points, percent)
                
                # Start the optimized drawing process with progress tracking
                success = self.drawer.draw(progress_callback=progress_callback)
                
                if success:
                    print("Robot drawing completed!")
                    self.root.after(0, self._draw_success)
                else:
                    print("Drawing failed")
                    self.root.after(0, self._draw_failed)
                
            except Exception as e:
                print(f"Drawing error: {e}")
                # Try to safely stop robot
                try:
                    self.drawer.send_pen_up()
                    self.drawer.send_stop()
                except:
                    pass
                self.root.after(0, lambda: self._draw_error(str(e)))
                
        except Exception as e:
            self.root.after(0, lambda: self._draw_error(str(e)))
    
    def _update_progress(self, current, total, percent):
        """Update progress bar in main thread"""
        if hasattr(self, 'bottom_progress_bar'):
            self.bottom_progress_bar.config(value=current)
            self.bottom_progress_label.config(text=f"{current} / {total} points ({percent:.1f}%)")
    
    def _draw_success(self):
        """Handle successful drawing"""
        import time
        self.drawing_active = False
        self.draw_btn.config(state='normal')
        self.progress_indicator.config(text="🎉 Complete")
        self.status_text.set("Drawing completed successfully!")
        # Hide progress elements
        self.progress_container.pack_forget()
        self.stop_btn.pack_forget()
        elapsed = None
        if hasattr(self, '_draw_start_time'):
            elapsed = time.time() - self._draw_start_time
        if elapsed is not None:
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            msg = f"Drawing completed successfully!\n\nTime taken: {mins} min {secs} sec"
        else:
            msg = "Drawing completed successfully!"
        messagebox.showinfo("Success", msg)
    
    def _draw_failed(self):
        """Handle drawing failure"""
        self.drawing_active = False
        self.draw_btn.config(state='normal')
        self.progress_indicator.config(text="❌ Failed")
        self.status_text.set("Drawing failed")
        
        # Hide progress elements
        self.progress_container.pack_forget()
        self.stop_btn.pack_forget()
        
        messagebox.showerror("Error", "Drawing failed")
    
    def _draw_error(self, error):
        """Handle drawing error"""
        self.drawing_active = False
        self.draw_btn.config(state='normal')
        self.progress_indicator.config(text="❌ Error")
        self.status_text.set("Drawing error")
        
        # Hide progress elements
        self.progress_container.pack_forget()
        self.stop_btn.pack_forget()
        
        messagebox.showerror("Error", f"Drawing error: {error}")
    
    def convert_to_face_drawing(self):
        """Convert current image to line art using convert_to_lineart.py"""
        # Determine current path based on mode
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if not current_path:
            messagebox.showwarning("Warning", "Please load an image or create a drawing first")
            return
        
        # Disable the button during processing
        self.face_drawing_btn.config(state='disabled')
        self.status_text.set("Converting to line art...")
        self.progress_indicator.config(text="🎨 Converting...")
        
        # Run conversion in background thread
        thread = threading.Thread(target=self._face_drawing_thread, args=(current_path,))
        thread.daemon = True
        thread.start()
    
    def _face_drawing_thread(self, image_path):
        """Convert image to line art in background thread"""
        try:
            # Import the convert_to_lineart module
            from convert_to_lineart import convert_to_lineart
            
            # Convert the image to line art
            convert_to_lineart(image_path)
            
            # Check if out.png was created
            output_path = os.path.join(os.getcwd(), "out.png")
            if os.path.exists(output_path):
                self.root.after(0, lambda: self._face_drawing_success(output_path))
            else:
                self.root.after(0, self._face_drawing_failed)
                
        except Exception as e:
            self.root.after(0, lambda: self._face_drawing_error(str(e)))
    
    def _face_drawing_success(self, output_path):
        """Handle successful face drawing conversion"""
        try:
            # Switch to load mode if not already
            self.drawing_mode.set("load")
            self.on_mode_change()
            
            # Update the image path to use the new line art
            self.image_path.set(output_path)
            self.file_label.config(text="Face Line Art: out.png", fg='#333')
            
            # Load preview of the line art
            self.load_preview_image()
            
            # Automatically process the line art
            self.status_text.set("Line art generated - processing for robot...")
            self.auto_process_image()
            
            # Re-enable the face drawing button
            self.face_drawing_btn.config(state='normal')
            self.progress_indicator.config(text="✅ Line Art Ready")
            
            messagebox.showinfo("Success", "Image converted to line art successfully!\nUsing out.png for robot drawing.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load line art: {e}")
            self.face_drawing_btn.config(state='normal')
            self.status_text.set("Failed to load line art")
            self.progress_indicator.config(text="❌ Failed")
    
    def _face_drawing_failed(self):
        """Handle face drawing conversion failure"""
        self.face_drawing_btn.config(state='normal')
        self.progress_indicator.config(text="❌ Failed")
        self.status_text.set("Line art conversion failed")
        messagebox.showerror("Error", "Failed to generate line art. Check if out.png was created.")
    
    def _face_drawing_error(self, error):
        """Handle face drawing conversion error"""
        self.face_drawing_btn.config(state='normal')
        self.progress_indicator.config(text="❌ Error")
        self.status_text.set("Line art conversion error")
        messagebox.showerror("Error", f"Line art conversion error: {error}")
    
    def convert_to_caricature(self):
        """Convert current image to caricature using convert_to_lineart.py"""
        # Determine current path based on mode
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        else:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if not current_path:
            messagebox.showwarning("Warning", "Please load an image or create a drawing first")
            return
        
        # Disable the button during processing
        self.caricature_btn.config(state='disabled')
        self.status_text.set("Converting to caricature...")
        self.progress_indicator.config(text="🎭 Converting...")
        
        # Run conversion in background thread
        thread = threading.Thread(target=self._caricature_thread, args=(current_path,))
        thread.daemon = True
        thread.start()
    
    def _caricature_thread(self, image_path):
        """Convert image to caricature in background thread"""
        try:
            # Import the convert_to_lineart module
            from convert_to_lineart import convert_to_lineart
            
            # Convert the image to caricature using caricature prompt
            convert_to_lineart(image_path, prompt_type="caricature")
            
            # Check if out.png was created
            output_path = os.path.join(os.getcwd(), "out.png")
            if os.path.exists(output_path):
                self.root.after(0, lambda: self._caricature_success(output_path))
            else:
                self.root.after(0, self._caricature_failed)
                
        except Exception as e:
            self.root.after(0, lambda: self._caricature_error(str(e)))
    
    def _caricature_success(self, output_path):
        """Handle successful caricature conversion"""
        try:
            # Switch to load mode if not already
            self.drawing_mode.set("load")
            self.on_mode_change()
            
            # Update the image path to use the new caricature
            self.image_path.set(output_path)
            self.file_label.config(text="Caricature: out.png", fg='#333')
            
            # Load preview of the caricature
            self.load_preview_image()
            
            # Automatically process the caricature
            self.status_text.set("Caricature generated - processing for robot...")
            self.auto_process_image()
            
            # Re-enable the caricature button
            self.caricature_btn.config(state='normal')
            self.progress_indicator.config(text="✅ Caricature Ready")
            
            messagebox.showinfo("Success", "Image converted to caricature successfully!\nUsing out.png for robot drawing.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load caricature: {e}")
            self.caricature_btn.config(state='normal')
            self.status_text.set("Failed to load caricature")
            self.progress_indicator.config(text="❌ Failed")
    
    def _caricature_failed(self):
        """Handle caricature conversion failure"""
        self.caricature_btn.config(state='normal')
        self.progress_indicator.config(text="❌ Failed")
        self.status_text.set("Caricature conversion failed")
        messagebox.showerror("Error", "Failed to generate caricature. Check if out.png was created.")
    
    def _caricature_error(self, error):
        """Handle caricature conversion error"""
        self.caricature_btn.config(state='normal')
        self.progress_indicator.config(text="❌ Error")
        self.status_text.set("Caricature conversion error")
        messagebox.showerror("Error", f"Caricature conversion error: {error}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = SimpleRobotGUI()
    app.run()


if __name__ == "__main__":
    main()

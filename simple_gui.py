"""
Simple, user-friendly GUI for Robot Drawing System.

This module provides a clean, intuitive graphical interface for the Robot Drawing System.
It offers three main input methods:
1. Load image files (JPG, PNG, BMP, etc.)
2. Create drawings using an interactive canvas
3. Generate images from text descriptions using AI

Features:
- Real-time image processing and preview
- Robot connection management
- Progress tracking during drawing operations
- Template shapes for quick testing
- TSP optimization controls
- Quality/precision settings
- AI-powered text-to-image generation

The GUI is designed to be accessible to users of all technical levels while providing
access to advanced features for power users.

Version: 1.0 - EXPO MODE
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import subprocess
import os
from datetime import datetime
import webbrowser
from PIL import Image, ImageTk
import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import math

from voice_commands import VoiceCommandListener

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
    DEFAULT_ROBOT_PORT_L = "1026"  # Left robot port for dual-arm mode
    
    # UI dimensions and colors - Optimized for 1920x1080 display
    WINDOW_WIDTH = 1600
    WINDOW_HEIGHT = 900
    PREVIEW_WIDTH = 640
    PREVIEW_HEIGHT = 480 

    # Button fonts for larger UI elements 
    BUTTON_FONT = ('Arial', 22,'bold')
    SMALL_BUTTON_FONT = ('Arial', 12)
    # Uniform button sizing (width in chars, height via padding)
    BUTTON_WIDTH = 18
    BUTTON_PADX = 25
    BUTTON_PADY = 15
    
    # Color scheme
    # Primary palette: use only these colors + white background for a clean, consistent UI
    COLORS = {
        'background': 'white',            # white background requested
        'section_bg': 'white',
        # Use photo preview color for headers to keep contrast with white
        'header_bg': '#5FA8D3',
        'header_text': 'white',

        # Main palette
        'take_photo': '#1B4965',    # deep navy / primary
        'portrait': '#BEE9E8',      # light aqua
        'start_drawing': '#62B6CB', # cyan
        'caricature': '#CAE9FF',    # very light blue
        'photo_preview': '#5FA8D3', # medium blue
        'drawing_active': '#1B4965',    # deep navy

        # Borders / subtle fills should reuse palette entries
        'portrait_border': '#BEE9E8',
        'caricature_border': '#CAE9FF',

        # Map generic button states to palette
        'button_draw': '#62B6CB',   # use start_drawing color
        'button_stop': '#1B4965',   # use deep navy for stop to match palette
    }
    
    def make_touch_button(self, parent, text, bg, command, font=None, triangle_type=None, **kwargs):
        """Create a touch-friendly button with visual feedback on press/release"""
        if font is None:
            font = self.BUTTON_FONT
        
        # Create darker pressed color by reducing brightness
        def darken_color(color):
            # Simple darkening for touch feedback
            if color.startswith('#') and len(color) == 7:
                r = int(color[1:3], 16)
                g = int(color[3:5], 16)
                b = int(color[5:7], 16)
                # Darken by 20%
                r = max(0, int(r * 0.8))
                g = max(0, int(g * 0.8))
                b = max(0, int(b * 0.8))
                return f"#{r:02x}{g:02x}{b:02x}"
            return color
        
        pressed_bg = darken_color(bg)
        
        # Set defaults for common parameters if not provided
        if 'fg' not in kwargs:
            kwargs['fg'] = 'white'
        if 'relief' not in kwargs:
            kwargs['relief'] = tk.RAISED
        if 'bd' not in kwargs:
            kwargs['bd'] = 3
        if 'cursor' not in kwargs:
            kwargs['cursor'] = 'hand2'
        
        # Create button with touch feedback
        btn = tk.Button(parent, text=text, command=command, font=font, bg=bg, **kwargs)
        
        def on_press(event):
            btn.config(bg=pressed_bg)
            # Also blink the corresponding triangle if specified
            if triangle_type and hasattr(self, 'triangle_overlay') and self.triangle_overlay.winfo_exists():
                if triangle_type == "portrait":
                    self.triangle_overlay.itemconfig("portrait_triangle", fill=darken_color(self.COLORS['portrait']))
                elif triangle_type == "caricature":
                    self.triangle_overlay.itemconfig("caricature_triangle", fill=darken_color(self.COLORS['caricature']))
        
        def on_release(event):
            btn.config(bg=bg)
            # Restore triangle color if specified
            if triangle_type and hasattr(self, 'triangle_overlay') and self.triangle_overlay.winfo_exists():
                if triangle_type == "portrait":
                    self.triangle_overlay.itemconfig("portrait_triangle", fill=self.COLORS['portrait'])
                elif triangle_type == "caricature":
                    self.triangle_overlay.itemconfig("caricature_triangle", fill=self.COLORS['caricature'])
        
        btn.bind('<ButtonPress-1>', on_press)
        btn.bind('<ButtonRelease-1>', on_release)
        
        return btn
    
    def __init__(self):
        """Initialize the GUI application."""
        import json
        import os
        self.config_path = "robot_gui_config.json"
        self.config = self._load_config()

        self.root = tk.Tk()
        self.root.title("🤖 Robot Drawing System - EXPO MODE")
        self.root.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
        self.root.configure(bg=self.COLORS['background'])

        # Create a lightweight placeholder for legacy callers that expect self.file_label
        # The real `self.file_label` will be created in `create_image_section`; this avoids
        # attribute errors if other routines attempt to update it before the setup UI exists.
        try:
            if not hasattr(self, 'file_label'):
                self.file_label = tk.Label(self.root, text="No image selected", bg=self.COLORS['section_bg'])
        except Exception:
            # If Tk isn't fully ready, keep a None fallback
            self.file_label = None

        # Dual-arm mode state (must be after tk.Tk() and self is defined)
        self.dual_arm_mode = tk.BooleanVar(master=self.root, value=False)

        # Initialize robot drawer with TSP enabled by default and default dimensions
        self.drawer = RobotDrawer(max_x=290, max_y=210, enable_tsp=True, use_center_origin=True, margin_x=10, margin_y=10)

        # Initialize state variables
        self._init_variables()

        # Override defaults with config values if present
        if self.config.get("robot_ip"):
            self.robot_ip.set(self.config["robot_ip"])
        if self.config.get("robot_port"):
            self.robot_port.set(self.config["robot_port"])
        if self.config.get("robot_port_l"):
            self.robot_port_l.set(self.config["robot_port_l"])
        if self.config.get("use_center_origin") is not None:
            self.use_center_origin.set(self.config["use_center_origin"])
        if self.config.get("enable_logo") is not None:
            self.enable_logo.set(self.config["enable_logo"])
        if self.config.get("logo_size") is not None:
            self.logo_size.set(self.config["logo_size"])
        if self.config.get("enable_frame_filtering") is not None:
            self.enable_frame_filtering.set(self.config["enable_frame_filtering"])
        if self.config.get("max_x") is not None:
            self.max_x.set(self.config["max_x"])
        if self.config.get("max_y") is not None:
            self.max_y.set(self.config["max_y"])
        if self.config.get("margin_x") is not None:
            self.margin_x.set(self.config["margin_x"])
        if self.config.get("margin_y") is not None:
            self.margin_y.set(self.config["margin_y"])
        # Restore additional UI settings (quality, detection, modes, brush, dual-arm)
        if self.config.get("quality_var") is not None:
            try:
                self.quality_var.set(self.config["quality_var"])
            except Exception:
                pass
        if self.config.get("detection_method") is not None:
            try:
                self.detection_method.set(self.config["detection_method"])
            except Exception:
                pass
        if self.config.get("enable_tsp") is not None:
            try:
                self.enable_tsp.set(self.config["enable_tsp"])
            except Exception:
                pass
        if self.config.get("use_batch_mode") is not None:
            try:
                self.use_batch_mode.set(self.config["use_batch_mode"])
            except Exception:
                pass
        if self.config.get("drawing_mode") is not None:
            try:
                self.drawing_mode.set(self.config["drawing_mode"])
            except Exception:
                pass
        if self.config.get("brush_size") is not None:
            try:
                self.brush_size.set(self.config["brush_size"])
            except Exception:
                pass
        if self.config.get("dual_arm_mode") is not None:
            try:
                # stored as bool
                self.dual_arm_mode.set(self.config["dual_arm_mode"])
            except Exception:
                pass

        # Create the user interface (compact main view). Full setup is in a separate window.
        self.create_simple_interface()

        # Restore text prompt after UI is created
        if self.config.get("text_prompt") is not None:
            try:
                if hasattr(self, 'text_entry'):
                    self.text_entry.delete("1.0", tk.END)
                    self.text_entry.insert("1.0", self.config["text_prompt"])
            except Exception:
                pass

        # Start voice listener (background thread). Calls into _on_voice_command -> main thread dispatcher.
        try:
            self._voice_listener = VoiceCommandListener(callback=self._on_voice_command)
            self._voice_listener.start()
        except Exception:
            # If voice model not available or sound device missing, continue without voice control
            self._voice_listener = None

        # Restore forbidden buffer from config (created during UI setup)
        if self.config.get("forbidden_buffer") is not None:
            try:
                if hasattr(self, 'forbidden_buffer_var'):
                    self.forbidden_buffer_var.set(int(self.config.get("forbidden_buffer", 40)))
            except Exception:
                pass

        # Autosave on window close: ensure config persisted and robot disconnected
        try:
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        except Exception:
            pass

        # Update connection display with initial values
        self.root.after(100, self._update_connection_display)

        # Try to load custom gear image on startup
        self.load_custom_gear_image()

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
                "robot_port_l": self.robot_port_l.get(),
                "use_center_origin": self.use_center_origin.get(),
                "enable_logo": self.enable_logo.get(),
                "logo_size": self.logo_size.get(),
                "enable_frame_filtering": self.enable_frame_filtering.get(),
                "max_x": self.max_x.get(),
                "max_y": self.max_y.get(),
                "margin_x": self.margin_x.get(),
                "margin_y": self.margin_y.get()
            }
            # Additional UI settings to persist 
            try:
                config["quality_var"] = self.quality_var.get()
            except Exception:
                config["quality_var"] = "high"
            try:
                config["detection_method"] = self.detection_method.get()
            except Exception:
                config["detection_method"] = "threshold"
            try:
                config["enable_tsp"] = bool(self.enable_tsp.get())
            except Exception:
                config["enable_tsp"] = True
            try:
                config["use_batch_mode"] = bool(self.use_batch_mode.get())
            except Exception:
                config["use_batch_mode"] = True
            try:
                config["drawing_mode"] = self.drawing_mode.get()
            except Exception:
                config["drawing_mode"] = "load"
            try:
                config["brush_size"] = int(self.brush_size.get())
            except Exception:
                config["brush_size"] = 3
            try:
                config["dual_arm_mode"] = bool(self.dual_arm_mode.get())
            except Exception:
                config["dual_arm_mode"] = False
            # Save text prompt for text generation mode
            try:
                if hasattr(self, 'text_entry'):
                    config["text_prompt"] = self.text_entry.get("1.0", tk.END).strip()
                else:
                    config["text_prompt"] = ""
            except Exception:
                config["text_prompt"] = ""
            # Persist forbidden buffer if present
            try:
                config["forbidden_buffer"] = int(self.forbidden_buffer_var.get()) if hasattr(self, 'forbidden_buffer_var') else 40
            except Exception:
                config["forbidden_buffer"] = 40

            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception:
            pass
    
    def _init_variables(self):
        """Initialize all GUI state variables."""
        # File and drawing state
        self.image_path = tk.StringVar()
        self.drawing_mode = tk.StringVar(value="load")  # "load", "draw", or "text"
        self.text_prompt = tk.StringVar()  # For text-to-image generation
        
        # Robot connection
        self.robot_ip = tk.StringVar(value=self.DEFAULT_ROBOT_IP)
        self.robot_port = tk.StringVar(value=self.DEFAULT_ROBOT_PORT)
        self.robot_port_l = tk.StringVar(value=self.DEFAULT_ROBOT_PORT_L)  # Left robot port
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
        
        # Frame filtering settings
        self.enable_frame_filtering = tk.BooleanVar(value=False)  # Frame filtering disabled by default
        
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
        
        # Forbidden buffer (for dual-arm mode)
        self.forbidden_buffer_var = tk.IntVar(value=40)
        
        # Triangle press state flags
        self.portrait_triangle_pressed = False
        self.caricature_triangle_pressed = False
    
    def create_simple_interface(self):
        """Create a 2x2 grid layout with tile buttons for expo."""
        # Main container with padding
        main_frame = tk.Frame(self.root, bg=self.COLORS['background'], padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Application title
        title_label = tk.Label(main_frame, text="🤖 Robot Drawing System", 
                    font=('Arial', 24, 'bold'), 
                    bg=self.COLORS['background'], fg=self.COLORS['take_photo'])
        title_label.pack(pady=(0, 10))
        
        subtitle_label = tk.Label(main_frame, text="Simple • Fast • Interactive Robot Art", 
                    font=('Arial', 14), 
                    bg=self.COLORS['background'], fg=self.COLORS['start_drawing'])
        subtitle_label.pack(pady=(0, 15))
        # Attempt to load company logo and place at top-right corner
        try:
            logo_path = os.path.join(os.path.dirname(__file__), 'logo_inlader.jpg')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                # Resize to a small corner icon while preserving aspect ratio
                max_size = (150, 150)
                try:
                    img.thumbnail(max_size, Image.LANCZOS)
                except Exception:
                    img.thumbnail(max_size)
                self.logo_image = ImageTk.PhotoImage(img)
                self.logo_label = tk.Label(main_frame, image=self.logo_image, bg=self.COLORS['background'], cursor='hand2')
                # Make logo clickable and open company site
                try:
                    self.logo_label.bind('<Button-1>', lambda e: webbrowser.open_new_tab('https://inlader.pl'))
                except Exception:
                    pass
                # Place in top-right using absolute placement relative to main_frame
                # small negative x to provide padding from right edge
                self.logo_label.place(relx=1.0, x=-10, y=10, anchor='ne')
        except Exception:
            # If logo can't be loaded, ignore silently
            pass
        
        # Create TRUE 2x2 grid layout 
        grid_frame = tk.Frame(main_frame, bg=self.COLORS['background'])
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for TRULY EQUAL distribution (2x2 grid)
        grid_frame.grid_rowconfigure(0, weight=1, minsize=200)
        grid_frame.grid_rowconfigure(1, weight=1, minsize=200)
        grid_frame.grid_columnconfigure(0, weight=1, minsize=400)  # Equal column widths
        grid_frame.grid_columnconfigure(1, weight=1, minsize=400)  # Equal column widths
        
        # Tile 1: Take Picture (Top Left) - Full button
        self.take_photo_btn = self.make_touch_button(grid_frame, 
                                      text="1. TAKE PICTURE\n\n📷",
                                      command=self.get_picture_from_robot,
                                      font=self.BUTTON_FONT, bg=self.COLORS['take_photo'], fg='white',
                                      relief=tk.RAISED, bd=3, cursor='hand2')
        self.take_photo_btn.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        # Tile 2: See Photo (Top Right) - Single column, equal size
        self.preview_frame = tk.Frame(grid_frame, bg=self.COLORS['photo_preview'], relief=tk.FLAT, bd=1)
        self.preview_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)  # NO COLUMNSPAN!
        
        # Fixed height header
        header_frame = tk.Frame(self.preview_frame, bg=self.COLORS['photo_preview'], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)  # Maintain fixed height
        
        tk.Label(header_frame, text="2. SEE YOUR PHOTO", font=self.BUTTON_FONT, 
                bg=self.COLORS['photo_preview'], fg='white').pack(pady=5)
        
        # Fixed size image preview container (use white background)
        preview_container = tk.Frame(self.preview_frame, bg='white', height=160)
        preview_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        preview_container.pack_propagate(False)  # Maintain fixed height to prevent ratio changes
        
    # Image preview with dynamic scaling
        self.preview_label = tk.Label(preview_container, text="Take a photo\nto see preview here", 
                        bg='white', 
                        font=('Arial', 14), relief=tk.SUNKEN, bd=0,
                        justify=tk.CENTER, fg=self.COLORS['take_photo'])
        self.preview_label.pack(fill=tk.BOTH, expand=True)
        
        # Bind resize event to refresh image scaling
        preview_container.bind('<Configure>', self.on_preview_resize)
        
        # Tile 3: Combined Portrait/Caricature with diagonal stairs effect - Single column, equal size
        # Style frame uses photo_preview color for a subtle band
        self.style_frame = tk.Frame(grid_frame, bg=self.COLORS['photo_preview'], relief=tk.RIDGE, bd=1)
        self.style_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=5)  # NO COLUMNSPAN!
        
        # Configure grid weights for the style frame (10 rows, 20 columns for ultra-fine triangle stairs)
        for i in range(20):
            self.style_frame.grid_columnconfigure(i, weight=1)
        for i in range(10):
            self.style_frame.grid_rowconfigure(i, weight=1)
        
        # Create ultra-granular diagonal triangle effect - Portrait (orange) upper left triangle
        # Row 0 - Full width Portrait
        self.portrait_btn1 = self.make_touch_button(
            self.style_frame, text="👤 PORTRAIT", font=("Arial", 15, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn1.grid(row=0, column=0, columnspan=20, sticky="nsew", padx=1, pady=1)
        
        # Row 1 - 18/20 width Portrait
        self.portrait_btn2 = self.make_touch_button(
            self.style_frame, text="Face Drawing", font=("Arial", 13, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn2.grid(row=1, column=0, columnspan=18, sticky="nsew", padx=1, pady=1)
        
        # Row 2 - 16/20 width Portrait
        self.portrait_btn3 = self.make_touch_button(
            self.style_frame, text="Style", font=("Arial", 12, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn3.grid(row=2, column=0, columnspan=16, sticky="nsew", padx=1, pady=1)
        
        # Row 3 - 14/20 width Portrait
        self.portrait_btn4 = self.make_touch_button(
            self.style_frame, text="Natural", font=("Arial", 11, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn4.grid(row=3, column=0, columnspan=14, sticky="nsew", padx=1, pady=1)
        
        # Row 4 - 12/20 width Portrait
        self.portrait_btn5 = self.make_touch_button(
            self.style_frame, text="Realistic", font=("Arial", 10, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn5.grid(row=4, column=0, columnspan=12, sticky="nsew", padx=1, pady=1)
        
        # Row 5 - 10/20 width Portrait
        self.portrait_btn6 = self.make_touch_button(
            self.style_frame, text="Art", font=("Arial", 9, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn6.grid(row=5, column=0, columnspan=10, sticky="nsew", padx=1, pady=1)
        
        # Row 6 - 8/20 width Portrait
        self.portrait_btn7 = self.make_touch_button(
            self.style_frame, text="Pro", font=("Arial", 8, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn7.grid(row=6, column=0, columnspan=8, sticky="nsew", padx=1, pady=1)
        
        # Row 7 - 6/20 width Portrait
        self.portrait_btn8 = self.make_touch_button(
            self.style_frame, text="✓", font=("Arial", 8, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn8.grid(row=7, column=0, columnspan=6, sticky="nsew", padx=1, pady=1)
        
        # Row 8 - 4/20 width Portrait
        self.portrait_btn9 = self.make_touch_button(
            self.style_frame, text="◆", font=("Arial", 7, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn9.grid(row=8, column=0, columnspan=4, sticky="nsew", padx=1, pady=1)
        
        # Row 9 - 2/20 width Portrait
        self.portrait_btn10 = self.make_touch_button(
            self.style_frame, text="•", font=("Arial", 7, "bold"),
            bg=self.COLORS['portrait'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("portrait"), triangle_type="portrait"
        )
        self.portrait_btn10.grid(row=9, column=0, columnspan=2, sticky="nsew", padx=1, pady=1)
        
        # Caricature (purple) lower right triangle - creating smooth stairs
        # Row 1 - 2/20 width Caricature (right side)
        self.caricature_btn1 = self.make_touch_button(
            self.style_frame, text="😄", font=("Arial", 13, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn1.grid(row=1, column=18, columnspan=2, sticky="nsew", padx=1, pady=1)
        
        # Row 2 - 4/20 width Caricature
        self.caricature_btn2 = self.make_touch_button(
            self.style_frame, text="Fun", font=("Arial", 12, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn2.grid(row=2, column=16, columnspan=4, sticky="nsew", padx=1, pady=1)
        
        # Row 3 - 6/20 width Caricature
        self.caricature_btn3 = self.make_touch_button(
            self.style_frame, text="Cartoon", font=("Arial", 11, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn3.grid(row=3, column=14, columnspan=6, sticky="nsew", padx=1, pady=1)
        
        # Row 4 - 8/20 width Caricature
        self.caricature_btn4 = self.make_touch_button(
            self.style_frame, text="Funny", font=("Arial", 10, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn4.grid(row=4, column=12, columnspan=8, sticky="nsew", padx=1, pady=1)
        
        # Row 5 - 10/20 width Caricature
        self.caricature_btn5 = self.make_touch_button(
            self.style_frame, text="Exaggerated", font=("Arial", 9, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn5.grid(row=5, column=10, columnspan=10, sticky="nsew", padx=1, pady=1)
        
        # Row 6 - 12/20 width Caricature
        self.caricature_btn6 = self.make_touch_button(
            self.style_frame, text="Stylized", font=("Arial", 8, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn6.grid(row=6, column=8, columnspan=12, sticky="nsew", padx=1, pady=1)
        
        # Row 7 - 14/20 width Caricature
        self.caricature_btn7 = self.make_touch_button(
            self.style_frame, text="Comedy", font=("Arial", 8, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn7.grid(row=7, column=6, columnspan=14, sticky="nsew", padx=1, pady=1)
        
        # Row 8 - 16/20 width Caricature
        self.caricature_btn8 = self.make_touch_button(
            self.style_frame, text="Express", font=("Arial", 7, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn8.grid(row=8, column=4, columnspan=16, sticky="nsew", padx=1, pady=1)
        
        # Row 9 - 18/20 width Caricature (almost full)
        self.caricature_btn9 = self.make_touch_button(
            self.style_frame, text="🎭 SELECT CARICATURE", font=("Arial", 7, "bold"),
            bg=self.COLORS['caricature'], fg="black", relief="flat", bd=0, cursor='hand2',
            command=lambda: self.set_style_and_convert("caricature"), triangle_type="caricature"
        )
        self.caricature_btn9.grid(row=9, column=2, columnspan=18, sticky="nsew", padx=1, pady=1)
        
        # Store references for backward compatibility
        self.face_drawing_btn = self.portrait_btn1
        self.caricature_btn = self.caricature_btn1
        
        # Create visual triangle overlay that looks like two simple triangular buttons
        self.create_triangle_button_overlay()
        
        # Tile 4: Start Drawing (Bottom Right) - Single column, equal size
        self.start_drawing_btn = tk.Button(grid_frame, 
                                         text="4. START DRAWING\n\n🤖",
                                         command=self.start_drawing,
                                         font=self.BUTTON_FONT, bg=self.COLORS['start_drawing'], fg='white',
                                         relief=tk.RAISED, bd=3, cursor='hand2')
        self.start_drawing_btn.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)  
        
        # Create alias for backward compatibility with existing code
        self.draw_btn = self.start_drawing_btn
        
        # Initialize drawing style variable
        self.drawing_style = tk.StringVar(value="normal")
        
        # Add status indicators
        self.create_status_indicators(main_frame)
        
        # Status bar at bottom
        self.create_status_bar(main_frame)
    
    def create_triangle_button_overlay(self):
        """Create visual overlay that makes it look like two triangle buttons while keeping staircase functional"""
        # Create a canvas that shows triangle shapes but allows clicks to pass through
        overlay_canvas = tk.Canvas(self.style_frame, highlightthickness=0, bg=self.COLORS['photo_preview'])
        overlay_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Store reference for updates
        self.triangle_overlay = overlay_canvas
        
        # Track disabled state for triangle overlay
        self.triangle_buttons_disabled = False
        
        # Bind to canvas events but allow clicks to pass through to buttons underneath
        overlay_canvas.bind('<Configure>', lambda e: self.draw_triangle_buttons_smart(overlay_canvas))
        overlay_canvas.bind('<Button-1>', self.handle_triangle_click)
        
        # Initial draw
        self.root.after(100, lambda: self.draw_triangle_buttons_smart(overlay_canvas))
    
    def draw_triangle_buttons_smart(self, canvas):
        """Draw triangle buttons based on current disabled state"""
        if self.triangle_buttons_disabled:
            self.draw_triangle_buttons_disabled(canvas)
        else:
            self.draw_triangle_buttons(canvas)

    def draw_triangle_buttons_disabled(self, canvas):
        """Draw disabled triangle buttons that keep original colors but gray out text"""
        if not canvas.winfo_exists():
            return
            
        canvas.delete("all")  # Clear canvas
        
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # Check if triangles are currently pressed using flags
        portrait_pressed = self.portrait_triangle_pressed
        caricature_pressed = self.caricature_triangle_pressed
        
        # Draw upper-left triangle (PORTRAIT) - keep original orange color but slightly dimmed
        portrait_triangle = [
            0, 0,           # Top-left
            width, 0,       # Top-right
            0, height       # Bottom-left
        ]
        canvas.create_polygon(
            portrait_triangle,
            fill="white" if portrait_pressed else self.COLORS['portrait'],     # Keep original orange color
            outline='black',
            width=2,
            tags="portrait_triangle"
        )
        
        # Draw lower-right triangle (CARICATURE) - keep original purple color but slightly dimmed  
        caricature_triangle = [
            width, 0,       # Top-right
            width, height,  # Bottom-right
            0, height       # Bottom-left
        ]
        canvas.create_polygon(
            caricature_triangle,
            fill="white" if caricature_pressed else self.COLORS['caricature'],     # Keep original purple color
            outline='black',
            width=2,
            tags="caricature_triangle"
        )
        
        # Add grayed-out text labels on the triangles
        canvas.create_text(
            width * 0.25, height * 0.25,  # Upper-left quadrant
            text="👤 PORTRAIT",
            fill='gray',  # Gray text instead of black
            font=self.BUTTON_FONT,
            justify=tk.CENTER,
            tags="portrait_text_disabled"
        )
        
        canvas.create_text(
            width * 0.75, height * 0.75,  # Lower-right quadrant  
            text="😄 CARICATURE",
            fill='gray',  # Gray text instead of black
            font=self.BUTTON_FONT,
            justify=tk.CENTER,
            tags="caricature_text_disabled"
        )
        
        # Draw grayed-out diagonal separator line
        canvas.create_line(
            width, 0,           # Top-right
            0, height,          # Bottom-left
            fill='white',     # keep subtle when disabled
            width=4,
            tags="separator_line_disabled"
        )

    def draw_triangle_buttons(self, canvas):
        """Draw two triangle button shapes that visually cover the staircase"""
        if not canvas.winfo_exists():
            return
            
        canvas.delete("all")  # Clear canvas
        
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # Check if triangles are currently pressed using flags
        portrait_pressed = self.portrait_triangle_pressed
        caricature_pressed = self.caricature_triangle_pressed
        
        # Draw upper-left triangle (PORTRAIT) - orange
        portrait_triangle = [
            0, 0,           # Top-left
            width, 0,       # Top-right
            0, height       # Bottom-left
        ]
        canvas.create_polygon(
            portrait_triangle,
            fill="white" if portrait_pressed else self.COLORS['portrait'],     
            outline='black',
            width=2,
            tags="portrait_triangle"
        )
        
        # Draw lower-right triangle (CARICATURE) - purple  
        caricature_triangle = [
            width, 0,       # Top-right
            width, height,  # Bottom-right
            0, height       # Bottom-left
        ]
        canvas.create_polygon(
            caricature_triangle,
            fill="white" if caricature_pressed else self.COLORS['caricature'],   
            outline='black',
            width=2,
            tags="caricature_triangle"
        )        # Add text labels on the triangles
        canvas.create_text(
            width * 0.25, height * 0.25,  # Upper-left quadrant
            text="👤 PORTRAIT",
            fill='black',
            font=self.BUTTON_FONT,
            justify=tk.CENTER,
            tags="portrait_text"
        )
        
        canvas.create_text(
            width * 0.75, height * 0.75,  # Lower-right quadrant  
            text="😄 CARICATURE",
            fill='black',
            font=self.BUTTON_FONT,
            justify=tk.CENTER,
            tags="caricature_text"
        )
        
        # Draw diagonal separator line
        canvas.create_line(
            width, 0,           # Top-right
            0, height,          # Bottom-left
            fill='white',
            width=4,
            tags="separator_line"
        )
    
    def handle_triangle_click(self, event):
        """Handle clicks on the triangle overlay and pass them to appropriate underlying buttons"""
        canvas = event.widget
        width = canvas.winfo_width()
        height = canvas.winfo_height()

        x, y = event.x, event.y

        # Determine which triangle was clicked based on position relative to diagonal
        # Diagonal line equation: y = height - (height/width) * x
        diagonal_y_at_x = height - (height/width) * x

        if y < diagonal_y_at_x:
            # Clicked in upper triangle (Portrait area)
            # Set press flag and redraw
            self.portrait_triangle_pressed = True
            self.draw_triangle_buttons_smart(canvas)
            # Schedule flag reset and redraw after a short delay to simulate button press
            canvas.after(150, lambda: self._reset_portrait_triangle(canvas))
            self.set_style_and_convert("portrait")
        else:
            # Clicked in lower triangle (Caricature area)
            # Set press flag and redraw
            self.caricature_triangle_pressed = True
            self.draw_triangle_buttons_smart(canvas)
            # Schedule flag reset and redraw after a short delay to simulate button press
            canvas.after(150, lambda: self._reset_caricature_triangle(canvas))
            self.set_style_and_convert("caricature")
    
    def _reset_portrait_triangle(self, canvas):
        """Reset portrait triangle press state and redraw"""
        self.portrait_triangle_pressed = False
        self.draw_triangle_buttons_smart(canvas)
    
    def _reset_caricature_triangle(self, canvas):
        """Reset caricature triangle press state and redraw"""
        self.caricature_triangle_pressed = False
        self.draw_triangle_buttons_smart(canvas)
    
    def create_status_indicators(self, parent):
        """Create compact status indicators"""
        status_frame = tk.Frame(parent, bg=self.COLORS['background'])
        status_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Robot connection status
        # use palette color for emphasis
        self.robot_status = tk.Label(status_frame, text="⚫ Robot: Disconnected", 
                    font=('Arial', 12, 'bold'), bg=self.COLORS['background'], fg=self.COLORS['take_photo'])
        self.robot_status.pack(side=tk.LEFT)
        
        # Progress info
        self.progress_label = tk.Label(status_frame, text="Ready to start!", 
                        font=('Arial', 12), bg=self.COLORS['background'], fg=self.COLORS['start_drawing'])
        self.progress_label.pack(side=tk.RIGHT)
        
        # Add settings button instead of test button
        settings_btn = tk.Button(status_frame, text="⚙️ Settings", 
            command=self.open_setup_window,
            bg=self.COLORS['photo_preview'], fg='white', font=('Arial', 8), relief='flat', 
            padx=5, pady=2, cursor='hand2')
        settings_btn.pack(side=tk.RIGHT, padx=(5, 0))
    
    def create_step_section(self, parent, title, content_func):
        """
        Create a clean step section with header and content.
        
        Args:
            parent: Parent widget
            title (str): Section title text
            content_func: Function to create section content
        """
        # Step container with border
        step_frame = tk.Frame(parent, bg=self.COLORS['section_bg'], relief='flat', bd=0)
        step_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Step header with colored background
        header_frame = tk.Frame(step_frame, bg=self.COLORS['header_bg'], height=40)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        header_label = tk.Label(header_frame, text=title, 
                               font=('Arial', 16, 'bold'), 
                               bg=self.COLORS['header_bg'], 
                               fg=self.COLORS['header_text'])
        header_label.pack(expand=True)
        
        # Step content area
        content_frame = tk.Frame(step_frame, bg=self.COLORS['section_bg'], padx=20, pady=15)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        content_func(content_frame)
    
    def create_file_selection_section(self, parent):
        """Create minimal input section for expo - just camera and setup"""
        # Current image display
        image_display_frame = tk.Frame(parent, bg='white')
        image_display_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.file_label_main = tk.Label(image_display_frame, text="📷 Take a photo to start drawing",
            font=('Arial', 14, 'bold'), bg='white', fg=self.COLORS['take_photo'], anchor='center')
        self.file_label_main.pack(anchor='center', pady=(0, 10))

        # Main action buttons - just camera and setup
        buttons_frame = tk.Frame(parent, bg='white')
        buttons_frame.pack()

        # Take Photo button (main action)
        self.take_photo_btn = self.make_touch_button(buttons_frame, text="📷 TAKE PHOTO", 
            command=self.get_picture_from_robot,
            bg=self.COLORS['take_photo'], fg='white', font=('Arial', 16, 'bold'), relief='flat', 
            padx=40, pady=20, cursor='hand2', width=20)
        self.take_photo_btn.pack(pady=(0, 15))

        # Setup button (smaller, for advanced users)
        setup_btn = tk.Button(parent, text="⚙️ Advanced Setup & Other Options", command=self.open_setup_window,
              bg=self.COLORS['photo_preview'], fg='white', font=('Arial', 11), relief='flat', 
              padx=20, pady=10, cursor='hand2')
        setup_btn.pack(pady=(20, 0))
    
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
                      activebackground='white', command=self.on_mode_change).pack(side=tk.LEFT, padx=(0, 20))
        
        tk.Radiobutton(mode_frame, text="🤖 Generate from Text", variable=self.drawing_mode, 
                      value="text", bg='white', font=('Arial', 10),
                      activebackground='white', command=self.on_mode_change).pack(side=tk.LEFT)
        
        # Robot Connection Settings
        connection_frame = tk.Frame(parent, bg='white')
        connection_frame.pack(fill=tk.X, pady=(15, 10))
        
        tk.Label(connection_frame, text="Robot Connection:", font=('Arial', 11, 'bold'), 
            bg='white', fg=self.COLORS['take_photo']).pack(anchor='w', pady=(0, 8))
        
        # IP Address row
        ip_row = tk.Frame(connection_frame, bg='white')
        ip_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(ip_row, text="Robot IP Address:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        ip_entry = tk.Entry(ip_row, textvariable=self.robot_ip, 
                           font=('Arial', 10), width=18, relief='solid', bd=1)
        ip_entry.pack(side=tk.LEFT, padx=(10, 0))
        ip_entry.bind('<KeyRelease>', lambda e: self._update_connection_display())
        ip_entry.bind('<FocusOut>', lambda e: self._update_connection_display())
        
        # Ports row
        ports_row = tk.Frame(connection_frame, bg='white')
        ports_row.pack(fill=tk.X, pady=(0, 5))
        
        # Right robot port
        tk.Label(ports_row, text="Right Robot Port:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        port_entry = tk.Entry(ports_row, textvariable=self.robot_port, 
                             font=('Arial', 10), width=8, relief='solid', bd=1)
        port_entry.pack(side=tk.LEFT, padx=(10, 20))
        port_entry.bind('<KeyRelease>', lambda e: self._update_connection_display())
        port_entry.bind('<FocusOut>', lambda e: self._update_connection_display())
        
        # Left robot port
        tk.Label(ports_row, text="Left Robot Port:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        port_l_entry = tk.Entry(ports_row, textvariable=self.robot_port_l, 
                               font=('Arial', 10), width=8, relief='solid', bd=1)
        port_l_entry.pack(side=tk.LEFT, padx=(10, 0))
        port_l_entry.bind('<KeyRelease>', lambda e: self._update_connection_display())
        port_l_entry.bind('<FocusOut>', lambda e: self._update_connection_display())
        
        # Port info
        port_info = tk.Label(connection_frame, text="ℹ️ Left port is used only in dual-arm drawing mode", 
                    font=('Arial', 9), bg='white', fg=self.COLORS['start_drawing'])
        port_info.pack(anchor='w', pady=(0, 10))
        
        # File selection section
        self.file_section = tk.Frame(parent, bg='white')
        self.file_section.pack(fill=tk.X, pady=(0, 10))
        
        # Current file display
        self.file_label = tk.Label(self.file_section, text="No image selected", 
                    font=('Arial', 10), bg='white', fg=self.COLORS['take_photo'], 
                    anchor='w', width=50)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Browse button
        browse_btn = tk.Button(self.file_section, text="Browse Images", 
            command=self.browse_image,
            bg=self.COLORS['photo_preview'], fg='white', font=self.BUTTON_FONT,
            relief='flat', padx=self.BUTTON_PADX, pady=self.BUTTON_PADY, cursor='hand2', width=self.BUTTON_WIDTH)
        browse_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Drawing section
        self.draw_section = tk.Frame(parent, bg='white')
        self.draw_section.pack(fill=tk.X, pady=(0, 10))
        
        # Drawing controls row
        draw_controls = tk.Frame(self.draw_section, bg='white')
        draw_controls.pack()
        
        draw_btn = tk.Button(draw_controls, text="🎨 Open Drawing Canvas", 
                command=self.open_drawing_window,
                bg=self.COLORS['caricature'], fg='white', font=self.BUTTON_FONT,
                relief='flat', padx=self.BUTTON_PADX, pady=self.BUTTON_PADY, cursor='hand2', width=self.BUTTON_WIDTH)
        draw_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Templates button
        templates_btn = tk.Button(draw_controls, text="📋 Templates", 
                command=self.show_templates,
        bg=self.COLORS['photo_preview'], fg='white', font=self.BUTTON_FONT,
                relief='flat', padx=self.BUTTON_PADX, pady=self.BUTTON_PADY, cursor='hand2', width=self.BUTTON_WIDTH)
        templates_btn.pack(side=tk.LEFT)
        
        # Initially hide draw section
        self.draw_section.pack_forget()
        
        # Text generation section
        self.text_section = tk.Frame(parent, bg='white')
        self.text_section.pack(fill=tk.X, pady=(0, 10))
        
        # Text input controls
        text_controls = tk.Frame(self.text_section, bg='white')
        text_controls.pack(fill=tk.X, pady=(0, 10))
        
        # Prompt label
        tk.Label(text_controls, text="Enter your description:", font=('Arial', 10, 'bold'), 
                bg='white').pack(anchor='w', pady=(0, 5))
        
        # Text input area
        text_input_frame = tk.Frame(text_controls, bg='white')
        text_input_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.text_entry = tk.Text(text_input_frame, height=3, width=60, 
                    font=('Arial', 10), relief='solid', bd=1,
                    wrap=tk.WORD, fg=self.COLORS['take_photo'])
        self.text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        # Generate button
        generate_btn = tk.Button(text_input_frame, text="🤖 Generate Image", 
            command=self.generate_from_text,
            bg=self.COLORS['start_drawing'], fg='white', font=self.BUTTON_FONT,
            relief='flat', padx=self.BUTTON_PADX, pady=self.BUTTON_PADY, cursor='hand2', width=self.BUTTON_WIDTH)
        generate_btn.pack(side=tk.RIGHT)
        
        # Example prompts
        examples_frame = tk.Frame(text_controls, bg='white')
        examples_frame.pack(fill=tk.X)
        
        tk.Label(examples_frame, text="Examples:", font=('Arial', 9, 'bold'), 
                bg='white', fg='#666').pack(anchor='w')
        
        examples_text = tk.Label(examples_frame, 
            text="• Simple house with a door and windows\n• Cat sitting on a chair\n• Geometric pattern with circles and triangles\n• Portrait of a person smiling", 
            font=('Arial', 8), bg='white', fg=self.COLORS['photo_preview'], justify='left')
        examples_text.pack(anchor='w', pady=(2, 0))
        
        # Initially hide text section
        self.text_section.pack_forget()
        
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
        
        for i, (text, value) in enumerate([("Adaptive", "adaptive"), ("Threshold", "threshold"), ("Canny Edge", "canny")]):
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
        coord_checkbox.pack(side=tk.LEFT, padx=(10, 10))

        # Dual-arm mode checkbox (placed next to coordinate system)
        dual_arm_checkbox = tk.Checkbutton(coord_logo_frame, text="Dual-arm drawing mode (split & sync)",
                        variable=self.dual_arm_mode, bg='white', font=('Arial', 9, 'bold'),
                        activebackground='white')
        dual_arm_checkbox.pack(side=tk.LEFT, padx=(10, 20))
        
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

        # Frame filtering section (new row)
        frame_filter_frame = tk.Frame(parent, bg='white')
        frame_filter_frame.pack(fill=tk.X, pady=(10, 0))
        
        tk.Label(frame_filter_frame, text="Image Processing:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side=tk.LEFT)
        
        frame_filter_checkbox = tk.Checkbutton(frame_filter_frame, text="🚫 Remove edge borders (CAUTION: may remove drawing content near edges)", 
                                              variable=self.enable_frame_filtering, bg='white', font=('Arial', 9),
                                              activebackground='white', command=self.on_frame_filtering_change)
        frame_filter_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        
        # Add warning label
        warning_label = tk.Label(frame_filter_frame, text="⚠️ Only enable for scanned documents with unwanted borders", 
            font=('Arial', 8), bg='white', fg=self.COLORS['start_drawing'])
        warning_label.pack(side=tk.LEFT, padx=(10, 0))

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
                                     bg='white', fg=self.COLORS['take_photo'], font=('Arial', 8), relief='flat', 
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
                                        bg='white', fg=self.COLORS['take_photo'], font=('Arial', 8), relief='flat', 
                                        padx=8, pady=2, cursor='hand2')
            margin_preset_btn.pack(side=tk.LEFT, padx=(2, 0))

        # Forbidden buffer radius (for dual-arm forbidden zones)
        buffer_frame = tk.Frame(parent, bg='white')
        buffer_frame.pack(fill=tk.X, pady=(8, 0))
        tk.Label(buffer_frame, text="Dual-arm forbidden buffer (mm):", font=('Arial', 10, 'bold'), bg='white').pack(side=tk.LEFT)
        self.forbidden_buffer_var = tk.IntVar(value=40)
        buffer_spin = tk.Spinbox(buffer_frame, from_=0, to=200, width=5, textvariable=self.forbidden_buffer_var, font=('Arial', 9), command=lambda: self._on_forbidden_buffer_change())
        buffer_spin.pack(side=tk.LEFT, padx=(8, 5))
        tk.Label(buffer_frame, text="mm (only used in dual-arm mode)", font=('Arial', 9), bg='white', fg='#666').pack(side=tk.LEFT)
    
    def create_connection_section(self, parent):
        """Create minimal connection section - just status and connect"""
        # Simple connection status
        status_frame = tk.Frame(parent, bg='white')
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Connection status (centered)
        self.conn_status_label = tk.Label(status_frame, text="⚫ Robot Not Connected", 
                font=('Arial', 14, 'bold'), bg='white', fg=self.COLORS['take_photo'])
        self.conn_status_label.pack(pady=(0, 10))
        
        # Connect button (prominent)
        self.connect_btn = tk.Button(status_frame, text="🔗 CONNECT ROBOT", 
            command=self.toggle_connection,
            bg=self.COLORS['portrait'], fg='white', font=('Arial', 16, 'bold'),
            relief='flat', padx=40, pady=20, cursor='hand2', width=20)
        self.connect_btn.pack()
        
        # Connection info (small)
        self.ip_display_label = tk.Label(status_frame, text=f"Robot: {self.robot_ip.get()}:{self.robot_port.get()}", 
                font=('Arial', 10), bg='white', fg=self.COLORS['photo_preview'])
        self.ip_display_label.pack(pady=(10, 0))
    
    def create_action_section(self, parent):
        """Create minimal action section - just image, effects, and start button"""
        # Single centered layout
        layout_frame = tk.Frame(parent, bg='white')
        layout_frame.pack(fill=tk.BOTH, expand=True)

        # Image preview (centered, larger)
        image_frame = tk.Frame(layout_frame, bg='white')
        image_frame.pack(pady=(0, 30))

        tk.Label(image_frame, text="📸 Your Photo", font=('Arial', 14, 'bold'), 
            bg='white', fg=self.COLORS['take_photo']).pack(pady=(0, 10))

        self.original_canvas = tk.Canvas(image_frame, bg='white', 
                width=self.PREVIEW_WIDTH, height=self.PREVIEW_HEIGHT, relief='solid', bd=1)
        self.original_canvas.pack()
        self.original_canvas.create_text(self.PREVIEW_WIDTH//2, self.PREVIEW_HEIGHT//2, 
                text="Take a photo to see it here", 
                font=('Arial', 14), fill=self.COLORS['photo_preview'])

        # Effect selection (horizontal layout)
        effects_frame = tk.Frame(layout_frame, bg='white')
        effects_frame.pack(pady=(0, 30))

        effects_frame_label = tk.Label(effects_frame, text="Choose Drawing Style:", 
                    font=('Arial', 14, 'bold'), bg='white', fg=self.COLORS['take_photo'])
        effects_frame_label.pack(pady=(0, 15))

        effects_buttons = tk.Frame(effects_frame, bg='white')
        effects_buttons.pack()

        # Normal drawing (default)
        self.normal_btn = tk.Button(effects_buttons, text="📄 Normal\nDrawing", 
            command=lambda: self.set_drawing_mode('normal'),
            bg=self.COLORS['photo_preview'], fg='white', font=('Arial', 12, 'bold'),
            relief='flat', padx=20, pady=15, cursor='hand2', width=12,
            state='disabled')
        self.normal_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Portrait mode
        self.face_drawing_btn = tk.Button(effects_buttons, text="👤 Portrait\nMode", 
            command=self.convert_to_face_drawing,
            bg=self.COLORS['start_drawing'], fg='black', font=('Arial', 12, 'bold'),
            relief='flat', padx=20, pady=15, cursor='hand2', width=12,
            state='disabled')
        self.face_drawing_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Caricature mode  
        self.caricature_btn = tk.Button(effects_buttons, text="🎭 Caricature\nMode", 
            command=self.convert_to_caricature,
            bg=self.COLORS['portrait'], fg='black', font=('Arial', 12, 'bold'),
            relief='flat', padx=20, pady=15, cursor='hand2', width=12,
            state='disabled')
        self.caricature_btn.pack(side=tk.LEFT)

        # Main START button (very prominent)
        start_frame = tk.Frame(layout_frame, bg='white')
        start_frame.pack(pady=(0, 20))

        self.draw_btn = self.make_touch_button(start_frame, text="🎨 START DRAWING", 
            command=self.start_robot_drawing,
            bg=self.COLORS['photo_preview'], fg='white', font=('Arial', 18, 'bold'),
            relief='flat', padx=50, pady=25, cursor='hand2', width=25,
            state='disabled')
        self.draw_btn.pack()

        # Emergency stop button (initially hidden)
        self.stop_btn = tk.Button(start_frame, text="⏹ EMERGENCY STOP", 
                command=self.emergency_stop,
                bg=self.COLORS['take_photo'], fg='white', font=('Arial', 16, 'bold'),
                relief='flat', padx=40, pady=20, cursor='hand2', width=25)

        # Store for matplotlib (moved to setup)
        self.fig = None
        self.ax = None
        self.canvas_widget = None
        
        self.drawing_active = False
        
        # Emergency stop button (initially hidden)
        self.stop_btn = tk.Button(start_frame, text="⏹ EMERGENCY\nSTOP", 
                command=self.emergency_stop,
                bg=self.COLORS['take_photo'], fg='white', font=('Arial', 12, 'bold'),
                relief='flat', padx=20, pady=15, cursor='hand2', width=16)
        
        self.drawing_active = False

    def set_drawing_mode(self, mode):
        """Set the drawing mode to normal (no special effects)"""
        if hasattr(self, 'current_image_path') and self.current_image_path:
            # Just process the current image normally
            self.auto_process_image()

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
        
        # Invert y-axis so (0,0) is at top-left corner
        ax.invert_yaxis()
        
        # Set equal aspect ratio so 1mm = 1mm visually
        ax.set_aspect('equal', adjustable='box')
        
        # Boundary
        ax.plot(boundary_x, boundary_y, 'k--', linewidth=2, alpha=0.5, label='Workspace Area')
        
        # Show effective drawing area if margins are applied
        if margin_x > 0 or margin_y > 0:
            ax.plot(effective_boundary_x, effective_boundary_y, 'g-', linewidth=1.5, alpha=0.7, label='Drawing Area (with margins)')

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
            # Check if dual-arm mode is enabled - only run dual-arm animation in dual-arm mode
            if not self.dual_arm_mode.get():
                import tkinter.messagebox as mb
                mb.showinfo("Single-Arm Mode", "Dual-arm animation is only available in dual-arm mode.\n\nPlease enable 'Dual-arm drawing mode' in the Advanced Setup to see arm assignment animations.\n\nFor single-arm mode, use the 'Animate Point by Point' button below.")
                return
                
            # Build dual-assignment steps using master_slave_assign_contours
            from coordinate_transformer import master_slave_assign_contours
            from matplotlib.animation import FuncAnimation
            import matplotlib.patches as mpatches

            # Get coordinate system setting
            use_center = self.use_center_origin.get()

            contours = self.drawer.drawing_points
            if not contours or not any(len(c) > 0 for c in contours):
                import tkinter.messagebox as mb
                msg = f"No paths to animate. drawing_points type: {type(contours)}, length: {len(contours) if contours is not None else 'None'}\nContent: {contours}"
                mb.showwarning("No Paths to Animate", msg)
                ax.clear()
                ax.text(0, 0, 'No path data to animate!', ha='center', va='center', color='red', fontsize=14)
                canvas.draw_idle()
                return

            steps = []
            remaining = contours[:]
            master_role = 'right'
            # Read forbidden buffer from GUI control (default 40 mm)
            buf_mm = int(self.forbidden_buffer_var.get()) if hasattr(self, 'forbidden_buffer_var') else 40
            while remaining:
                result = master_slave_assign_contours(remaining, master=master_role, buffer_radius=buf_mm)
                if len(result) == 5:
                    master, slave, rest, unassigned, forbidden_poly = result
                else:
                    master, slave, rest, unassigned = result
                    forbidden_poly = None
                steps.append((remaining[:], master_role, master, slave, forbidden_poly))
                remaining = rest
                master_role = 'left' if master_role == 'right' else 'right'

            # Prepare legend with Professional/Industrial colors
            legend_handles = [
                mpatches.Patch(color='#FF1744', alpha=0.15, label='Forbidden zone (Safety Red)', hatch='//'),
                mpatches.Patch(color='#FFCDD2', alpha=0.7, label='Left-forbidden rectangle'),
                mpatches.Patch(color='#004E89', label='Right Arm (Deep Blue)'),
                mpatches.Patch(color='#FF6B35', label='Left Arm (Safety Orange)'),
            ]

            def plot_contour(ax, contour, color, lw=2, alpha=1.0, zorder=1):
                if not contour:
                    return
                xs, ys = zip(*contour)
                
                # Transform coordinates to mirror them vertically for proper display
                workspace_height = max_y  # Use the workspace height from boundary
                ys_transformed = [workspace_height - y for y in ys]
                
                xs = list(xs) + [xs[0]]
                ys_transformed = list(ys_transformed) + [ys_transformed[0]]
                ax.plot(xs, ys_transformed, color=color, lw=lw, alpha=alpha, zorder=zorder)

            # Add a small label to show current step / total steps
            step_label = tk.Label(self.detail_window, text="Step 0 / 0", bg='white', font=('Arial', 10, 'bold'))
            step_label.pack(side=tk.TOP)

            def update(frame):
                # Clear and set labels
                ax.clear()
                ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)')
                ax.grid(True, alpha=0.3)
                
                # Invert y-axis so (0,0) is at top-left corner (only if not already inverted)
                if not ax.yaxis_inverted():
                    ax.invert_yaxis()
                print(f"Animation frame {frame}: Y-axis inverted = {ax.yaxis_inverted()}")
                
                ax.set_aspect('equal', adjustable='box')

                # Force view limits to workspace boundary so huge forbidden tails don't expand view
                x_min, x_max = min(boundary_x), max(boundary_x)
                y_min, y_max = min(boundary_y), max(boundary_y)
                # Add small padding
                pad_x = max(5.0, (x_max - x_min) * 0.02)
                pad_y = max(5.0, (y_max - y_min) * 0.02)
                ax.set_xlim(x_min - pad_x, x_max + pad_x)
                ax.set_ylim(y_min - pad_y, y_max + pad_y)

                # Draw static workspace outlines - transform coordinates
                boundary_y_transformed = [max_y - y for y in boundary_y]
                ax.plot(boundary_x, boundary_y_transformed, 'k--', linewidth=2, alpha=0.5, label='Workspace Area')
                if margin_x > 0 or margin_y > 0:
                    effective_boundary_y_transformed = [max_y - y for y in effective_boundary_y]
                    ax.plot(effective_boundary_x, effective_boundary_y_transformed, 'g-', linewidth=1.5, alpha=0.7, label='Drawing Area (with margins)')
                
                # Draw static left-forbidden rectangle (0,0) to (130,40) - transform coordinates
                if not use_center:  # Only show in corner origin mode
                    left_forbidden_x = [0, 130, 130, 0, 0]
                    left_forbidden_y = [0, 0, 40, 40, 0]
                    left_forbidden_y_transformed = [max_y - y for y in left_forbidden_y]
                    ax.fill(left_forbidden_x, left_forbidden_y_transformed, color='#FFCDD2', alpha=0.7, zorder=1)
                    ax.plot(left_forbidden_x, left_forbidden_y_transformed, color='#FF1744', linewidth=2, 
                           linestyle='--', alpha=0.8, zorder=1)
                ax.set_title(f'Step {frame+1} / {len(steps)}')
                # Update step label text
                try:
                    step_label.config(text=f"Step {frame+1} / {len(steps)}")
                except Exception:
                    pass
                ax.legend(handles=legend_handles)

                remaining, master_role, master, slave, forbidden_poly = steps[frame]
                # Show current master (left/right) prominently in the corner
                master_text = f'Master: {master_role.title()}'
                ax.text(0.02, 0.95, master_text, transform=ax.transAxes, ha='left', va='top',
                    fontsize=10, color='black', bbox=dict(facecolor='white', alpha=0.8, edgecolor='none'))

                # Plot remaining contours faint
                colors_local = plt.cm.tab20(np.linspace(0, 1, max(1, len(remaining))))
                for i, c in enumerate(remaining):
                    if c:
                        plot_contour(ax, c, color=colors_local[i % len(colors_local)], lw=1, alpha=0.4, zorder=1)

                # Plot forbidden area clipped to view box to avoid huge tails
                if forbidden_poly is not None:
                    # Always use safety red for forbidden zones (consistent safety warning)
                    forbidden_color = '#FF1744'  # Safety Red for all forbidden areas
                    
                    try:
                        from shapely.geometry import box as shapely_box
                        view_box = shapely_box(ax.get_xlim()[0], ax.get_ylim()[0], ax.get_xlim()[1], ax.get_ylim()[1])
                        clipped = forbidden_poly.intersection(view_box)
                    except Exception:
                        clipped = forbidden_poly

                    if clipped is not None and not clipped.is_empty:
                        if clipped.geom_type == 'Polygon':
                            polys = [clipped]
                        else:
                            polys = list(clipped.geoms)
                        for poly in polys:
                            if hasattr(poly, 'exterior') and poly.exterior is not None:
                                x_f, y_f = poly.exterior.xy
                                # Transform forbidden polygon coordinates
                                y_f_transformed = [max_y - y for y in y_f]
                                ax.fill(x_f, y_f_transformed, color=forbidden_color, alpha=0.15, zorder=2, hatch='//')

                # Plot master and slave with Professional/Industrial colors (Deep Blue=right, Safety Orange=left)
                if master:
                    master_color = '#004E89' if master_role == 'right' else '#FF6B35'
                    plot_contour(ax, master, color=master_color, lw=3, alpha=1.0, zorder=3)
                if slave:
                    slave_role = 'left' if master_role == 'right' else 'right'
                    slave_color = '#004E89' if slave_role == 'right' else '#FF6B35'
                    plot_contour(ax, slave, color=slave_color, lw=3, alpha=1.0, zorder=3)

                canvas.draw_idle()

            # Create and store animation to avoid garbage collection
            self._current_anim = FuncAnimation(ax.figure, update, frames=len(steps), interval=1200, repeat=False)
            canvas.draw_idle()

        anim_btn = tk.Button(self.detail_window, text="Animate Dual-Arm Paths", command=start_animation, bg=self.COLORS['take_photo'], fg="white", font=("Arial", 10, "bold"))

        anim_btn.pack(side=tk.TOP, pady=8)

        # --- Point-by-point Animation Button ---
        def start_point_animation():
            ax.clear()
            ax.set_xlabel('X (mm)'); ax.set_ylabel('Y (mm)')
            ax.grid(True, alpha=0.3)
            
            # Invert y-axis so (0,0) is at top-left corner
            ax.invert_yaxis()
            
            ax.set_aspect('equal', adjustable='box')
            ax.plot(boundary_x, boundary_y, 'k--', linewidth=2, alpha=0.5, label='Workspace Area')
            if margin_x > 0 or margin_y > 0:
                ax.plot(effective_boundary_x, effective_boundary_y, 'g-', linewidth=1.5, alpha=0.7, label='Drawing Area (with margins)')
            if self.drawer.drawing_points and any(len(p) > 0 for p in self.drawer.drawing_points):
                from matplotlib_anim_point_helper import animate_points
                
                # Use Professional/Industrial colors with arm roles if in dual-arm mode
                if self.dual_arm_mode.get():
                    # Create alternating arm roles for demonstration (this could be improved with actual assignments)
                    arm_roles = ['left' if i % 2 == 0 else 'right' for i in range(len(self.drawer.drawing_points))]
                    colors = None  # Let the animation helper determine colors based on arm_roles
                else:
                    arm_roles = None
                    colors = plt.cm.tab20(np.linspace(0, 1, len(self.drawer.drawing_points)))
                
                self._current_anim = animate_points(
                    ax, self.drawer.drawing_points, colors=colors, arm_roles=arm_roles, interval=1,
                    on_frame=lambda f: canvas.draw_idle(), show_left_forbidden=self.dual_arm_mode.get(), invert_y=False)
                canvas.draw_idle()
            else:
                import tkinter.messagebox as mb
                msg = f"No points to animate. drawing_points type: {type(self.drawer.drawing_points)}, length: {len(self.drawer.drawing_points) if self.drawer.drawing_points is not None else 'None'}\nContent: {self.drawer.drawing_points}"
                mb.showwarning("No Points to Animate", msg)
                ax.text(0, 0, 'No point data to animate!', ha='center', va='center', color='red', fontsize=14)
            canvas.draw_idle()

        anim_point_btn = tk.Button(self.detail_window, text="Animate Point by Point (fast)", command=start_point_animation, bg=self.COLORS['photo_preview'], fg="white", font=("Arial", 10, "bold"))
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
        # Use white background for the overall UI and keep accents from the palette
        status_frame = tk.Frame(parent, bg=self.COLORS['background'], height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(status_frame, textvariable=self.status_text,
                                    font=('Arial', 9), bg=self.COLORS['background'], anchor='w', fg=self.COLORS['take_photo'])
        self.status_label.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

        # Progress indicator label for conversion status
        self.progress_indicator = tk.Label(status_frame, text="",
                                          font=('Arial', 9, 'bold'), bg=self.COLORS['background'],
                                          fg=self.COLORS['start_drawing'])
        self.progress_indicator.pack(side=tk.RIGHT, padx=(0, 10))

        # Progress bar container (initially hidden)
        self.progress_container = tk.Frame(status_frame, bg=self.COLORS['background'])

        # Create a ttk style for the progress bar using palette colors
        style = ttk.Style()
        try:
            style.theme_use('default')
        except Exception:
            pass
        style.configure('Palette.Horizontal.TProgressbar', troughcolor=self.COLORS['section_bg'], background=self.COLORS['start_drawing'], thickness=10)

        # Minimalistic progress bar (styled)
        self.bottom_progress_bar = ttk.Progressbar(
            self.progress_container,
            style='Palette.Horizontal.TProgressbar',
            mode='determinate',
            length=200
        )
        self.bottom_progress_bar.pack(side=tk.LEFT, padx=(5, 5))

        # Progress text
        self.bottom_progress_label = tk.Label(
            self.progress_container,
            text="",
            font=('Arial', 8),
            bg=self.COLORS['background'],
            fg=self.COLORS['take_photo']
        )
        self.bottom_progress_label.pack(side=tk.LEFT, padx=(5, 10))

    def _on_voice_command(self, cmd):
        """Internal callback from voice listener (worker thread).

        Re-dispatch to Tk main thread using root.after.
        """
        try:
            if hasattr(self, 'root') and self.root:
                self.root.after(0, lambda: self._handle_command(cmd))
        except Exception:
            pass

    def _handle_command(self, cmd):
        """Map recognized voice commands (strings) to GUI actions.

        Edit mappings here if you want different behavior.
        """
        cmd = (cmd or '').lower().strip()
        if cmd == 'połącz':
            # Polish: connect
            try:
                self.toggle_connection()
            except Exception:
                pass
        elif cmd == 'start':
            try:
                self.start_robot_drawing()
            except Exception:
                pass
        elif cmd == 'stop':
            try:
                self.emergency_stop()
            except Exception:
                pass
        elif cmd == 'uchwyć':
            try:
                self.get_picture_from_robot()
            except Exception:
                pass
        elif cmd == 'portret':
            try:
                self.convert_to_face_drawing()
            except Exception:
                pass
        elif cmd == 'karykatura':
            try:
                self.convert_to_caricature()
            except Exception:
                pass
        elif cmd == 'podgląd':
            try:
                self.update_robot_preview()
            except Exception:
                pass
        else:
            print('Voice command not mapped:', cmd)
    
    def on_mode_change(self):
        """Handle mode selection change"""
        try:
            if self.drawing_mode.get() == "load":
                if hasattr(self, 'file_section') and self.file_section.winfo_exists():
                    self.file_section.pack(fill=tk.X, pady=(0, 10))
                if hasattr(self, 'draw_section') and self.draw_section.winfo_exists():
                    try:
                        self.draw_section.pack_forget()
                    except Exception:
                        pass
                if hasattr(self, 'text_section') and self.text_section.winfo_exists():
                    try:
                        self.text_section.pack_forget()
                    except Exception:
                        pass
                # Clear drawing path and text when switching to file mode
                self.temp_drawing_path = None
                # Reset to no image if no file is selected
                if not self.image_path.get():
                    if hasattr(self, 'file_label') and self.file_label.winfo_exists():
                        try:
                            self.file_label.config(text="No image selected", fg='#666')
                        except Exception:
                            pass
                    try:
                        if hasattr(self, 'draw_btn') and self.draw_btn:
                            self.draw_btn.config(state='disabled')
                    except Exception:
                        pass
                    try:
                        if hasattr(self, 'face_drawing_btn') and self.face_drawing_btn:
                            self.face_drawing_btn.config(state='disabled')
                    except Exception:
                        pass
                    if hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                        try:
                            self.original_canvas.delete("all")
                            self.original_canvas.create_text(150, 100, text="No image loaded", 
                                                            font=('Arial', 10), fill='#999')
                        except Exception:
                            pass
            elif self.drawing_mode.get() == "draw":
                if hasattr(self, 'file_section') and self.file_section.winfo_exists():
                    try:
                        self.file_section.pack_forget()
                    except Exception:
                        pass
                if hasattr(self, 'text_section') and self.text_section.winfo_exists():
                    try:
                        self.text_section.pack_forget()
                    except Exception:
                        pass
                if hasattr(self, 'draw_section') and self.draw_section.winfo_exists():
                    try:
                        self.draw_section.pack(fill=tk.X, pady=(0, 10))
                    except Exception:
                        pass
                # Clear file path when switching to draw mode
                self.image_path.set("")
                try:
                    if hasattr(self, 'draw_btn') and self.draw_btn:
                        self.draw_btn.config(state='disabled')
                except Exception:
                    pass
                try:
                    if hasattr(self, 'face_drawing_btn') and self.face_drawing_btn:
                        self.face_drawing_btn.config(state='disabled')
                except Exception:
                    pass
                if hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                    try:
                        self.original_canvas.delete("all")
                        self.original_canvas.create_text(150, 100, text="No image loaded", 
                                                        font=('Arial', 10), fill='#999')
                    except Exception:
                        pass
            elif self.drawing_mode.get() == "text":
                if hasattr(self, 'file_section') and self.file_section.winfo_exists():
                    try:
                        self.file_section.pack_forget()
                    except Exception:
                        pass
                if hasattr(self, 'draw_section') and self.draw_section.winfo_exists():
                    try:
                        self.draw_section.pack_forget()
                    except Exception:
                        pass
                if hasattr(self, 'text_section') and self.text_section.winfo_exists():
                    try:
                        self.text_section.pack(fill=tk.X, pady=(0, 10))
                    except Exception:
                        pass
                # Clear file path and drawing path when switching to text mode
                self.image_path.set("")
                self.temp_drawing_path = None
                try:
                    if hasattr(self, 'draw_btn') and self.draw_btn:
                        self.draw_btn.config(state='disabled')
                except Exception:
                    pass
                try:
                    if hasattr(self, 'face_drawing_btn') and self.face_drawing_btn:
                        self.face_drawing_btn.config(state='disabled')
                except Exception:
                    pass
                if hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                    try:
                        self.original_canvas.delete("all")
                        self.original_canvas.create_text(150, 100, text="No image loaded", 
                                                        font=('Arial', 10), fill='#999')
                    except Exception:
                        pass
        except Exception:
            # Protect against widget path errors when widgets are destroyed
            pass
    
    def on_quality_change(self):
        """Handle quality setting change"""
        # Only reprocess if we have an image/drawing loaded
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        elif self.drawing_mode.get() in ["load", "text"]:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            self.status_text.set("Quality changed - reprocessing...")
            self.auto_process_image()
            try:
                if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                    self._regenerate_forbidden_zones()
            except Exception:
                pass
    
    def on_tsp_change(self):
        """Handle TSP optimization setting change"""
        # Preserve existing connection if any
        old_robot = None
        was_connected = False
        
        if hasattr(self.drawer, 'robot') and self.drawer.robot and self.drawer.robot.socket:
            old_robot = self.drawer.robot
            was_connected = True
        
        # Update the drawer's TSP setting with coordinate system
        self.drawer = RobotDrawer(
            ip=self.robot_ip.get(),
            port=int(self.robot_port.get()),
            port_l=int(self.robot_port_l.get()),
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
            try:
                if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                    self._regenerate_forbidden_zones()
            except Exception:
                pass
    
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
            elif self.drawing_mode.get() in ["load", "text"]:
                if self.image_path.get():
                    current_path = self.image_path.get()
            
            if current_path:
                self.status_text.set(f"Coordinate system changed to {origin_text} - reprocessing...")
                self.auto_process_image()
                try:
                    if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                        self._regenerate_forbidden_zones()
                except Exception:
                    pass
    
    def on_detection_method_change(self):
        """Handle detection method setting change"""
        # Only reprocess if we have an image/drawing loaded
        current_path = None
        
        if self.drawing_mode.get() == "draw":
            if hasattr(self, 'temp_drawing_path') and self.temp_drawing_path:
                current_path = self.temp_drawing_path
        elif self.drawing_mode.get() in ["load", "text"]:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            method_names = {"adaptive": "Adaptive", "threshold": "Threshold", "canny": "Canny Edge", "canny_filled": "Canny+Fill"}
            method_name = method_names.get(self.detection_method.get(), "Unknown")
            self.status_text.set(f"Detection method changed to {method_name} - reprocessing...")
            self.auto_process_image()
            try:
                if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                    self._regenerate_forbidden_zones()
            except Exception:
                pass
    
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
            try:
                if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                    self._regenerate_forbidden_zones()
            except Exception:
                pass
    
    def on_frame_filtering_change(self):
        """Handle frame filtering setting changes"""
        if self.enable_frame_filtering.get():
            self.status_text.set("⚠️ Edge border removal ENABLED - may remove drawing content near edges!")
        else:
            self.status_text.set("✅ Edge border removal DISABLED - all drawing content preserved")
        
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
            try:
                if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                    self._regenerate_forbidden_zones()
            except Exception:
                pass
    
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
            ip=self.robot_ip.get(),
            port=int(self.robot_port.get()),
            port_l=int(self.robot_port_l.get()),
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
            try:
                if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                    self._regenerate_forbidden_zones()
            except Exception:
                pass
    
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
        elif self.drawing_mode.get() in ["load", "text"]:
            if self.image_path.get():
                current_path = self.image_path.get()
        
        if current_path:
            self.status_text.set(f"Margins changed to {self.margin_x.get()}x{self.margin_y.get()}mm - reprocessing...")
            self.auto_process_image()
            try:
                if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                    self._regenerate_forbidden_zones()
            except Exception:
                pass
    
    def _recreate_drawer_with_margins(self):
        """Recreate robot drawer with new margin settings while preserving connection"""
        # Preserve existing connection if any
        old_robot = None
        was_connected = False
        
        if hasattr(self.drawer, 'robot') and self.drawer.robot and self.drawer.robot.socket:
            old_robot = self.drawer.robot
            was_connected = True
        
        # Create new drawer with margins
        self.drawer = RobotDrawer(
            ip=self.robot_ip.get(),
            port=int(self.robot_port.get()),
            port_l=int(self.robot_port_l.get()),
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
                            bg=self.COLORS['photo_preview'], fg='white', font=('Arial', 10, 'bold'),
                            relief='flat', padx=15, pady=5)
        save_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        use_btn = tk.Button(controls_frame, text="✅ Use Drawing", command=self.use_drawing,
                           bg=self.COLORS['take_photo'], fg='white', font=('Arial', 10, 'bold'),
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

    def open_setup_window(self):
        """Open a comprehensive Setup window containing all advanced settings"""
        if hasattr(self, 'setup_window') and self.setup_window.winfo_exists():
            self.setup_window.lift()
            return
            
        self.setup_window = tk.Toplevel(self.root)
        self.setup_window.title("⚙️ Advanced Setup & Configuration")
        self.setup_window.geometry("900x700")
        self.setup_window.configure(bg='#f5f5f5')
        
        # Create notebook for organized tabs
        notebook = ttk.Notebook(self.setup_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Input Methods & Image Loading
        input_frame = ttk.Frame(notebook)
        notebook.add(input_frame, text="Input Methods")
        self.create_input_methods_tab(input_frame)
        
        # Tab 2: Image Processing Settings
        processing_frame = ttk.Frame(notebook)
        notebook.add(processing_frame, text="Image Processing")
        self.create_processing_tab(processing_frame)
        
        # Tab 3: Robot Connection Settings  
        connection_frame = ttk.Frame(notebook)
        notebook.add(connection_frame, text="Robot Connection")
        self.create_connection_tab(connection_frame)
        
        # Tab 4: Drawing Settings
        drawing_frame = ttk.Frame(notebook)
        notebook.add(drawing_frame, text="Drawing Settings")
        self.create_drawing_tab(drawing_frame)
        
        # Tab 5: Advanced Options
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Advanced Options")
        self.create_advanced_tab(advanced_frame)

    def create_input_methods_tab(self, parent):
        """Create input methods tab with all the options moved from main interface"""
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File Loading Section
        file_section = tk.LabelFrame(main_frame, text="Load Image Files", font=('Arial', 12, 'bold'),
                                    bg='white', padx=15, pady=10)
        file_section.pack(fill=tk.X, pady=(0, 15))
        
        # Current file display
        self.file_label = tk.Label(file_section, text="No image selected", 
                                  font=('Arial', 11), bg='white', fg='#666', 
                                  anchor='w')
        self.file_label.pack(fill=tk.X, pady=(0, 10))
        
        # Browse button
        browse_btn = tk.Button(file_section, text="📁 Browse Images", 
                command=self.browse_image,
                bg=self.COLORS['photo_preview'], fg='white', font=('Arial', 11, 'bold'),
                relief='flat', padx=20, pady=10, cursor='hand2')
        browse_btn.pack(pady=(0, 5))
        
        # Drawing Section
        draw_section = tk.LabelFrame(main_frame, text="Create Drawings", font=('Arial', 12, 'bold'),
                                    bg='white', padx=15, pady=10)
        draw_section.pack(fill=tk.X, pady=(0, 15))
        
        # Drawing controls
        draw_controls = tk.Frame(draw_section, bg='white')
        draw_controls.pack()
        
        draw_btn = tk.Button(draw_controls, text="🎨 Open Drawing Canvas", 
                command=self.open_drawing_window,
                bg=self.COLORS['caricature'], fg='white', font=('Arial', 11, 'bold'),
                relief='flat', padx=20, pady=10, cursor='hand2')
        draw_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Templates button
        templates_btn = tk.Button(draw_controls, text="📋 Shape Templates", 
                command=self.show_templates,
                bg='#607D8B', fg='white', font=('Arial', 11, 'bold'),
                relief='flat', padx=20, pady=10, cursor='hand2')
        templates_btn.pack(side=tk.LEFT)
        
        # AI Generation Section
        ai_section = tk.LabelFrame(main_frame, text="AI Image Generation", font=('Arial', 12, 'bold'),
                                  bg='white', padx=15, pady=10)
        ai_section.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(ai_section, text="Enter detailed description:", font=('Arial', 11, 'bold'), 
                bg='white').pack(anchor='w', pady=(0, 5))
        
        # Text input area
        text_input_frame = tk.Frame(ai_section, bg='white')
        text_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.text_entry = tk.Text(text_input_frame, height=6, width=70, 
                                 font=('Arial', 11), relief='solid', bd=1, wrap=tk.WORD)
        self.text_entry.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Generate button
        generate_btn = tk.Button(ai_section, text="🤖 Generate Image from Text", 
                command=self.generate_from_text,
                bg='#FF5722', fg='white', font=('Arial', 11, 'bold'),
                relief='flat', padx=20, pady=10, cursor='hand2')
        generate_btn.pack(pady=(0, 10))
        
        # Example prompts
        examples_frame = tk.Frame(ai_section, bg='white')
        examples_frame.pack(fill=tk.X)
        
        tk.Label(examples_frame, text="Quick Examples:", font=('Arial', 10, 'bold'), 
                bg='white').pack(anchor='w', pady=(0, 5))
        
        examples_grid = tk.Frame(examples_frame, bg='white')
        examples_grid.pack(fill=tk.X)
        
        examples = [
            "Simple house with door and windows",
            "Cat sitting on a chair", 
            "Geometric pattern with circles",
            "Portrait of a person smiling",
            "Tree with branches and leaves",
            "Car from the side view"
        ]
        
        for i, example in enumerate(examples):
            btn = tk.Button(examples_grid, text=example,
                           command=lambda e=example: self.text_entry.insert(tk.END, e + "\n"),
                           bg='#e0e0e0', fg='#333', font=('Arial', 9),
                           relief='flat', padx=8, pady=3, cursor='hand2')
            btn.grid(row=i//2, column=i%2, sticky='ew', padx=2, pady=1)
        
        examples_grid.columnconfigure(0, weight=1)
        examples_grid.columnconfigure(1, weight=1)
        
        # Preview Section
        preview_section = tk.LabelFrame(main_frame, text="Robot Path Preview", font=('Arial', 12, 'bold'),
                                       bg='white', padx=15, pady=10)
        preview_section.pack(fill=tk.X, pady=(15, 0))
        
        preview_btn = tk.Button(preview_section, text="🔍 Open Detailed Path Viewer",
                command=self.open_detailed_path_window,
                bg='#607D8B', fg='white', font=('Arial', 11, 'bold'),
                relief='flat', padx=20, pady=10, cursor='hand2')
        preview_btn.pack()

    def create_processing_tab(self, parent):
        """Create image processing settings tab"""
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Quality Settings
        quality_section = tk.LabelFrame(main_frame, text="Quality Settings", font=('Arial', 11, 'bold'), 
                                       bg='white', padx=15, pady=10)
        quality_section.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(quality_section, text="Processing Quality:", font=('Arial', 10, 'bold'), 
                bg='white').pack(anchor='w', pady=(0, 5))
        
        quality_frame = tk.Frame(quality_section, bg='white')
        quality_frame.pack(fill=tk.X)
        
        for i, (text, value) in enumerate([("Standard", "medium"), ("High", "high"), ("Ultra", "highest")]):
            tk.Radiobutton(quality_frame, text=text, variable=self.quality_var, value=value,
                          bg='white', font=('Arial', 10), command=self.on_quality_change).pack(side=tk.LEFT, padx=(0, 20))
        
        # Detection Method
        detection_section = tk.LabelFrame(main_frame, text="Edge Detection Method", font=('Arial', 11, 'bold'),
                                         bg='white', padx=15, pady=10)
        detection_section.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(detection_section, text="Detection Algorithm:", font=('Arial', 10, 'bold'), 
                bg='white').pack(anchor='w', pady=(0, 5))
        
        detection_frame = tk.Frame(detection_section, bg='white')
        detection_frame.pack(fill=tk.X)
        
        for i, (text, value) in enumerate([("Adaptive", "adaptive"), ("Threshold", "threshold"), ("Canny Edge", "canny")]):
            tk.Radiobutton(detection_frame, text=text, variable=self.detection_method, value=value,
                          bg='white', font=('Arial', 10), command=self.on_detection_method_change).pack(side=tk.LEFT, padx=(0, 20))
        
        # Frame Filtering
        frame_section = tk.LabelFrame(main_frame, text="Border Processing", font=('Arial', 11, 'bold'),
                                     bg='white', padx=15, pady=10)
        frame_section.pack(fill=tk.X, pady=(0, 15))
        
        frame_filter_checkbox = tk.Checkbutton(frame_section, text="🚫 Remove edge borders (CAUTION: may remove drawing content near edges)", 
                                              variable=self.enable_frame_filtering, bg='white', font=('Arial', 10),
                                              command=self.on_frame_filtering_change)
        frame_filter_checkbox.pack(anchor='w', pady=(0, 5))
        
        warning_label = tk.Label(frame_section, text="⚠️ Only enable for scanned documents with unwanted borders", 
                                font=('Arial', 9), bg='white', fg='#ff6600')
        warning_label.pack(anchor='w')

    def create_connection_tab(self, parent):
        """Create robot connection settings tab"""
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection Settings
        conn_section = tk.LabelFrame(main_frame, text="Robot Network Settings", font=('Arial', 11, 'bold'),
                                    bg='white', padx=15, pady=10)
        conn_section.pack(fill=tk.X, pady=(0, 15))
        
        # IP Address
        ip_row = tk.Frame(conn_section, bg='white')
        ip_row.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(ip_row, text="Robot IP Address:", font=('Arial', 10, 'bold'), 
                bg='white', width=20, anchor='w').pack(side=tk.LEFT)
        
        ip_entry = tk.Entry(ip_row, textvariable=self.robot_ip, 
                           font=('Arial', 10), width=20, relief='solid', bd=1)
        ip_entry.pack(side=tk.LEFT, padx=(10, 0))
        ip_entry.bind('<KeyRelease>', lambda e: self._update_connection_display())
        
        # Right Robot Port
        port_row = tk.Frame(conn_section, bg='white')
        port_row.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(port_row, text="Right Robot Port:", font=('Arial', 10, 'bold'), 
                bg='white', width=20, anchor='w').pack(side=tk.LEFT)
        
        port_entry = tk.Entry(port_row, textvariable=self.robot_port, 
                             font=('Arial', 10), width=10, relief='solid', bd=1)
        port_entry.pack(side=tk.LEFT, padx=(10, 0))
        port_entry.bind('<KeyRelease>', lambda e: self._update_connection_display())
        
        # Left Robot Port
        port_l_row = tk.Frame(conn_section, bg='white')
        port_l_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(port_l_row, text="Left Robot Port:", font=('Arial', 10, 'bold'), 
                bg='white', width=20, anchor='w').pack(side=tk.LEFT)
        
        port_l_entry = tk.Entry(port_l_row, textvariable=self.robot_port_l, 
                               font=('Arial', 10), width=10, relief='solid', bd=1)
        port_l_entry.pack(side=tk.LEFT, padx=(10, 0))
        port_l_entry.bind('<KeyRelease>', lambda e: self._update_connection_display())
        
        # Dual-arm mode
        dual_arm_checkbox = tk.Checkbutton(conn_section, text="Enable dual-arm drawing mode (split & sync)",
                        variable=self.dual_arm_mode, bg='white', font=('Arial', 10, 'bold'))
        dual_arm_checkbox.pack(anchor='w', pady=(10, 0))
        
        # Connection Status and Controls
        status_section = tk.LabelFrame(main_frame, text="Connection Status & Control", font=('Arial', 11, 'bold'),
                                      bg='white', padx=15, pady=10)
        status_section.pack(fill=tk.X, pady=(0, 15))
        
        # Status display
        status_frame = tk.Frame(status_section, bg='white')
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(status_frame, text="Status:", font=('Arial', 10, 'bold'), 
                bg='white', width=20, anchor='w').pack(side=tk.LEFT)
        
        self.conn_status_label = tk.Label(status_frame, text="🔴 Disconnected", 
                                         font=('Arial', 10, 'bold'), bg='white', fg='red')
        self.conn_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Connection button
        button_frame = tk.Frame(status_section, bg='white')
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.connect_btn = tk.Button(button_frame, text="Connect to Robot", 
                                   command=self.toggle_connection,
                                   font=('Arial', 12, 'bold'), bg=self.COLORS['photo_preview'], fg='white',
                                   width=20, height=2, relief=tk.RAISED, bd=2)
        self.connect_btn.pack(pady=5)
        
        # Target info
        self.robot_target_label = tk.Label(status_section, text="", 
                                         font=('Arial', 9), bg='white', fg='gray')
        self.robot_target_label.pack(pady=(5, 0))
        
        # Update the display
        self._update_connection_display()

    def create_drawing_tab(self, parent):
        """Create drawing settings tab"""
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Optimization Settings
        opt_section = tk.LabelFrame(main_frame, text="Path Optimization", font=('Arial', 11, 'bold'),
                                   bg='white', padx=15, pady=10)
        opt_section.pack(fill=tk.X, pady=(0, 15))
        
        tsp_checkbox = tk.Checkbutton(opt_section, text="Enable TSP optimization (shorter drawing paths)", 
                                     variable=self.enable_tsp, bg='white', font=('Arial', 10),
                                     command=self.on_tsp_change)
        tsp_checkbox.pack(anchor='w', pady=(0, 5))
        
        batch_checkbox = tk.Checkbutton(opt_section, text="Use batch command mode (faster transmission)", 
                                       variable=self.use_batch_mode, bg='white', font=('Arial', 10),
                                       command=self.on_batch_mode_change)
        batch_checkbox.pack(anchor='w')
        
        # Coordinate System
        coord_section = tk.LabelFrame(main_frame, text="Coordinate System", font=('Arial', 11, 'bold'),
                                     bg='white', padx=15, pady=10)
        coord_section.pack(fill=tk.X, pady=(0, 15))
        
        coord_checkbox = tk.Checkbutton(coord_section, text="Use center origin (0,0 at center of workspace)", 
                        variable=self.use_center_origin, bg='white', font=('Arial', 10),
                        command=self.on_coordinate_system_change)
        coord_checkbox.pack(anchor='w')
        
        # Drawing Dimensions
        dim_section = tk.LabelFrame(main_frame, text="Drawing Area (mm)", font=('Arial', 11, 'bold'),
                                   bg='white', padx=15, pady=10)
        dim_section.pack(fill=tk.X, pady=(0, 15))
        
        # Width and Height controls
        dim_controls = tk.Frame(dim_section, bg='white')
        dim_controls.pack(fill=tk.X, pady=(0, 10))
        
        # Width
        width_frame = tk.Frame(dim_controls, bg='white')
        width_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(width_frame, text="Width:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        x_spinbox = tk.Spinbox(width_frame, from_=50, to=500, textvariable=self.max_x, 
                              width=8, font=('Arial', 10), command=self.on_dimensions_change)
        x_spinbox.pack()
        x_spinbox.bind('<KeyRelease>', lambda e: self.on_dimensions_change())
        
        # Height
        height_frame = tk.Frame(dim_controls, bg='white')
        height_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(height_frame, text="Height:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        y_spinbox = tk.Spinbox(height_frame, from_=50, to=400, textvariable=self.max_y, 
                              width=8, font=('Arial', 10), command=self.on_dimensions_change)
        y_spinbox.pack()
        y_spinbox.bind('<KeyRelease>', lambda e: self.on_dimensions_change())
        
        # Preset buttons
        preset_frame = tk.Frame(dim_section, bg='white')
        preset_frame.pack(fill=tk.X)
        tk.Label(preset_frame, text="Presets:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w', pady=(0, 5))
        
        preset_buttons = tk.Frame(preset_frame, bg='white')
        preset_buttons.pack()
        
        presets = [("A4", 290, 210), ("A5", 210, 148), ("Custom", None, None)]
        for text, width, height in presets:
            if width and height:
                btn = tk.Button(preset_buttons, text=text, 
                               command=lambda w=width, h=height: self.set_dimension_preset(w, h),
                               bg='#607D8B', fg='white', font=('Arial', 9), padx=15, pady=5)
                btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Safety Margins
        margin_section = tk.LabelFrame(main_frame, text="Safety Margins (mm)", font=('Arial', 11, 'bold'),
                                      bg='white', padx=15, pady=10)
        margin_section.pack(fill=tk.X)
        
        margin_controls = tk.Frame(margin_section, bg='white')
        margin_controls.pack(fill=tk.X, pady=(0, 10))
        
        # Horizontal margin
        margin_x_frame = tk.Frame(margin_controls, bg='white')
        margin_x_frame.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(margin_x_frame, text="Horizontal:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        margin_x_spinbox = tk.Spinbox(margin_x_frame, from_=0, to=50, textvariable=self.margin_x, 
                                     width=6, font=('Arial', 10), command=self.on_margins_change)
        margin_x_spinbox.pack()
        margin_x_spinbox.bind('<KeyRelease>', lambda e: self.on_margins_change())
        
        # Vertical margin
        margin_y_frame = tk.Frame(margin_controls, bg='white')
        margin_y_frame.pack(side=tk.LEFT)
        tk.Label(margin_y_frame, text="Vertical:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        margin_y_spinbox = tk.Spinbox(margin_y_frame, from_=0, to=50, textvariable=self.margin_y, 
                                     width=6, font=('Arial', 10), command=self.on_margins_change)
        margin_y_spinbox.pack()
        margin_y_spinbox.bind('<KeyRelease>', lambda e: self.on_margins_change())

    def create_advanced_tab(self, parent):
        """Create advanced options tab"""
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo Settings
        logo_section = tk.LabelFrame(main_frame, text="Logo Settings", font=('Arial', 11, 'bold'),
                                    bg='white', padx=15, pady=10)
        logo_section.pack(fill=tk.X, pady=(0, 15))
        
        logo_checkbox = tk.Checkbutton(logo_section, text="Add logo_short.png to drawings", 
                                      variable=self.enable_logo, bg='white', font=('Arial', 10),
                                      command=self.on_logo_setting_change)
        logo_checkbox.pack(anchor='w', pady=(0, 10))
        
        logo_size_frame = tk.Frame(logo_section, bg='white')
        logo_size_frame.pack(fill=tk.X)
        
        tk.Label(logo_size_frame, text="Logo Size:", font=('Arial', 10, 'bold'), bg='white').pack(side=tk.LEFT)
        logo_size_spinbox = tk.Spinbox(logo_size_frame, from_=10, to=50, width=6, 
                                      textvariable=self.logo_size, font=('Arial', 10),
                                      command=self.on_logo_setting_change)
        logo_size_spinbox.pack(side=tk.LEFT, padx=(10, 5))
        tk.Label(logo_size_frame, text="mm", font=('Arial', 10), bg='white').pack(side=tk.LEFT)
        
        # Dual-arm buffer settings
        buffer_section = tk.LabelFrame(main_frame, text="Dual-arm Buffer Zone", font=('Arial', 11, 'bold'),
                                      bg='white', padx=15, pady=10)
        buffer_section.pack(fill=tk.X)
        
        tk.Label(buffer_section, text="Forbidden buffer radius:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w', pady=(0, 5))
        
        buffer_frame = tk.Frame(buffer_section, bg='white')
        buffer_frame.pack(fill=tk.X)
        
        buffer_spin = tk.Spinbox(buffer_frame, from_=0, to=200, width=8, textvariable=self.forbidden_buffer_var, 
                                font=('Arial', 10), command=lambda: self._on_forbidden_buffer_change())
        buffer_spin.pack(side=tk.LEFT, padx=(0, 5))
        tk.Label(buffer_frame, text="mm", font=('Arial', 10), bg='white').pack(side=tk.LEFT, padx=(0, 10))
        
        # Custom Gear Settings Section
        gear_section = tk.LabelFrame(main_frame, text="Custom Gear Animation", font=('Arial', 11, 'bold'),
                                    bg='white', padx=15, pady=10)
        gear_section.pack(fill=tk.X, pady=(15, 0))
        
        tk.Label(gear_section, text="The app uses 'gear.png' from the current directory as the spinning gear\nduring image conversions. This file must be present for the animation to work.", 
                font=('Arial', 9), bg='white', fg='#666').pack(anchor='w', pady=(5, 0))
        
        tk.Label(buffer_section, text="Creates safety zones around robot positions in dual-arm mode", 
                font=('Arial', 9), bg='white', fg='#666').pack(anchor='w', pady=(5, 0))

    def create_text_generation_tab(self, parent):
        """Create AI text generation settings tab"""
        main_frame = tk.Frame(parent, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text Input Section
        input_section = tk.LabelFrame(main_frame, text="AI Image Generation", font=('Arial', 11, 'bold'),
                                     bg='white', padx=15, pady=10)
        input_section.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        tk.Label(input_section, text="Enter detailed description:", font=('Arial', 10, 'bold'), 
                bg='white').pack(anchor='w', pady=(0, 5))
        
        # Text input area
        text_input_frame = tk.Frame(input_section, bg='white')
        text_input_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.text_entry = tk.Text(text_input_frame, height=8, width=70, 
                                 font=('Arial', 11), relief='solid', bd=1, wrap=tk.WORD)
        self.text_entry.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Generate button
        generate_btn = tk.Button(input_section, text="🤖 Generate Image from Text", 
                command=self.generate_from_text,
                bg='#FF5722', fg='white', font=('Arial', 12, 'bold'),
                relief='flat', padx=20, pady=10, cursor='hand2')
        generate_btn.pack(pady=(0, 15))
        
        # Example prompts
        examples_section = tk.LabelFrame(input_section, text="Example Prompts", font=('Arial', 10, 'bold'),
                                        bg='white', padx=10, pady=5)
        examples_section.pack(fill=tk.X)
        
        examples = [
            "Simple house with a door and two windows",
            "Cat sitting on a chair, line drawing style", 
            "Geometric pattern with circles and triangles",
            "Portrait of a person smiling, sketch style",
            "Tree with branches and leaves, simple outline",
            "Car from the side view, basic shapes"
        ]
        
        for i, example in enumerate(examples):
            btn = tk.Button(examples_section, text=example,
                           command=lambda e=example: self.text_entry.insert(tk.END, e + "\n"),
                           bg='#e0e0e0', fg='#333', font=('Arial', 9),
                           relief='flat', padx=10, pady=3, cursor='hand2')
            btn.pack(fill=tk.X, pady=1)
        if hasattr(self, 'setup_window') and self.setup_window.winfo_exists():
            self.setup_window.lift()
            return

        self.setup_window = tk.Toplevel(self.root)
        self.setup_window.title("Setup")
        self.setup_window.geometry("760x620")
        self.setup_window.configure(bg=self.COLORS['background'])

        # Create scrollable frame for long setup content
        canvas = tk.Canvas(self.setup_window, bg=self.COLORS['background'])
        scrollbar = ttk.Scrollbar(self.setup_window, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.COLORS['background'])

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate the setup with the full image section and the larger controls
        try:
            self.create_image_section(scroll_frame)
        except Exception:
            # If something fails, fall back to manual creation
            pass

        # When closed, update compact main label with current selection
        def on_setup_close():
            try:
                if self.image_path.get() and hasattr(self, 'file_label_main'):
                    self.file_label_main.config(text=f"Selected: {os.path.basename(self.image_path.get())}")
            except Exception:
                pass
            self.setup_window.destroy()

        try:
            self.setup_window.protocol("WM_DELETE_WINDOW", on_setup_close)
        except Exception:
            pass
    
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
            try:
                if hasattr(self, 'file_label') and self.file_label and self.file_label.winfo_exists():
                    self.file_label.config(text=f"Template: {shape.title()}")
            except Exception:
                pass
            
            # Enable face drawing button when template is loaded
            self.face_drawing_btn.config(state='normal')
            self.caricature_btn.config(state='normal')
            
            self.status_text.set(f"{shape.title()} template loaded - processing...")
            
            # Load preview
            self.load_preview_image()
            
            # Process automatically
            self.auto_process_image()
            
            # Template created successfully - no popup needed
            
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
                # Drawing saved successfully - no popup needed
                
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
            try:
                if hasattr(self, 'file_label') and self.file_label and self.file_label.winfo_exists():
                    self.file_label.config(text=f"Drawing: {os.path.basename(self.temp_drawing_path)}")
            except Exception:
                pass
            
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
            # Update the full file label if the setup UI has been created
            try:
                if hasattr(self, 'file_label') and self.file_label:
                    self.file_label.config(text=f"Selected: {filename.split('/')[-1]}", fg='#333')
            except Exception:
                pass
            # Update compact main label if present
            try:
                if hasattr(self, 'file_label_main'):
                    self.file_label_main.config(text=f"Selected: {filename.split('/')[-1]}")
            except Exception:
                pass

            # Enable face drawing button when image is loaded (guarded)
            try:
                self.face_drawing_btn.config(state='normal')
                self.caricature_btn.config(state='normal')
            except Exception:
                pass

            self.load_preview_image()
            self.status_text.set("Image loaded - processing...")
            # Automatically process the image
            self.auto_process_image()
    
    def load_preview_image(self):
        """
        Load and display preview image scaled to fit the available space.
        
        Scales height to fit container while maintaining aspect ratio.
        """
        try:
            # Load with OpenCV
            image = cv2.imread(self.image_path.get())
            if image is None:
                return

            # Convert BGR to RGB for display
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Get original dimensions
            h, w = image_rgb.shape[:2]
            
            # Get available space from the preview container
            if hasattr(self, 'preview_label') and self.preview_label.winfo_exists():
                # Get the actual container dimensions
                container_width = self.preview_label.winfo_width()
                container_height = self.preview_label.winfo_height()
                
                # Use minimum reasonable dimensions if container isn't drawn yet
                if container_width <= 1:
                    container_width = 390  # Single column width minus padding
                if container_height <= 1:
                    container_height = 160  # Available height in preview area
                
                # Add small padding to prevent touching edges
                available_width = container_width - 10
                available_height = container_height - 10
                
                # Calculate scale to fit while maintaining aspect ratio
                scale_w = available_width / w
                scale_h = available_height / h
                scale = min(scale_w, scale_h)  # Use min to fit entire image
                
                # Calculate new dimensions
                new_w, new_h = int(w * scale), int(h * scale)
                
                # Resize image
                image_resized = cv2.resize(image_rgb, (new_w, new_h))

                # Convert to PhotoImage for tkinter
                pil_image = Image.fromarray(image_resized)
                self.preview_image = ImageTk.PhotoImage(pil_image)

                # Display in preview label
                self.preview_label.config(image=self.preview_image, text="")
                self.preview_label.image = self.preview_image  # Keep a reference
                
                # Store current image path for other methods
                self.current_image_path = self.image_path.get()
                
                print(f"Image scaled: {w}x{h} → {new_w}x{new_h} (container: {container_width}x{container_height})")
                
        except Exception as e:
            print(f"Error loading preview: {e}")
            # Reset preview to default state on error
            if hasattr(self, 'preview_label'):
                self.preview_label.config(image="", text="Error loading\nimage preview")
    
    def on_preview_resize(self, event):
        """Handle preview container resize by refreshing image scaling"""
        # Only refresh if we have an image loaded
        if hasattr(self, 'current_image_path') and self.current_image_path:
            # Add small delay to avoid too frequent updates during resize
            self.root.after(100, self.load_preview_image)
    
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
            self.connect_btn.config(text="Connect", bg=self.COLORS['portrait'])
            self.conn_status_label.config(text="⚫ Not Connected", fg='#f44336')
            self.status_text.set("Disconnected from robot")
    
    def _connect_thread(self):
        """Connect in background thread"""
        try:
            ip = self.robot_ip.get().strip()
            port = int(self.robot_port.get().strip())
            port_l = int(self.robot_port_l.get().strip())
            
            # Create new drawer with custom connection
            self.drawer = RobotDrawer(
                ip=ip, 
                port=port,
                port_l=port_l,
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
        self.conn_status_label.config(text="🟢 Connected", fg=self.COLORS['photo_preview'])
        
        # Update robot status in the new tile interface
        if hasattr(self, 'robot_status'):
            self.robot_status.config(text="⚫ Robot: Connected", fg=self.COLORS['photo_preview'])

        self.take_photo_btn.config(state='normal')  # Ensure get picture button available

        # Apply current settings to robot
        if hasattr(self.drawer, 'robot') and self.drawer.robot:
            self.drawer.robot.set_batch_mode(self.use_batch_mode.get())
            self.drawer.robot.set_coordinate_system(self.use_center_origin.get())

        # Recalculate drawing paths / regenerate forbidden zones if we already have an image or drawing
        try:
            # If a drawing or image path exists, re-run automatic processing so the new drawer (with robot settings)
            # recalculates drawing_points and steps similar to when parameters change.
            has_image = bool(self.image_path.get())
            has_temp = hasattr(self, 'temp_drawing_path') and self.temp_drawing_path
            if has_image or has_temp or self.is_processed:
                # Inform user and trigger processing which will update preview and forbidden zones on success
                self.status_text.set("Connected to robot - recalculating paths...")
                try:
                    self.auto_process_image()
                except Exception:
                    # Fallback: regenerate forbidden zones if processing cannot run now
                    try:
                        self._regenerate_forbidden_zones()
                        self.update_robot_preview()
                    except Exception:
                        pass
        except Exception:
            pass

        self.status_text.set("Connected to robot successfully")
    
    def _connection_failed(self):
        """Handle connection failure"""
        self.connect_btn.config(state='normal')
        
        # Update robot status in the new tile interface
        if hasattr(self, 'robot_status'):
            self.robot_status.config(text="🔴 Robot: Failed", fg='red')
            
        # Keep get picture button available for local camera
        self.status_text.set("Failed to connect to robot")
        messagebox.showerror("Connection Error", "Could not connect to robot. Please check IP and port.")
    
    def _connection_error(self, error):
        """Handle connection error"""
        self.connect_btn.config(state='normal')
        # Keep get picture button available for local camera
        self.status_text.set("Connection error")
        messagebox.showerror("Error", f"Connection error: {error}")

    def quick_text_generate(self):
        """Quick text generation with simple prompt dialog"""
        # Simple input dialog for text prompt
        from tkinter import simpledialog
        
        prompt = simpledialog.askstring(
            "AI Image Generation", 
            "Enter description for AI to generate:\n(e.g., 'simple house with door and windows')",
            initialvalue="simple house with door and windows"
        )
        
        if prompt:
            # Create temporary text widget for compatibility with existing generate_from_text
            if not hasattr(self, 'text_entry'):
                self.text_entry = tk.Text(self.root)
            self.text_entry.delete('1.0', tk.END)
            self.text_entry.insert('1.0', prompt)
            self.generate_from_text()

    def _update_connection_display(self, *args):
        """Update connection display for simplified expo interface"""
        if hasattr(self, 'ip_display_label'):
            # Update IP display with connection status  
            ip_text = f"Target: {self.robot_ip.get()}:{self.robot_port.get()}"
            if self.dual_arm_mode.get():
                ip_text += f" & {self.robot_port_l.get()}"
            self.ip_display_label.config(text=ip_text)
        
        if hasattr(self, 'conn_status_label'):
            # Update connection status
            if self.is_connected:
                self.conn_status_label.config(text="🟢 Robot Connected", fg=self.COLORS['photo_preview'])
                if hasattr(self, 'connect_btn'):
                    self.connect_btn.config(text="🔗 Disconnect", bg='#f44336')
            else:
                self.conn_status_label.config(text="⚫ Robot Not Connected", fg='#f44336')
                if hasattr(self, 'connect_btn'):
                    self.connect_btn.config(text="🔗 Connect Robot", bg=self.COLORS['portrait'])
        
        # Keep compatibility with old dual_info_label if it exists
        if hasattr(self, 'dual_info_label'):
            if self.dual_arm_mode.get():
                self.dual_info_label.config(text=f"Dual-arm: {self.robot_ip.get()}:{self.robot_port_l.get()}")
            else:
                self.dual_info_label.config(text="")

    def _on_close(self):
        """Handler run when the main window is closed: save config and disconnect robot."""
        try:
            # Save GUI settings
            self._save_config()
        except Exception:
            pass
        try:
            # Attempt a graceful robot disconnect
            if hasattr(self, 'drawer') and getattr(self.drawer, 'robot', None):
                try:
                    self.drawer.disconnect()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            try:
                import sys
                sys.exit(0)
            except Exception:
                pass
        finally:
            # Ensure voice listener stopped
            try:
                if hasattr(self, '_voice_listener') and self._voice_listener:
                    self._voice_listener.stop()
            except Exception:
                pass
    
    def get_picture_from_robot(self):
        """Show camera preview overlay for user to position themselves before taking picture"""
        self.status_text.set("Opening camera preview...")
        self.show_camera_preview()
    
    def show_camera_preview(self):
        """Show live camera preview with capture controls"""
        # Create camera preview window - massive for full visibility
        self.camera_window = tk.Toplevel(self.root)
        self.camera_window.title("📷 Camera Preview - Position Yourself")
        self.camera_window.geometry("1400x1000")  # Much larger window
        self.camera_window.configure(bg='#2C2C2C')
        self.camera_window.resizable(False, False)
        
        # Make it modal and on top
        self.camera_window.transient(self.root)
        self.camera_window.grab_set()
        self.camera_window.attributes('-topmost', True)
        
        # Title label
        title_frame = tk.Frame(self.camera_window, bg='#2C2C2C')
        title_frame.pack(fill=tk.X, pady=10)
        
        title_label = tk.Label(
            title_frame,
            text="📷 CAMERA PREVIEW",
            font=('Arial', 20, 'bold'),
            fg='white',
            bg='#2C2C2C'
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame,
            text="Position yourself in the frame and click 'Take Photo' when ready",
            font=('Arial', 14),
            fg='#CCCCCC',
            bg='#2C2C2C'
        )
        subtitle_label.pack(pady=(5, 0))
        
        # Camera display frame - expandable to fill window  
        camera_frame = tk.Frame(self.camera_window, bg='#1E1E1E', relief='sunken', bd=3)
        camera_frame.pack(pady=20, padx=20, expand=True, fill='both')
        
        # Camera preview label - let it expand to full image size
        self.camera_label = tk.Label(
            camera_frame,
            text="📹 Initializing camera...",
            font=('Arial', 16),
            fg='white',
            bg='#1E1E1E'
            # Removed width/height constraints to let image fill naturally
        )
        self.camera_label.pack(padx=20, pady=20, expand=True, fill='both')
        
        # Control buttons frame
        controls_frame = tk.Frame(self.camera_window, bg='#2C2C2C')
        controls_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Take Photo button
        self.capture_btn = tk.Button(
            controls_frame,
            text="📸 TAKE PHOTO",
            font=('Arial', 18, 'bold'),
            bg=self.COLORS['photo_preview'],
            fg='white',
            relief='raised',
            bd=4,
            cursor='hand2',
            command=self.capture_photo_from_preview
        )
        self.capture_btn.pack(side=tk.LEFT, padx=(30, 15), pady=15)
        
        # Cancel button
        cancel_btn = tk.Button(
            controls_frame,
            text="❌ CANCEL",
            font=('Arial', 16, 'bold'),
            bg='#F44336',
            fg='white',
            relief='raised',
            bd=4,
            cursor='hand2',
            command=self.close_camera_preview
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(15, 30), pady=15)
        
        # Status label
        self.camera_status = tk.Label(
            self.camera_window,
            text="🔄 Starting camera...",
            font=('Arial', 12),
            fg='#CCCCCC',
            bg='#2C2C2C'
        )
        self.camera_status.pack(pady=(0, 15))
        
        # Initialize camera immediately and faster
        self.root.after(50, self.init_camera)  # Start camera faster
        
        # Handle window close
        self.camera_window.protocol("WM_DELETE_WINDOW", self.close_camera_preview)
    
    def init_camera(self):
        """Initialize camera with faster settings and higher resolution"""
        try:
            # Fast camera initialization with optimized settings for Windows
            self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow for faster init on Windows
            
            if not self.camera.isOpened():
                raise Exception("Could not open camera")
            
            # Set camera properties for speed and quality
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)   # Higher resolution to match display
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)   # Higher resolution 16:9 ratio
            self.camera.set(cv2.CAP_PROP_FPS, 30)            # 30 FPS for smooth preview
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # Reduce buffer for less delay
            
            # Test camera with a quick frame read
            ret, frame = self.camera.read()
            if not ret:
                raise Exception("Could not read from camera")
            
            self.camera_status.config(text="✅ Camera ready - Position yourself and click 'Take Photo'", fg=self.COLORS['photo_preview'])
            self.capture_btn.config(state='normal')
            
            # Start video preview immediately
            self.update_camera_preview()
            
        except Exception as e:
            self.camera_status.config(text=f"❌ Camera error: {str(e)}", fg='#F44336')
            self.camera_label.config(text="📹 Camera not available\n\nPlease check:\n• Camera permissions\n• Camera not used by other apps\n• Camera drivers installed")
            self.capture_btn.config(state='disabled')
    
    def update_camera_preview(self):
        """Update the camera preview continuously with larger display"""
        if hasattr(self, 'camera') and self.camera.isOpened() and hasattr(self, 'camera_window') and self.camera_window.winfo_exists():
            ret, frame = self.camera.read()
            
            if ret:
                # Flip frame horizontally for mirror effect (natural selfie view)
                frame = cv2.flip(frame, 1)
                
                # Convert from BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Resize frame to fit the massive display area for perfect visibility
                display_width = 1280   # Massive width for excellent visibility
                display_height = 720   # Large height maintaining 16:9 aspect ratio
                frame_resized = cv2.resize(frame_rgb, (display_width, display_height))
                
                # Convert to PIL Image and then to PhotoImage
                from PIL import Image, ImageTk
                pil_image = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(pil_image)
                
                # Update label with large preview
                self.camera_label.config(image=photo, text="")
                self.camera_label.image = photo  # Keep a reference
                
            # Schedule next update at 30 FPS for smooth preview
            self.camera_window.after(33, self.update_camera_preview)
        else:
            # Camera lost or window closed
            print("Camera preview stopped - camera or window not available")
    
    def capture_photo_from_preview(self):
        """Capture photo from camera preview"""
        if hasattr(self, 'camera') and self.camera.isOpened():
            ret, frame = self.camera.read()
            
            if ret:
                # Flip frame horizontally (mirror effect)
                frame = cv2.flip(frame, 1)
                
                # Save the captured image
                cv2.imwrite('image.png', frame)
                
                # Close camera and preview window
                self.close_camera_preview()
                
                # Load the captured image into the GUI
                self._load_robot_image(os.path.abspath('image.png'))
                
                self.status_text.set("Photo captured successfully!")
            else:
                messagebox.showerror("Error", "Failed to capture image from camera")
        else:
            messagebox.showerror("Error", "Camera not available")
    
    def close_camera_preview(self):
        """Close camera preview and cleanup"""
        if hasattr(self, 'camera'):
            self.camera.release()
            delattr(self, 'camera')
        
        if hasattr(self, 'camera_window'):
            self.camera_window.destroy()
            delattr(self, 'camera_window')
        
        # Re-enable the take photo button
        try:
            self.take_photo_btn.config(state='normal')
        except Exception:
            pass
        
        self.status_text.set("Camera preview closed")
    
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
        # Robot ready - status shown in GUI, no popup needed
    
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
        """Capture a picture from a local camera in background thread (no FTP)."""
        import os

        try:
            # Use local camera capture utility instead of FTP
            from robot_ftp_downloader import RobotCameraCapture
        except Exception as e:
            print(f"Local camera utility unavailable: {e}")
            self.root.after(0, lambda: self._get_picture_error(f"Local camera utility unavailable: {e}"))
            return

        try:
            cam = RobotCameraCapture()
            ok = cam.capture_image()
            image_path = os.path.abspath(cam.local_path)
            if ok and os.path.exists(image_path):
                print(f"Captured image: {image_path}")
                self.root.after(0, lambda: self._load_robot_image(image_path))
            else:
                print("Failed to capture image from local camera")
                self.root.after(0, self._get_picture_no_image)
        except Exception as e:
            print(f"Local capture error: {e}")
            self.root.after(0, lambda: self._get_picture_error(str(e)))
    
    def _load_robot_image(self, image_path):
        """Load the robot image into the GUI"""
        try:
            # Switch to load mode if not already
            self.drawing_mode.set("load")
            try:
                # Call on_mode_change safely (it already guards against missing widgets)
                self.on_mode_change()
            except Exception:
                pass
            
            # Set the image path
            self.image_path.set(image_path)
            try:
                if hasattr(self, 'file_label') and self.file_label.winfo_exists():
                    self.file_label.config(text="Robot Camera: image.png", fg='#333')
            except Exception:
                pass
            
            # Enable face drawing button when robot image is loaded
            try:
                if hasattr(self, 'face_drawing_btn'):
                    self.face_drawing_btn.config(state='normal')
                if hasattr(self, 'caricature_btn'):
                    self.caricature_btn.config(state='normal')
            except Exception:
                pass
            
            # Load preview
            self.load_preview_image()
            
            # Automatically process the image
            self.status_text.set("Robot image loaded - processing...")
            self.auto_process_image()
            
            self.take_photo_btn.config(state='normal')
            # Picture taken successfully - image loaded in GUI, no popup needed
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load robot image: {e}")
            self.take_photo_btn.config(state='normal')
            self.status_text.set("Failed to load robot image")
    
    def _get_picture_failed(self):
        """Handle get picture failure"""
        self.take_photo_btn.config(state='normal')
        self.status_text.set("Failed to get picture from robot")
        messagebox.showerror("Error", "Failed to send get_pic command to robot")
    
    def _get_picture_no_image(self):
        """Handle case where image.png doesn't exist"""
        self.take_photo_btn.config(state='normal')
        self.status_text.set("No image received from robot")
        messagebox.showwarning("Warning", "No image.png file found after capture")
    
    def _get_picture_error(self, error):
        """Handle get picture error"""
        self.take_photo_btn.config(state='normal')
        self.status_text.set("Get picture error")
        messagebox.showerror("Error", f"Get picture error: {error}")
    
    def auto_process_image(self):
        """Automatically process the selected image or drawing"""
        # Small delay to let UI update
        self.root.after(100, self._start_auto_processing)
    
    def _start_auto_processing(self):
        """Start automatic processing"""
        if hasattr(self, 'progress_indicator'):
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
        if hasattr(self, 'process_btn'):
            self.process_btn.config(state='disabled')
        if hasattr(self, 'progress_indicator'):
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
                logo_settings=logo_settings,
                protect_logo=not self.enable_frame_filtering.get()  # Invert because protect_logo=True disables filtering
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
        if hasattr(self, 'progress_indicator'):
            self.progress_indicator.config(text="✅ Ready to Draw")
        self.status_text.set("Image processed successfully - ready to draw!")
        
        if self.is_connected:
            if hasattr(self, 'draw_btn'):
                self.draw_btn.config(state='normal')
            if hasattr(self, 'start_drawing_btn'):
                self.start_drawing_btn.config(state='normal')
        
        # Enable face drawing button when image is processed (only if it exists)
        if hasattr(self, 'face_drawing_btn'):
            self.face_drawing_btn.config(state='normal')
        if hasattr(self, 'caricature_btn'):
            self.caricature_btn.config(state='normal')
        
        # Update robot path preview
        self.update_robot_preview()
        # Regenerate forbidden zones after a successful processing step
        try:
            self._regenerate_forbidden_zones()
        except Exception:
            pass

    def _on_forbidden_buffer_change(self):
        """Called when the forbidden buffer Spinbox changes value."""
        try:
            if hasattr(self.drawer, 'drawing_points') and self.drawer.drawing_points:
                self._regenerate_forbidden_zones()
        except Exception:
            pass

    def _regenerate_forbidden_zones(self):
        """Regenerate master/slave assignment steps and forbidden polygons from current drawing points.

        Stores the result in `self.forbidden_steps` as a list of dicts with keys:
        remaining, master_role, master, slave, forbidden
        
        Only runs in dual-arm mode. In single-arm mode, forbidden zones are not needed.
        """
        # Only run forbidden zone calculations in dual-arm mode
        if not self.dual_arm_mode.get():
            self.forbidden_steps = []
            return
            
        try:
            from coordinate_transformer import master_slave_assign_contours
        except Exception:
            return

        contours = getattr(self.drawer, 'drawing_points', None)
        if not contours:
            self.forbidden_steps = []
            return

        steps = []
        remaining = contours[:]
        master_role = 'right'
        buf_mm = int(self.forbidden_buffer_var.get()) if hasattr(self, 'forbidden_buffer_var') else 40
        while remaining:
            result = master_slave_assign_contours(remaining, master=master_role, buffer_radius=buf_mm)
            if len(result) == 5:
                master, slave, rest, unassigned, forbidden_poly = result
            else:
                master, slave, rest, unassigned = result
                forbidden_poly = None
            steps.append({'remaining': remaining[:], 'master_role': master_role, 'master': master, 'slave': slave, 'forbidden': forbidden_poly})
            remaining = rest
            master_role = 'left' if master_role == 'right' else 'right'

        self.forbidden_steps = steps
        # small visual/status hint
        try:
            self.status_text.set(f"Forbidden zones regenerated ({len(steps)} steps)")
        except Exception:
            pass
    
    def _process_failed(self):
        """Handle processing failure"""
        if hasattr(self, 'progress_indicator'):
            self.progress_indicator.config(text="❌ Failed")
        self.status_text.set("Processing failed")
        messagebox.showerror("Error", "Failed to process image")
    
    def _process_error(self, error):
        """Handle processing error"""
        if hasattr(self, 'progress_indicator'):
            self.progress_indicator.config(text="❌ Error")
        self.status_text.set("Processing error")
        messagebox.showerror("Error", f"Processing error: {error}")
    
    def update_robot_preview(self):
        """Update robot path preview with current coordinate system"""
        try:
            # Skip matplotlib preview in simple interface mode
            if not hasattr(self, 'ax') or self.ax is None:
                return
                
            max_x = self.max_x.get()
            max_y = self.max_y.get()

            # Clear and prepare axes
            self.ax.clear()

            # Set coordinate system based on user selection
            use_center = self.use_center_origin.get()
            if use_center:
                self.ax.set_xlim(-max_x/2, max_x/2)
                self.ax.set_ylim(-max_y/2, max_y/2)
                origin_x, origin_y = 0, 0
            else:
                self.ax.set_xlim(0, max_x)
                self.ax.set_ylim(0, max_y)
                origin_x, origin_y = 0, 0
            
            # Invert y-axis so (0,0) is at top-left corner
            self.ax.invert_yaxis()

            # Reduce outer margins so drawing fills the preview
            try:
                self.fig.subplots_adjust(left=0.06, right=0.98, top=0.9, bottom=0.08)
                self.ax.set_position([0.06, 0.08, 0.88, 0.86])
            except Exception:
                pass

            self.ax.set_xlabel('X (mm)', fontsize=9)
            self.ax.set_ylabel('Y (mm)', fontsize=9)
            self.ax.grid(True, alpha=0.3)

            # Ensure 1mm == 1mm and eliminate data margins
            self.ax.set_aspect('equal', adjustable='box')
            try:
                self.ax.margins(0)
            except Exception:
                pass

            # Draw drawing area boundary
            if use_center:
                boundary_x = [-max_x/2, max_x/2, max_x/2, -max_x/2, -max_x/2]
                boundary_y = [-max_y/2, -max_y/2, max_y/2, max_y/2, -max_y/2]
            else:
                boundary_x = [0, max_x, max_x, 0, 0]
                boundary_y = [0, 0, max_y, max_y, 0]

            self.ax.plot(boundary_x, boundary_y, 'k-', linewidth=2.5, alpha=0.9)

            # Plot left-forbidden rectangle (0,0) to (130,40) - always visible in corner origin mode
            if not use_center:  # Only show in corner origin mode where this constraint applies
                left_forbidden_x = [0, 130, 130, 0, 0]
                left_forbidden_y = [0, 0, 40, 40, 0]
                self.ax.fill(left_forbidden_x, left_forbidden_y, color='pink', alpha=0.3, 
                           label='Left-forbidden (0,0)-(130,40)')
                self.ax.plot(left_forbidden_x, left_forbidden_y, color='red', linewidth=2, 
                           linestyle='--', alpha=0.8)

            # Plot effective drawing area (margins) if present
            margin_x = self.margin_x.get()
            margin_y = self.margin_y.get()
            if margin_x > 0 or margin_y > 0:
                if use_center:
                    eff_x = [-(max_x/2-margin_x), (max_x/2-margin_x), (max_x/2-margin_x), -(max_x/2-margin_x), -(max_x/2-margin_x)]
                    eff_y = [-(max_y/2-margin_y), -(max_y/2-margin_y), (max_y/2-margin_y), (max_y/2-margin_y), -(max_y/2-margin_y)]
                else:
                    eff_x = [margin_x, max_x-margin_x, max_x-margin_x, margin_x, margin_x]
                    eff_y = [margin_y, margin_y, max_y-margin_y, max_y-margin_y, margin_y]
                self.ax.plot(eff_x, eff_y, 'g-', linewidth=1.8, alpha=0.8)

            # Origin marker
            self.ax.plot(origin_x, origin_y, 'r+', markersize=9, markeredgewidth=2)

            # If no drawing points, show centered message
            if not getattr(self.drawer, 'drawing_points', None):
                coord_info = 'center' if use_center else 'corner'
                self.ax.text(0.5, 0.5, f'No path generated\n(0,0) at {coord_info}', ha='center', va='center', transform=self.ax.transAxes, fontsize=11, color='#666')
                self.canvas_widget.draw_idle()
                return

            # Plot paths with larger stroke and markers for visibility
            colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(self.drawer.drawing_points))))
            for i, path in enumerate(self.drawer.drawing_points):
                if path and len(path) > 0:
                    x_coords = [p[0] for p in path]
                    y_coords = [p[1] for p in path]
                    self.ax.plot(x_coords, y_coords, '-', color=colors[i % len(colors)], linewidth=2.2, alpha=0.95)
                    # small markers at points for clarity
                    self.ax.plot(x_coords, y_coords, 'o', color=colors[i % len(colors)], markersize=3.5, alpha=0.9)

            total_points = sum(len(path) for path in self.drawer.drawing_points)
            coord_info = 'center' if use_center else 'corner'
            margin_info = f" (margins: {margin_x}x{margin_y}mm)" if margin_x > 0 or margin_y > 0 else ''
            self.ax.set_title(f'{len(self.drawer.drawing_points)} paths, {total_points} points ({coord_info} origin{margin_info})', fontsize=10)

            self.fig.tight_layout(pad=0.5)
            try:
                self.canvas_widget.draw_idle()
            except Exception:
                self.canvas_widget.draw()
            
        except Exception as e:
            print(f"Preview error: {e}")
    
    def disable_all_buttons(self):
        """Disable all buttons during processing to show conversion is happening"""
        # Main action buttons
        if hasattr(self, 'take_photo_btn'):
            self.take_photo_btn.config(state='disabled')
        if hasattr(self, 'start_drawing_btn'):
            self.start_drawing_btn.config(state='disabled')
        
        # All portrait buttons (10 buttons in diagonal)
        for i in range(1, 11):
            btn_name = f'portrait_btn{i}'
            if hasattr(self, btn_name):
                getattr(self, btn_name).config(state='disabled')
        
        # All caricature buttons (9 buttons in diagonal)
        for i in range(1, 10):
            btn_name = f'caricature_btn{i}'
            if hasattr(self, btn_name):
                getattr(self, btn_name).config(state='disabled')
        
        # Disable triangle overlay to prevent clicks and show disabled appearance
        if hasattr(self, 'triangle_overlay'):
            self.triangle_buttons_disabled = True
            # Keep click event bound so blinking still works during processing
            # self.triangle_overlay.unbind('<Button-1>')  # Commented out to keep blinking
            self.draw_triangle_buttons_disabled(self.triangle_overlay)
    
    def enable_all_buttons(self):
        """Re-enable all buttons after processing is complete"""
        # Main action buttons
        if hasattr(self, 'take_photo_btn'):
            self.take_photo_btn.config(state='normal')
        if hasattr(self, 'start_drawing_btn'):
            self.start_drawing_btn.config(state='normal')
        
        # All portrait buttons (10 buttons in diagonal)
        for i in range(1, 11):
            btn_name = f'portrait_btn{i}'
            if hasattr(self, btn_name):
                getattr(self, btn_name).config(state='normal')
        
        # All caricature buttons (9 buttons in diagonal)
        for i in range(1, 10):
            btn_name = f'caricature_btn{i}'
            if hasattr(self, btn_name):
                getattr(self, btn_name).config(state='normal')
        
        # Re-enable triangle overlay by rebinding click events
        if hasattr(self, 'triangle_overlay'):
            self.triangle_buttons_disabled = False
            # Click event should already be bound, just update the appearance
            # self.triangle_overlay.bind('<Button-1>', self.handle_triangle_click)  # Already bound
            self.draw_triangle_buttons_smart(self.triangle_overlay)

    def set_style_and_convert(self, style):
        """Set drawing style and apply conversion if needed"""
        self.drawing_style.set(style)
        
        # Style selection debug removed - no popup needed
        
        # Check if we have an image to process
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            messagebox.showwarning("Warning", "Please take a photo first!")
            return
        
        # Disable all buttons to show processing is happening
        self.disable_all_buttons()
        
        try:
            if style == "portrait":
                self.convert_to_face_drawing()
            elif style == "caricature":
                # Convert to caricature using the proper caricature method
                self.convert_to_caricature()
        except Exception as e:
            # If there's an immediate error (not in thread), re-enable buttons
            self.enable_all_buttons()
            # Restore triangle overlay
            if hasattr(self, 'triangle_overlay'):
                self.draw_triangle_buttons_smart(self.triangle_overlay)
            raise e

    def start_drawing(self):
        """Start drawing with current image and style settings"""
        # Check if robot is connected
        if not self.is_connected:
            messagebox.showwarning("Warning", "Please connect to robot first!\nUse the Setup window to configure robot connection.")
            return
        
        # Check if image is processed
        if not hasattr(self, 'current_image_path') or not self.current_image_path:
            messagebox.showwarning("Warning", "Please take a photo first!")
            return
        
        # Apply style processing if needed
        style = self.drawing_style.get()
        if style == "portrait":
            self.convert_to_face_drawing()
        elif style == "caricature":
            # For caricature, we could apply special processing here
            self.auto_process_image()
        else:
            # Normal processing
            self.auto_process_image()
        
        # Update progress
        if hasattr(self, 'progress_label'):
            self.progress_label.config(text="Starting drawing...")
        
        # Start the actual robot drawing
        self.start_robot_drawing()

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
        
        # Start drawing immediately without confirmation
        import time
        self._draw_start_time = time.time()
        
        # Print start message to terminal
        print(f"🚀 Starting robot drawing...")
        print(f"📊 Total points to draw: {total_points}")
        drawing_mode = "dual-arm" if self.dual_arm_mode.get() else "single-arm"
        coord_system = "center" if self.use_center_origin.get() else "corner"
        print(f"🤖 Mode: {drawing_mode}, Coordinates: {coord_system}")
        print(f"⏰ Start time: {time.strftime('%H:%M:%S', time.localtime(self._draw_start_time))}")
        
        # Update robot with current coordinate system before starting
        if hasattr(self.drawer, 'robot') and self.drawer.robot:
            self.drawer.robot.set_coordinate_system(self.use_center_origin.get())
        
        # Show progress elements in status bar (safely check if they exist)
        if hasattr(self, 'progress_container'):
            self.progress_container.pack(side=tk.RIGHT, before=self.progress_indicator)
        if hasattr(self, 'stop_btn'):
            self.stop_btn.pack(pady=(10, 0))
            
        self.drawing_active = True
        self.status_text.set(f"Initializing robot with {coord_system} coordinates ({command_type})...")
        
        # Disable drawing buttons safely
        if hasattr(self, 'draw_btn'):
            self.draw_btn.config(state='disabled')
        if hasattr(self, 'start_drawing_btn'):
            self.start_drawing_btn.config(state='disabled', text="Drawing...", bg=self.COLORS['drawing_active'])
            
        self.progress_indicator.config(text="🤖 Initializing...")
        
        # Update progress in the new interface
        if hasattr(self, 'progress_label'):
            self.progress_label.config(text="🤖 Starting robots...", fg=self.COLORS['photo_preview'])
            
        # Setup progress tracking
        total_points = sum(len(path) for path in self.drawer.drawing_points)
        if hasattr(self, 'bottom_progress_bar'):
            self.bottom_progress_bar.config(maximum=total_points)
        self.bottom_progress_bar.config(value=0)
        self.bottom_progress_label.config(text=f"0 / {total_points} points")
        thread = threading.Thread(target=self._draw_thread)
        thread.daemon = True
        thread.start()
    
    def emergency_stop(self):
        """ stop the drawing process"""
        if self.drawing_active:
            # Print  stop message to terminal with timing if available
            if hasattr(self, '_draw_start_time'):
                elapsed = time.time() - self._draw_start_time
                mins = int(elapsed // 60)
                secs = int(elapsed % 60)
                print(f"🛑  STOP triggered after {mins} min {secs} sec ({elapsed:.1f} seconds)")
            else:
                print(f"🛑  STOP triggered")

            self.drawing_active = False
            try:
                # Send emergency stop to robot
                if self.drawer.robot and self.drawer.robot.socket:
                    # Send IMMEDIATE stop command to appropriate arms (no pen movement to avoid collisions)
                    if self.dual_arm_mode.get():
                        # In dual-arm mode, stop both arms immediately
                        print("🛑 EMERGENCY STOP: Sending IMMEDIATE halt to BOTH arms")
                        self.drawer.send_stop(target='both')
                        self.status_text.set("EMERGENCY STOP sent to both arms")
                    else:
                        # Single arm mode, stop right arm immediately
                        print("🛑 EMERGENCY STOP: Sending IMMEDIATE halt to RIGHT arm")
                        self.drawer.send_stop(target='right')
                        self.status_text.set("EMERGENCY STOP sent to robot")
                else:
                    self.status_text.set("Drawing stopped (no robot connection)")
                # Drawing stopped - status shown in GUI, no popup needed
            except Exception as e:
                messagebox.showerror("Error", f"Could not stop robot: {e}")
                self.status_text.set("Stop command failed")
            
            # Hide progress elements
            self.progress_container.pack_forget()
            self.stop_btn.pack_forget()
            if hasattr(self, 'draw_btn'): self.draw_btn.config(state='normal')
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
            
            # Check if we should continue (emergency stop may have been pressed)
            if not self.drawing_active:
                print("Drawing stopped before START command")
                return
            
            print(f"Sending {command_type} command to robot...")
            self.root.after(0, lambda: self.status_text.set(f"Sending {command_type} command to robot..."))
            
            # If dual-arm mode is enabled, send the START command to both robot sockets
            if self.dual_arm_mode.get():
                # _send_command supports a 'target' argument; using 'both' will send to both sockets
                print("Dual-arm mode enabled - sending START to both robots (may take up to 90s)...")
                success = self.drawer.robot._send_command("START\n", wait_response=True, timeout=self.drawer.robot.START_COMMAND_TIMEOUT, target='both')
            else:
                success = self.drawer.robot.send_start()  # This automatically chooses START vs START_CORNER

            # Check if we should continue after START command
            if not self.drawing_active:
                print("Drawing stopped after START command")
                return

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
                
                # Create progress callback that updates GUI and checks for stop
                def progress_callback(current_batch, total_batches, points_sent, total_points):
                    if self.drawing_active:  # Only update if drawing is still active
                        percent = (points_sent / total_points) * 100 if total_points > 0 else 0
                        self.root.after(0, self._update_progress, points_sent, total_points, percent)
                        return True  # Continue drawing
                    else:
                        return False  # Stop drawing
                
                # Create a stop check function for the drawer
                def should_continue():
                    return self.drawing_active
                
                # Pass the stop check to the drawer
                if hasattr(self.drawer, 'set_stop_check'):
                    self.drawer.set_stop_check(should_continue)
                
                # Final check before starting drawing operations
                if not self.drawing_active:
                    print("Drawing stopped before starting drawing operations")
                    return
                
                # Start the optimized drawing process with progress tracking
                if self.dual_arm_mode.get():
                    print("Starting dual-arm drawing flow (draw_dual)")
                    buf_mm = int(self.forbidden_buffer_var.get()) if hasattr(self, 'forbidden_buffer_var') else 40
                    success = self.drawer.draw_dual(buffer_radius=buf_mm, progress_callback=progress_callback)
                else:
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
        if hasattr(self, 'draw_btn'): 
            self.draw_btn.config(state='normal')
        if hasattr(self, 'start_drawing_btn'): 
            self.start_drawing_btn.config(state='normal', text="START\nDRAWING", bg=self.COLORS['start_drawing'])
        
        self.progress_indicator.config(text="🎉 Complete")
        self.status_text.set("Drawing completed successfully!")
        
        # Update progress in the new interface
        if hasattr(self, 'progress_label'):
            self.progress_label.config(text="🎉 Drawing complete!", fg=self.COLORS['start_drawing'])
            
        # Hide progress elements (safely check if they exist)
        if hasattr(self, 'progress_container'):
            self.progress_container.pack_forget()
        if hasattr(self, 'stop_btn'):
            self.stop_btn.pack_forget()
        elapsed = None
        if hasattr(self, '_draw_start_time'):
            elapsed = time.time() - self._draw_start_time
        if elapsed is not None:
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            # Print drawing time to terminal
            print(f"🎉 Drawing completed successfully!")
            print(f"⏱️  Total drawing time: {mins} min {secs} sec ({elapsed:.1f} seconds)")
            msg = f"Drawing completed successfully!\n\nTime taken: {mins} min {secs} sec"
        else:
            print(f"🎉 Drawing completed successfully!")
            msg = "Drawing completed successfully!"
        # Drawing completed - status shown in GUI, no popup needed
    
    def _draw_failed(self):
        """Handle drawing failure"""
        # Print failure message to terminal with timing if available
        if hasattr(self, '_draw_start_time'):
            elapsed = time.time() - self._draw_start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            print(f"❌ Drawing failed after {mins} min {secs} sec ({elapsed:.1f} seconds)")
        else:
            print(f"❌ Drawing failed")
            
        self.drawing_active = False
        if hasattr(self, 'draw_btn'): 
            self.draw_btn.config(state='normal')
        if hasattr(self, 'start_drawing_btn'): 
            self.start_drawing_btn.config(state='normal', text="START\nDRAWING", bg=self.COLORS['start_drawing'])
            
        self.progress_indicator.config(text="❌ Failed")
        self.status_text.set("Drawing failed")
        
        # Update progress in the new interface
        if hasattr(self, 'progress_label'):
            self.progress_label.config(text="❌ Drawing failed", fg=self.COLORS['take_photo'])
        
        # Hide progress elements (safely check if they exist)
        if hasattr(self, 'progress_container'):
            self.progress_container.pack_forget()
        if hasattr(self, 'stop_btn'):
            self.stop_btn.pack_forget()
        
        messagebox.showerror("Error", "Drawing failed")
    
    def _draw_error(self, error):
        """Handle drawing error"""
        self.drawing_active = False
        if hasattr(self, 'draw_btn'): 
            self.draw_btn.config(state='normal')
        if hasattr(self, 'start_drawing_btn'): 
            self.start_drawing_btn.config(state='normal', text="START\nDRAWING", bg=self.COLORS['start_drawing'])
            
        self.progress_indicator.config(text="❌ Error")
        self.status_text.set("Drawing error")
        
        # Update progress in the new interface
        if hasattr(self, 'progress_label'):
            self.progress_label.config(text="❌ Error occurred", fg=self.COLORS['take_photo'])
        
        # Hide progress elements (safely check if they exist)
        if hasattr(self, 'progress_container'):
            self.progress_container.pack_forget()
        if hasattr(self, 'stop_btn'):
            self.stop_btn.pack_forget()
        
        messagebox.showerror("Error", f"Drawing error: {error}")
    
    def _start_conversion_feedback(self, conversion_type):
        """Start visual feedback for image conversion process"""
        # Show progress container with indeterminate progress bar
        self.progress_container.pack(side=tk.RIGHT, before=self.progress_indicator)
        self.bottom_progress_bar.config(mode='indeterminate')
        self.bottom_progress_bar.start(10)  # Start animated progress bar
        self.bottom_progress_label.config(text=f"Converting to {conversion_type}...")
        
        # Update status
        self.status_text.set(f"Converting to {conversion_type}...")
        self.progress_indicator.config(text=f"🔄 Converting...")
        
        # Flash the main window to get user attention
        try:
            self.root.bell()  # System sound
        except Exception:
            pass
            
        # Add animated overlay to the image preview
        self._start_conversion_overlay(conversion_type)
    
    def _stop_conversion_feedback(self):
        """Stop visual feedback for image conversion process"""
        # Stop and hide progress bar
        self.bottom_progress_bar.stop()
        self.progress_container.pack_forget()
        
        # Stop overlay animation
        self._stop_conversion_overlay()
    
    def _create_gear_polygon(self, canvas, center_x, center_y, gear_size, rotation_angle=0):
        """Create a gear from custom image (always available)"""
        try:
            # Rotate the image
            rotated_image = self._rotate_image(self.custom_gear_image, rotation_angle)

            # Calculate image position and size - fix the redundant min() call
            image_size = gear_size * 2  # Scale appropriately
            x1 = center_x - image_size // 2
            y1 = center_y - image_size // 2
            x2 = center_x + image_size // 2
            y2 = center_y + image_size // 2

            # Store reference to prevent garbage collection
            self.current_gear_image = rotated_image

            # Create image on canvas
            gear_id = canvas.create_image(center_x, center_y, image=rotated_image, tags="conversion_overlay")

            print(f"DEBUG: Gear created at ({center_x}, {center_y}) with size {image_size}")
            return gear_id
        except Exception as e:
            print(f"Failed to use custom gear image: {e}")
            # This should never happen since gear.png is always present
            return None
    
    def _rotate_image(self, image, angle):
        """Rotate a PIL image by the given angle"""
        try:
            from PIL import Image, ImageTk
            # Convert angle to degrees if needed
            angle_deg = math.degrees(angle) if angle != 0 else 0

            # Rotate the image
            rotated = image.rotate(-angle_deg, expand=True)  # Negative for clockwise rotation

            # Convert back to PhotoImage for Tkinter and keep reference
            photo_image = ImageTk.PhotoImage(rotated)

            # Store reference to prevent garbage collection
            if not hasattr(self, 'gear_image_refs'):
                self.gear_image_refs = []
            self.gear_image_refs.append(photo_image)

            # Keep only the last few references to avoid memory buildup
            if len(self.gear_image_refs) > 10:
                self.gear_image_refs.pop(0)

            print(f"DEBUG: Image rotated by {angle_deg}°")
            return photo_image
        except ImportError:
            print("PIL not available for image rotation")
            return image
        except Exception as e:
            print(f"Image rotation failed: {e}")
            return image
    
    def load_custom_gear_image(self, image_path=None):
        """Load gear.png from current directory (always present)"""
        try:
            from PIL import Image, ImageTk
            import os
            
            gear_path = os.path.join(os.getcwd(), "gear.png")
            # Load and resize the image
            image = Image.open(gear_path)
            
            # Resize to a reasonable size (will be scaled later)
            image = image.resize((100, 100), Image.Resampling.LANCZOS)
            
            # Store the PIL image for rotation
            self.custom_gear_image = image
            
            # Create PhotoImage for immediate use
            self.custom_gear_photo = ImageTk.PhotoImage(image)
            
            print(f"Custom gear loaded from: {gear_path}")
            return True
            
        except ImportError:
            print("PIL not available. Install with: pip install pillow")
            return False
        except Exception as e:
            print(f"Failed to load gear.png: {e}")
            return False
    

    def _start_conversion_overlay(self, conversion_type):
        """Add animated overlay to image preview during conversion"""
        print(f"DEBUG: _start_conversion_overlay called with {conversion_type}")
        try:
            # Create overlay canvas on top of preview_label if it exists
            if hasattr(self, 'preview_label') and self.preview_label.winfo_exists():
                # Get preview_label position and size
                preview_x = self.preview_label.winfo_x()
                preview_y = self.preview_label.winfo_y()
                preview_width = self.preview_label.winfo_width()
                preview_height = self.preview_label.winfo_height()

                if preview_width > 100 and preview_height > 100:  # Preview is properly sized
                    # Get absolute position of preview_label
                    preview_abs_x = self.preview_label.winfo_rootx() - self.root.winfo_rootx()
                    preview_abs_y = self.preview_label.winfo_rooty() - self.root.winfo_rooty()

                    # Create overlay canvas positioned over the preview_label
                    self.overlay_canvas = tk.Canvas(
                        self.root,  # Use root as parent for absolute positioning
                        width=preview_width,
                        height=preview_height,
                        highlightthickness=0,
                        bg='white'  # White background
                    )

                    # Position overlay canvas exactly over preview_label using absolute coordinates
                    self.overlay_canvas.place(
                        x=preview_abs_x,
                        y=preview_abs_y,
                        width=preview_width,
                        height=preview_height
                    )
                    
                    print(f"DEBUG: preview_label exists - size: {preview_width}x{preview_height}, pos: {preview_x},{preview_y}, abs: {preview_abs_x},{preview_abs_y}")
                    
                    # Create semi-transparent overlay with white background
                    self.conversion_overlay = self.overlay_canvas.create_rectangle(
                        0, 0, preview_width, preview_height,
                        fill='white', tags="conversion_overlay")

                    # Create large centered text with black color for contrast
                    self.conversion_text = self.overlay_canvas.create_text(
                        preview_width // 2, preview_height // 2 + 30,
                        text=f"Converting to\n{conversion_type}...",
                        fill='black', font=('Arial', 16, 'bold'),
                        tags="conversion_overlay", justify='center')

                    # Create spinning gear animation - responsive sizing
                    gear_size = min(preview_width, preview_height) // 8  # Scale with canvas size
                    gear_center_x = preview_width // 2
                    gear_center_y = preview_height // 2 - 30

                    # Create gear as a single polygon with integrated teeth - one color design
                    self.gear_id = self._create_gear_polygon(self.overlay_canvas, gear_center_x, gear_center_y, gear_size, 0)
                    
                    # No gear center hole needed - using custom image

                    # Start animations
                    self.conversion_dots = 0
                    self.gear_angle = 0
                    print(f"DEBUG: Starting gear animation for {conversion_type}")
                    self._animate_conversion_text(conversion_type)
                    self._animate_spinning_gear()

                    # Bring overlay to front
                    try:
                        self.overlay_canvas.lift()
                        print(f"DEBUG: Overlay canvas lifted")
                    except Exception as e:
                        print(f"DEBUG: Could not lift overlay canvas: {e}")

                    # Bind resize event to update overlay position and size
                    self.root.bind('<Configure>', self._update_overlay_position)
            elif hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                canvas_width = self.original_canvas.winfo_width()
                canvas_height = self.original_canvas.winfo_height()

                if canvas_width > 100 and canvas_height > 100:  # Canvas is properly sized
                    # Create semi-transparent overlay with white background
                    self.conversion_overlay = self.original_canvas.create_rectangle(
                        0, 0, canvas_width, canvas_height,
                        fill='white', tags="conversion_overlay")

                    # Create large centered text with black color for contrast
                    self.conversion_text = self.original_canvas.create_text(
                        canvas_width // 2, canvas_height // 2 + 30,
                        text=f"Converting to\n{conversion_type}...",
                        fill='black', font=('Arial', 16, 'bold'),
                        tags="conversion_overlay", justify='center')

                    # Create spinning gear animation - larger and more visible
                    gear_size = 40  # Increased size
                    gear_center_x = canvas_width // 2
                    gear_center_y = canvas_height // 2 - 30

                    # Create gear as a single polygon with integrated teeth - one color design
                    self.gear_id = self._create_gear_polygon(self.original_canvas, gear_center_x, gear_center_y, gear_size, 0)
                    
                    # No gear center hole needed - using custom image

                    # Start animations
                    self.conversion_dots = 0
                    self.gear_angle = 0
                    self._animate_conversion_text(conversion_type)
                    self._animate_spinning_gear()
        except Exception as e:
            print(f"Error creating conversion overlay: {e}")
            pass
    
    def _animate_conversion_text(self, conversion_type):
        """Animate the conversion overlay text"""
        try:
            # Determine which canvas to use for animation
            active_canvas = None
            if hasattr(self, 'overlay_canvas') and self.overlay_canvas.winfo_exists():
                active_canvas = self.overlay_canvas
            elif hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                active_canvas = self.original_canvas
            
            if hasattr(self, 'conversion_text') and active_canvas:
                # Cycle through different dot patterns
                dots = "." * (self.conversion_dots % 4)
                self.conversion_dots += 1
                
                # Update text with animated dots
                active_canvas.itemconfig(
                    self.conversion_text, 
                    text=f"🔄 Converting to\n{conversion_type}{dots}")
                
                # Schedule next animation frame
                self.conversion_animation_id = self.root.after(500, lambda: self._animate_conversion_text(conversion_type))
        except Exception:
            pass
    
    def _animate_spinning_gear(self):
        """Animate the spinning gear during conversion"""
        try:
            # Determine which canvas to use for animation
            active_canvas = None
            if hasattr(self, 'overlay_canvas') and self.overlay_canvas.winfo_exists():
                active_canvas = self.overlay_canvas
            elif hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                active_canvas = self.original_canvas

            if active_canvas and hasattr(self, 'gear_id'):
                canvas_width = active_canvas.winfo_width()
                canvas_height = active_canvas.winfo_height()
                gear_center_x = canvas_width // 2
                gear_center_y = canvas_height // 2 - 30
                gear_size = min(canvas_width, canvas_height) // 8  # Responsive sizing

                # Update gear angle for rotation (slower for better visibility)
                self.gear_angle = (self.gear_angle + 2) % 360  # Slower rotation

                # Rotate the entire gear polygon by recreating it at the new angle
                if hasattr(self, 'gear_id'):
                    # Delete the old gear
                    active_canvas.delete(self.gear_id)
                    print(f"DEBUG: Deleted old gear, creating new one at angle {self.gear_angle}")
                    # Create new gear at rotated position
                    self.gear_id = self._create_gear_polygon(active_canvas, gear_center_x, gear_center_y, gear_size, self.gear_angle)

                # Continue animation if still converting (check both overlay and original canvas)
                should_continue = False
                if hasattr(self, 'conversion_overlay') and self.conversion_overlay:
                    should_continue = True
                elif hasattr(self, 'original_canvas') and hasattr(self, 'conversion_text'):
                    should_continue = True

                if should_continue:
                    print(f"DEBUG: Continuing animation, next frame in 80ms")
                    self.root.after(80, self._animate_spinning_gear)  # Slower animation
                else:
                    print(f"DEBUG: Stopping animation - no conversion overlay found")
        except Exception as e:
            print(f"Animation error: {e}")
            # Silently handle animation errors
            pass
    
    def _update_overlay_position(self, event=None):
        """Update overlay position and size when window is resized"""
        try:
            if hasattr(self, 'overlay_canvas') and self.overlay_canvas.winfo_exists():
                if hasattr(self, 'preview_label') and self.preview_label.winfo_exists():
                    # Get updated preview_label position and size
                    preview_abs_x = self.preview_label.winfo_rootx() - self.root.winfo_rootx()
                    preview_abs_y = self.preview_label.winfo_rooty() - self.root.winfo_rooty()
                    preview_width = self.preview_label.winfo_width()
                    preview_height = self.preview_label.winfo_height()

                    # Update overlay canvas position and size
                    self.overlay_canvas.place(
                        x=preview_abs_x,
                        y=preview_abs_y,
                        width=preview_width,
                        height=preview_height
                    )

                    # Update overlay rectangle size
                    if hasattr(self, 'conversion_overlay'):
                        self.overlay_canvas.coords(self.conversion_overlay, 0, 0, preview_width, preview_height)

                    # Update text position
                    if hasattr(self, 'conversion_text'):
                        self.overlay_canvas.coords(self.conversion_text, preview_width // 2, preview_height // 2 + 30)

                    # Update gear size and position if it exists
                    if hasattr(self, 'gear_id'):
                        self._update_gear_size_and_position(preview_width, preview_height)

                    # Bring overlay to front
                    try:
                        self.overlay_canvas.lift()
                    except Exception as e:
                        print(f"Error lifting overlay canvas: {e}")

        except Exception as e:
            print(f"Error updating overlay position: {e}")
            pass
    
    def _update_gear_size_and_position(self, canvas_width, canvas_height):
        """Update gear size and position to fit current canvas dimensions"""
        try:
            # Calculate new gear size based on canvas dimensions
            gear_size = min(canvas_width, canvas_height) // 8
            gear_center_x = canvas_width // 2
            gear_center_y = canvas_height // 2 - 30

            # Recreate the gear polygon at new size and position
            if hasattr(self, 'gear_id'):
                self.overlay_canvas.delete(self.gear_id)
                current_angle = getattr(self, 'gear_angle', 0)
                self.gear_id = self._create_gear_polygon(self.overlay_canvas, gear_center_x, gear_center_y, gear_size, current_angle)

        except Exception as e:
            print(f"Error updating gear size and position: {e}")
            pass
    
    def _stop_conversion_overlay(self):
        try:
            # Cancel animation
            if hasattr(self, 'conversion_animation_id'):
                self.root.after_cancel(self.conversion_animation_id)
                
            # Remove overlay elements from both possible canvases
            if hasattr(self, 'overlay_canvas') and self.overlay_canvas.winfo_exists():
                self.overlay_canvas.delete("conversion_overlay")
                # Destroy the overlay canvas itself
                self.overlay_canvas.destroy()
                delattr(self, 'overlay_canvas')
                
            if hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                self.original_canvas.delete("conversion_overlay")
                
            # Clean up gear animation variables
            if hasattr(self, 'gear_id'):
                delattr(self, 'gear_id')
            if hasattr(self, 'gear_angle'):
                delattr(self, 'gear_angle')
        except Exception:
            pass
    
    def _show_conversion_notification(self, message, msg_type="info"):
        """Show a temporary notification for conversion status - disabled for expo"""
        # Success notifications disabled for cleaner expo experience
        if msg_type == "success":
            return  # No success notifications shown
        
        # Still show error notifications for debugging
        if msg_type == "error":
            # Create a temporary notification in the original canvas area
            try:
                if hasattr(self, 'original_canvas') and self.original_canvas.winfo_exists():
                    # Clear any existing notification
                    self.original_canvas.delete("notification")
                    
                    # Add notification text overlay for errors only
                    bg_color = "#f44336"
                    text_color = "white"
                    
                    # Create notification rectangle and text
                    canvas_width = self.original_canvas.winfo_width()
                    canvas_height = self.original_canvas.winfo_height()
                    
                    if canvas_width > 1 and canvas_height > 1:  # Canvas is initialized
                        rect_id = self.original_canvas.create_rectangle(
                            10, 10, canvas_width - 10, 60, 
                            fill=bg_color, outline="", tags="notification")
                        text_id = self.original_canvas.create_text(
                            canvas_width // 2, 35, text=message, 
                            fill=text_color, font=('Arial', 11, 'bold'), tags="notification")
                        
                        # Remove notification after 3 seconds
                        self.root.after(3000, lambda: self.original_canvas.delete("notification"))
            except Exception:
                pass  # Fail silently if canvas notification doesn't work
    
    def generate_from_text(self):
        """Generate image from text prompt using OpenAI's DALL-E"""
        if not hasattr(self, 'text_entry'):
            messagebox.showerror("Error", "Text input not available")
            return
            
        # Get text from text widget
        text_prompt = self.text_entry.get("1.0", tk.END).strip()
        
        if not text_prompt:
            messagebox.showwarning("Input Required", "Please enter a description for the image you want to generate.")
            return
        
        # Confirm with user
        if not messagebox.askyesno("Generate Image", 
                                  f"Generate line art image from:\n\n'{text_prompt}'\n\nThis will use OpenAI API credits. Continue?"):
            return
        
        # Start generation in background thread
        self._start_text_generation_feedback()
        
        # Run in thread to avoid blocking UI
        import threading
        thread = threading.Thread(target=self._text_generation_thread, args=(text_prompt,))
        thread.daemon = True
        thread.start()
    
    def _text_generation_thread(self, text_prompt):
        """Background thread for text-to-image generation"""
        try:
            from convert_to_lineart import generate_image_from_text
            
            # Generate image
            result = generate_image_from_text(text_prompt, style="line_art")
            
            # Schedule UI update on main thread
            self.root.after(0, self._text_generation_success, result['output_path'])
            
        except Exception as e:
            # Schedule error handling on main thread
            self.root.after(0, self._text_generation_error, str(e))
    
    def _text_generation_success(self, output_path):
        """Handle successful text-to-image generation"""
        try:
            self._stop_text_generation_feedback()
            
            # Set the generated image as current image
            self.image_path.set(output_path)
            
            # Load preview
            self.load_preview_image()
            
            # Update status
            self.status_text.set("Image generated successfully! Processing for robot drawing...")
            
            # Show success notification
            self._show_conversion_notification("✅ Image generated successfully from your text prompt!", "success")
            
            # Enable processing buttons
            if hasattr(self, 'draw_btn') and self.draw_btn:
                if hasattr(self, 'draw_btn'): self.draw_btn.config(state='normal')
            if hasattr(self, 'face_drawing_btn') and self.face_drawing_btn:
                self.face_drawing_btn.config(state='normal')
            
            # Automatically process the generated image to create drawing paths
            self.root.after(1000, self._auto_process_generated_image)  # Small delay to ensure UI updates complete
                
        except Exception as e:
            self._text_generation_error(f"Error loading generated image: {e}")
    
    def _auto_process_generated_image(self):
        """Automatically process the generated image to create drawing paths"""
        try:
            self.status_text.set("Processing generated image for robot drawing...")
            # Trigger automatic image processing
            self.auto_process_image()
        except Exception as e:
            self.status_text.set("Generated image processing failed")
            messagebox.showerror("Processing Error", f"Failed to process generated image:\n\n{e}")
    
    def _text_generation_error(self, error):
        """Handle text-to-image generation error"""
        self._stop_text_generation_feedback()
        self.status_text.set("Text generation failed")
        messagebox.showerror("Generation Error", f"Failed to generate image from text:\n\n{error}")
    
    def _start_text_generation_feedback(self):
        """Start visual feedback for text generation"""
        self.status_text.set("Generating image from text...")
        
        # Disable generate button during processing
        if hasattr(self, 'text_section'):
            for child in self.text_section.winfo_children():
                if isinstance(child, tk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Button) and "Generate" in grandchild.cget('text'):
                            grandchild.config(state='disabled', text="🔄 Generating...")
    
    def _stop_text_generation_feedback(self):
        """Stop visual feedback for text generation"""
        # Re-enable generate button
        if hasattr(self, 'text_section'):
            for child in self.text_section.winfo_children():
                if isinstance(child, tk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, tk.Button) and ("Generating" in grandchild.cget('text') or "Generate" in grandchild.cget('text')):
                            grandchild.config(state='normal', text="🤖 Generate Image")
    
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
        
        # Show progress indicators
        self._start_conversion_feedback("Face Drawing")
        
        # Show temporary notification
        self._show_conversion_notification("Starting Face Drawing conversion...", "info")
        
        # Disable the button during processing and change appearance dramatically (only if it exists)
        if hasattr(self, 'face_drawing_btn'):
            self.face_drawing_btn.config(
                state='disabled', 
                text="⏳ Converting\nFace Drawing...", 
                bg='#9E9E9E', 
                fg='white',
                relief='sunken'
            )
        
        if hasattr(self, 'caricature_btn'):
            self.caricature_btn.config(state='disabled', bg='#BDBDBD')  # Make other button also visibly disabled
        
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
            # Stop progress animation
            self._stop_conversion_feedback()
            
            # Switch to load mode if not already
            self.drawing_mode.set("load")
            self.on_mode_change()
            
            # Update the image path to use the new line art
            self.image_path.set(output_path)
            try:
                if hasattr(self, 'file_label') and self.file_label and self.file_label.winfo_exists():
                    self.file_label.config(text="Face Line Art: out.png", fg='#333')
            except Exception:
                pass
            
            # Load preview of the line art
            self.load_preview_image()
            
            # Automatically process the line art
            self.status_text.set("Line art generated - processing for robot...")
            self.auto_process_image()
            
            # Re-enable buttons and restore appearance
            if hasattr(self, 'face_drawing_btn'):
                self.face_drawing_btn.config(
                    state='normal', 
                    text="👤 Face\nDrawing", 
                    bg=self.COLORS['start_drawing'], 
                    fg='white',
                    relief='flat'
                )
            if hasattr(self, 'caricature_btn'):
                self.caricature_btn.config(state='normal', bg=self.COLORS['portrait'])
            if hasattr(self, 'progress_indicator'):
                self.progress_indicator.config(text="✅ Line Art Ready")
            
            # Re-enable all buttons and restore triangle overlay
            self.enable_all_buttons()
            if hasattr(self, 'triangle_overlay'):
                self.draw_triangle_buttons_smart(self.triangle_overlay)
            
            # Show success notification
            self._show_conversion_notification("✅ Face Drawing conversion completed!", "success")
            
            # Line art conversion completed - image loaded in GUI, no popup needed
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load line art: {e}")
            self._face_drawing_failed()
    
    def _face_drawing_failed(self):
        """Handle face drawing conversion failure"""
        self._stop_conversion_feedback()
        if hasattr(self, 'face_drawing_btn'):
            self.face_drawing_btn.config(
                state='normal', 
                text="👤 Face\nDrawing", 
                bg=self.COLORS['start_drawing'], 
                fg='white',
                relief='flat'
            )
        if hasattr(self, 'caricature_btn'):
            self.caricature_btn.config(state='normal', bg=self.COLORS['portrait'])
        if hasattr(self, 'progress_indicator'):
            self.progress_indicator.config(text="❌ Failed")
        
        # Re-enable all buttons and restore triangle overlay
        self.enable_all_buttons()
        if hasattr(self, 'triangle_overlay'):
            self.draw_triangle_buttons_smart(self.triangle_overlay)
            
        self.status_text.set("Line art conversion failed")
        self._show_conversion_notification("❌ Face Drawing conversion failed!", "error")
        messagebox.showerror("Error", "Failed to generate line art. Check if out.png was created.")
    
    def _face_drawing_error(self, error):
        """Handle face drawing conversion error"""
        self._stop_conversion_feedback()
        if hasattr(self, 'face_drawing_btn'):
            self.face_drawing_btn.config(
                state='normal', 
                text="👤 Face\nDrawing", 
                bg=self.COLORS['start_drawing'], 
                fg='white',
                relief='flat'
            )
        if hasattr(self, 'caricature_btn'):
            self.caricature_btn.config(state='normal', bg=self.COLORS['portrait'])
        if hasattr(self, 'progress_indicator'):
            self.progress_indicator.config(text="❌ Error")
        
        # Re-enable all buttons and restore triangle overlay
        self.enable_all_buttons()
        if hasattr(self, 'triangle_overlay'):
            self.draw_triangle_buttons_smart(self.triangle_overlay)
            
        self.status_text.set("Line art conversion error")
        self._show_conversion_notification("❌ Face Drawing conversion error!", "error")
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
        
        # Show progress indicators
        self._start_conversion_feedback("Caricature")
        
        # Show temporary notification
        self._show_conversion_notification("Starting Caricature conversion...", "info")
        
        # Disable the button during processing and change appearance dramatically
        self.caricature_btn.config(
            state='disabled', 
            text="⏳ Converting\nCaricature...", 
            bg='#9E9E9E', 
            fg='white',
            relief='sunken'
        )
        self.face_drawing_btn.config(state='disabled', bg='#BDBDBD')  # Make other button also visibly disabled
        
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
            # Stop progress animation
            self._stop_conversion_feedback()
            
            # Switch to load mode if not already
            self.drawing_mode.set("load")
            self.on_mode_change()
            
            # Update the image path to use the new caricature
            self.image_path.set(output_path)
            try:
                if hasattr(self, 'file_label') and self.file_label and self.file_label.winfo_exists():
                    self.file_label.config(text="Caricature: out.png", fg='#333')
            except Exception:
                pass
            
            # Load preview of the caricature
            self.load_preview_image()
            
            # Automatically process the caricature
            self.status_text.set("Caricature generated - processing for robot...")
            self.auto_process_image()
            
            # Re-enable buttons and restore appearance
            if hasattr(self, 'caricature_btn'):
                self.caricature_btn.config(
                    state='normal', 
                    text="🎭 Caricature", 
                    bg=self.COLORS['portrait'], 
                    fg='white',
                    relief='flat'
                )
            if hasattr(self, 'face_drawing_btn'):
                self.face_drawing_btn.config(state='normal', bg=self.COLORS['start_drawing'])
            if hasattr(self, 'progress_indicator'):
                self.progress_indicator.config(text="✅ Caricature Ready")
            
            # Re-enable all buttons and restore triangle overlay
            self.enable_all_buttons()
            if hasattr(self, 'triangle_overlay'):
                self.draw_triangle_buttons_smart(self.triangle_overlay)
            
            # Show success notification
            self._show_conversion_notification("✅ Caricature conversion completed!", "success")
            
            # Caricature conversion completed - image loaded in GUI, no popup needed
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load caricature: {e}")
            self._caricature_failed()
    
    def _caricature_failed(self):
        """Handle caricature conversion failure"""
        self._stop_conversion_feedback()
        if hasattr(self, 'caricature_btn'):
            self.caricature_btn.config(
                state='normal', 
                text="🎭 Caricature", 
                bg=self.COLORS['portrait'], 
                fg='white',
                relief='flat'
            )
        if hasattr(self, 'face_drawing_btn'):
            self.face_drawing_btn.config(state='normal', bg=self.COLORS['start_drawing'])
        if hasattr(self, 'progress_indicator'):
            self.progress_indicator.config(text="❌ Failed")
        
        # Re-enable all buttons and restore triangle overlay
        self.enable_all_buttons()
        if hasattr(self, 'triangle_overlay'):
            self.draw_triangle_buttons_smart(self.triangle_overlay)
            
        self.status_text.set("Caricature conversion failed")
        self._show_conversion_notification("❌ Caricature conversion failed!", "error")
        messagebox.showerror("Error", "Failed to generate caricature. Check if out.png was created.")
    
    def _caricature_error(self, error):
        """Handle caricature conversion error"""
        self._stop_conversion_feedback()
        if hasattr(self, 'caricature_btn'):
            self.caricature_btn.config(
                state='normal', 
                text="🎭 Caricature", 
                bg=self.COLORS['portrait'], 
                fg='white',
                relief='flat'
            )
        if hasattr(self, 'face_drawing_btn'):
            self.face_drawing_btn.config(state='normal', bg=self.COLORS['start_drawing'])
        if hasattr(self, 'progress_indicator'):
            self.progress_indicator.config(text="❌ Error")
        
        # Re-enable all buttons and restore triangle overlay
        self.enable_all_buttons()
        if hasattr(self, 'triangle_overlay'):
            self.draw_triangle_buttons_smart(self.triangle_overlay)
            
        self.status_text.set("Caricature conversion error")
        self._show_conversion_notification("❌ Caricature conversion error!", "error")
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

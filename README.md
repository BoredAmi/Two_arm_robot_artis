# 🤖 Robot Drawing System

**AI-Powered Dual-Arm Robotic Artist**

Transform images into physical drawings using ABB YuMi industrial robots with AI assistance, voice control, and advanced image processing.

---

## 🚀 Quick Start

### For First-Time Users (2 minutes)
1. **Launch**: `python simple_gui.py`
2. **Connect**: Click "Connect Robot" (in advanced setup) or say "Połącz"→ Wait for green status
3. **Image**: Click "📷 TAKE PICTURE" or upload an image
4. **Style**: Choose "👤 Portrait" or "😄 Caricature"
5. **Draw**: Click "🤖 START DRAWING" → Monitor progress

### 🎤 Voice Commands (Polish)
- **"uchwyć"** - Take picture
- **"połącz"** - Connect robot  
- **"start"** - Start drawing
- **"stop"** -  Stop
- **"karykatura"** - convert to carycature 
- **"portret"** - covert to portrait

---

## ✨ Key Features

### 🎨 **Multiple Input Methods**
- **Camera Capture**: Direct from computers camera
- **File Upload**: JPG, PNG, BMP etc. support
- **Drawing Canvas**: Interactive brush tools
- **AI Generation**: Text-to-image with OpenAI

### 🤖 **Advanced Robotics**
- **Dual-Arm Operation**: Simultaneous drawing with collision avoidance
- **Smart Coordination**: Step-by-step task assignment
- **Safety Systems**: Stop and workspace bounds
- **Real-Time Control**: Live progress tracking

### 🧠 **AI Integration**
- **Image Processing**: 3 edge detection algorithms
- **Voice Recognition**: VOSK Polish speech recognition
- **Line Art Conversion**: AI-powered style transformation

### ⚡ **Performance**
- **Batch Processing**: Optimized communication (1-15 points)
- **Fast Drawing**: 0.5-8 minutes per artwork
- **Dual-Arm Advantage**: ~30% faster for complex images

---

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Simple GUI    │────│  Robot Drawer   │────│ Robot Controller│
│  (User Interface│    │  (Orchestrator) │    │ (TCP/IP Comm)  │
│     Layer)      │    │                 │    │                 │
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

## 📁 Project Structure

```
moje_skrypty/
├── 🎨 Main Application
│   ├── simple_gui.py              # Main GUI (EXPO mode)
│   └── robot_drawer.py            # Core orchestrator
│
├── 🤖 Robot Control  
│   ├── robot_communication.py     # TCP/IP communication
│   ├── Right_arm.mod             # RAPID code for right arm
│   └── Left_arm.mod              # RAPID code for left arm
│
├── 🖼️ Image Processing
│   ├── image_processor.py         # Edge detection & contours
│   ├── coordinate_transformer.py  # Coordinate transformation
│   └── visualizer.py             # Plotting and animation
│
├── 🔊 AI & External Services
│   ├── voice_commands.py          # Voice recognition (VOSK)
│   ├── convert_to_lineart.py      # OpenAI DALL-E integration
│   └── robot_ftp_downloader.py    # Local camera capture
│
├── 🎬 Animation & Helpers
│   ├── matplotlib_anim_helper.py      # Path-by-path animation
│   └── matplotlib_anim_point_helper.py # Point-by-point animation
│
├── 📊 Data & Configuration
│   ├── robot_gui_config.json      # Persistent settings
│   ├── image.png / out.png        # Sample/temp images
│   ├── logo_short.png             # Logo overlay
│   └── line_art_catalog/          # Generated artwork archive
│
├── 🤖 RAPID Robot Programs
│   ├── Right_arm.mod             # ABB RAPID for right arm
│   └── Left_arm.mod              # ABB RAPID for left arm
│
├── 🔊 Voice Model
│   └── vosk-model-small-pl-0.22/  # Polish speech recognition
│
└── 📚 Documentation
    ├── COMPREHENSIVE_DOCUMENTATION.md # Complete technical docs
    ├── PROJECT_SUMMARY.md            # Executive overview
    └── README.md                     # This file
```

---

## 💻 Requirements

### Hardware
- **Robot**: ABB YuMi IRB 14000 with IRC5 controller
- **Computer**: Windows 10/11
- **Network**: Ethernet to robot (192.168.125.1)
- **Optional**: Microphone, USB camera

### Software  
- **Python 3.8+** with standard libraries
- **Key Dependencies**: OpenCV, Matplotlib, PIL, Shapely
- **AI Services**: OpenAI API key (for text generation)
- **Voice Model**: VOSK Polish model 

---

## 🚀 Installation

### 1. Clone Repository
```bash
git clone [repository-url]
cd moje_skrypty
```

### 2. Install Dependencies
```bash
pip install opencv-python matplotlib pillow numpy shapely
pip install sounddevice vosk openai tkinter
```

### 3. Configure Robot
- Load RAPID modules: `Right_arm.mod`, `Left_arm.mod`
- Set robot IP: `192.168.125.1`
- Configure ports: 1025 (right), 1026 (left)

### 4. Run Application
```bash
python simple_gui.py
```

---

## 🎯 Usage Examples

### Basic Drawing
```python
from robot_drawer import RobotDrawer

# Initialize and connect
drawer = RobotDrawer(ip="192.168.125.1")
drawer.connect()

# Process image and draw
drawer.load_image("portrait.jpg", precision="high")
drawer.plot_preview()  # Preview before drawing
drawer.draw()  # Start drawing

drawer.disconnect()
```

### Dual-Arm Drawing
```python
# Enable dual-arm mode
drawer = RobotDrawer(port_l=1026)  # Enable left arm
drawer.connect()

# Process and draw with both arms
drawer.load_image("complex_artwork.png")
drawer.draw_dual(buffer_radius=50)  # Collision avoidance
```

### AI-Generated Art
```python
from convert_to_lineart import generate_image_from_text, convert_to_lineart

# Generate from text
image_path = generate_image_from_text("minimalist cat portrait")
line_art_path = convert_to_lineart(image_path, "minimalist")

# Draw with robot
drawer.load_image(line_art_path)
drawer.draw()
```

---

## ⚙️ Configuration

### Default Settings
```json
{
  "robot_ip": "192.168.125.1",
  "robot_port": "1025",
  "robot_port_l": "1026", 
  "max_x": 290,
  "max_y": 210,
  "quality_var": "high",
  "detection_method": "threshold",
  "dual_arm_mode": false,
  "use_batch_mode": true
}
```

### Key Parameters
- **Workspace**: 290mm × 210mm (A4 paper)
- **Margins**: 10mm default safety buffer
- **Quality**: "highest", "high", "medium", "low"
- **Detection**: "threshold", "canny", "adaptive"

---

## 🛡️ Safety

### Built-in Safety Features
- **Stop**: Software, voice, and hardware
- **Collision Avoidance**: Dual-arm coordination algorithms
- **Workspace Bounds**: Automatic coordinate validation
- **Error Recovery**: Graceful failure handling

### Safety Guidelines
- **Monitor Operation**: Never leave unattended
- **Clear Workspace**: 1-meter clearance around robot
- **Emergency Access**: Know emergency stop locations
- **Proper Training**: Only trained operators

---

## 🔧 Troubleshooting

### Common Issues

**Robot Won't Connect**
- Verify robot IP: `ping 192.168.125.1`
- Check RAPID modules are loaded and running
- Ensure network cables connected

**Poor Drawing Quality**
- Increase quality setting to "high" or "highest"
- Try different detection method ("adaptive" for photos)
- Improve image lighting and contrast

**Slow Performance**
- Enable batch mode for faster communication
- Use dual-arm mode for parallel processing
- Reduce precision for faster processing

---

## 📚 Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| **README.md** | Quick overview and setup | Everyone |
| **COMPREHENSIVE_DOCUMENTATION.md** | Complete technical reference | Developers, Engineers |
| **PROJECT_SUMMARY.md** | Executive overview | Management |


---

## 📊 Project Status

### ✅ Current Version: 1.0 - EXPO MODE
- **Release Date**: September 2025
- **Status**: Production Ready
- **Target**: Windows 10/11 with ABB YuMi robots

### Feature Completeness
- ✅ Core drawing functionality
- ✅ Dual-arm coordination
- ✅ AI integration
- ✅ Voice control
- ✅ Safety systems
- ✅ User interface
- ✅ Documentation

---

## 🎉 Acknowledgments

### Technologies Used
- **ABB YuMi IRB 14000**: Industrial robot platform
- **OpenAI DALL-E**: AI image generation
- **VOSK**: Open-source speech recognition
- **OpenCV**: Computer vision library
- **Python Ecosystem**: NumPy, Matplotlib, PIL, Shapely


---
**Robot Drawing System** 
*Transforming digital creativity into physical art through advanced automation*


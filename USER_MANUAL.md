# 🤖 Robot Drawing System - User Manual
**Step-by-Step Operating Instructions**

---

## 📖 Table of Contents
1. [Quick Start Guide](#quick-start-guide)
2. [System Requirements](#system-requirements)
3. [Installation Instructions](#installation-instructions)
4. [Basic Operation](#basic-operation)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)
7. [Safety Guidelines](#safety-guidelines)

---

## 🚀 Quick Start Guide

### For First-Time Users (5 Minutes)

1. **Launch the Application**
   ```
   Double-click: launcher.py
   ```

2. **Main Interface Overview**
   ```
   ┌─────────────────────────────────────┐
   │  [📷 TAKE PICTURE] [🖼️ SEE PHOTO]   │
   │  [🎨 STYLE SELECT] [🤖 START DRAW]  │
   └─────────────────────────────────────┘
   ```

3. **Basic Workflow**
   - Click **"📷 TAKE PICTURE"** to capture an image
   - Choose drawing style: **👤 Portrait** or **😄 Caricature**
   - Click **"🔗 CONNECT ROBOT"** (appears at bottom)
   - Click **"🤖 START DRAWING"** to begin

### Voice Commands (Polish)
Say these commands aloud while the application is running:
- **"uchwyć"** - Take a picture
- **"połącz"** - Connect to robot
- **"portret"** - Switch to portrait mode
- **"karykatura"** - Switch to caricature mode
- **"start"** - Begin drawing
- **"stop"** - Emergency stop

---

## 💻 System Requirements

### Minimum Requirements
- **OS**: Windows 10 (64-bit)
- **RAM**: 4 GB
- **Storage**: 2 GB free space
- **Network**: Ethernet connection
- **Python**: 3.8 or higher

### Recommended Requirements
- **OS**: Windows 11 (64-bit)
- **RAM**: 8 GB
- **Storage**: 5 GB free space
- **Network**: Gigabit Ethernet
- **Audio**: Microphone (for voice commands)

### Robot Requirements
- **Robot**: ABB YuMi IRB 14000
- **Controller**: IRC5 with Robot Studio
- **Network**: TCP/IP connection
- **Default IP**: 192.168.125.1
- **Ports**: 1025 (Right arm), 1026 (Left arm)

---

## 📥 Installation Instructions

### Option 1: Quick Setup (Recommended)
1. Download the complete package
2. Extract to desired folder
3. Double-click `launcher.py`
4. System will auto-install missing components

### Option 2: Manual Installation
1. Install Python 3.8+
2. Install required packages:
   ```bash
   pip install opencv-python pillow numpy matplotlib tkinter
   pip install shapely vosk sounddevice
   ```
3. Download VOSK Polish model (if using voice commands)
4. Launch `simple_gui.py`

### Network Configuration
1. Connect computer to robot network
2. Verify robot IP: Default `192.168.125.1`
3. Test connection: `ping 192.168.125.1`

---

## 🎯 Basic Operation

### 1. Starting the System

**Step 1: Launch Application**
- Double-click `launcher.py` or `simple_gui.py`
- Wait for main window to appear (2x2 grid layout)

**Step 2: Verify Settings**
- Click **"⚙️ Advanced Setup"** for configuration
- Check robot IP address (default: 192.168.125.1)
- Verify drawing area (default: 290mm × 210mm A4)

### 2. Image Input Methods

#### Method A: Camera Capture (Recommended)
1. Click **"📷 TAKE PICTURE"**
2. System captures image from robot's camera
3. Image appears in preview area
4. Proceed to style selection

#### Method B: File Upload
1. Click **"⚙️ Advanced Setup"**
2. Go to **"Input Methods"** tab
3. Click **"📁 Browse Images"**
4. Select JPG, PNG, or BMP file
5. Return to main interface

#### Method C: Create Drawing
1. Click **"⚙️ Advanced Setup"**
2. Go to **"Input Methods"** tab
3. Click **"🎨 Open Drawing Canvas"**
4. Draw with mouse using brush tool
5. Click **"✅ Use Drawing"**

#### Method D: AI Generation
1. Click **"⚙️ Advanced Setup"**
2. Go to **"Input Methods"** tab
3. Enter description: "Simple house with door and windows"
4. Click **"🤖 Generate Image from Text"**

### 3. Style Selection

Once image is loaded, choose drawing style:

#### 👤 Portrait Mode
- **Best for**: Faces, people, portraits
- **Effect**: Natural lines, enhanced facial features
- **Quality**: High detail preservation
- **Time**: Standard processing

#### 😄 Caricature Mode  
- **Best for**: Fun drawings, exaggerated features
- **Effect**: Bold lines, enhanced contrasts
- **Quality**: Stylized output
- **Time**: Fast processing

#### 📄 Normal Mode
- **Best for**: Documents, technical drawings
- **Effect**: Clean lines, accurate reproduction
- **Quality**: Precise detail
- **Time**: Variable based on complexity

### 4. Robot Connection

**Step 1: Connect**
1. Ensure robot is powered on and ready
2. Verify network connection
3. Click **"🔗 CONNECT ROBOT"** button
4. Wait for green status: **"🟢 Robot: Connected"**

**Step 2: Test Connection**
- Status shows robot IP and port
- Green indicator confirms successful connection
- If connection fails, check network settings

### 5. Start Drawing

**Final Step: Execute Drawing**
1. Verify image is processed (preview visible)
2. Confirm robot is connected (green status)
3. Click **"🤖 START DRAWING"**
4. Monitor progress bar and status messages
5. Use **"⏹ EMERGENCY STOP"** if needed

---

## 🔧 Advanced Features

### Drawing Quality Settings

Access via **"⚙️ Advanced Setup"** → **"Image Processing"**

#### Quality Levels
- **Standard**: Fast processing, good results
- **High**: Balanced quality and speed (recommended)
- **Ultra**: Maximum detail, slower processing

#### Edge Detection Methods
- **Threshold**: Best for high-contrast images (recommended)
- **Adaptive**: Best for photos with varying lighting
- **Canny**: Best for detailed technical drawings

### Coordinate Systems

Access via **"⚙️ Advanced Setup"** → **"Drawing Settings"**

#### Corner Origin (Default)
- Origin (0,0) at top-left of workspace
- Familiar to most users
- Matches image coordinate system

#### Center Origin
- Origin (0,0) at center of workspace
- Better for symmetric drawings
- Professional robotics standard

### Dual-Arm Mode

Access via **"⚙️ Advanced Setup"** → **"Robot Connection"**

#### Enabling Dual-Arm Drawing
1. Check **"Enable dual-arm drawing mode"**
2. Verify both robot ports are configured
3. Set forbidden buffer radius (default: 40mm)
4. Both arms will work simultaneously with collision avoidance

#### Benefits
- **50% faster** drawing for complex images
- Automatic task splitting between arms
- Built-in collision avoidance
- Synchronized operation

### Workspace Configuration

Access via **"⚙️ Advanced Setup"** → **"Drawing Settings"**

#### Drawing Area
- **A4**: 290mm × 210mm (default)
- **A5**: 210mm × 148mm
- **Custom**: Set your own dimensions

#### Safety Margins
- **Purpose**: Prevents drawing at workspace edges
- **Horizontal**: 0-50mm safety border
- **Vertical**: 0-50mm safety border
- **Recommended**: 10mm for general use

### Path Optimization

#### TSP (Traveling Salesman Problem)
- **Enable**: Checkbox in drawing settings
- **Purpose**: Minimizes pen travel time
- **Result**: 40-60% faster drawing
- **Recommendation**: Keep enabled for most drawings

#### Batch Mode
- **Individual**: One command per point (precise, slower)
- **Batch**: Multiple points per command (fast, efficient)
- **Ultra-Fast**: Optimized batching (fastest)

---

## 🎨 Working with Different Image Types

### Photographs
**Recommended Settings:**
- Quality: High
- Detection: Adaptive
- Style: Portrait or Caricature
- TSP: Enabled

**Tips:**
- Use good lighting for best results
- Avoid cluttered backgrounds
- Portrait mode works best for faces

### Line Art / Sketches
**Recommended Settings:**
- Quality: Ultra
- Detection: Threshold
- Style: Normal
- TSP: Enabled

**Tips:**
- Ensure clean, high-contrast lines
- Avoid very thin lines (may not be detected)
- Scan at high resolution if possible

### Technical Drawings
**Recommended Settings:**
- Quality: Ultra
- Detection: Canny
- Style: Normal
- TSP: Disabled (preserve original order)

**Tips:**
- Use high-resolution images
- Ensure drawings are clean and precise
- Consider manual drawing mode for CAD-like precision

### Handwritten Text
**Recommended Settings:**
- Quality: High
- Detection: Adaptive
- Style: Normal
- TSP: Disabled

**Tips:**
- Use dark ink on white paper
- Ensure letters are clearly separated
- Larger text works better

---

## 🔍 Troubleshooting

### Connection Issues

#### Problem: "Cannot connect to robot"
**Solutions:**
1. Check robot is powered on
2. Verify IP address: `ping 192.168.125.1`
3. Check network cable connections
4. Try different IP if robot configuration changed
5. Restart robot controller if necessary

#### Problem: "Connection lost during drawing"
**Solutions:**
1. Check network stability
2. Ensure no firewall blocking
3. Use emergency stop, then reconnect
4. Check for loose network cables

### Image Processing Issues

#### Problem: "No edges detected in image"
**Solutions:**
1. Try different detection method (Adaptive)
2. Increase image contrast
3. Use higher quality setting
4. Check image is not too dark/light

#### Problem: "Too many edges detected"
**Solutions:**
1. Use lower quality setting
2. Try Threshold detection method
3. Reduce image noise/artifacts
4. Use simpler image

### Drawing Quality Issues

#### Problem: "Drawing looks choppy/angular"
**Solutions:**
1. Increase quality setting to High/Ultra
2. Use smaller precision factors
3. Enable smoothing in advanced settings
4. Check robot is properly calibrated

#### Problem: "Drawing is too small/large"
**Solutions:**
1. Check drawing area settings (A4 vs A5)
2. Verify workspace dimensions match robot
3. Adjust margins if drawing is cut off
4. Check coordinate system (corner vs center)

### Performance Issues

#### Problem: "Processing is very slow"
**Solutions:**
1. Reduce quality setting to Medium/Standard
2. Use smaller images (reduce resolution)
3. Enable batch mode for faster drawing
4. Close other applications

#### Problem: "Robot moves very slowly"
**Solutions:**
1. Enable batch mode
2. Reduce move delay in advanced settings
3. Check robot speed settings
4. Use TSP optimization

### Voice Command Issues

#### Problem: "Voice commands not recognized"
**Solutions:**
1. Check microphone is connected
2. Speak clearly in Polish
3. Reduce background noise
4. Check VOSK model is installed
5. Use exact command words

### Emergency Situations

#### Problem: Robot collision or dangerous movement
**Action:**
1. **Immediately** click **"⏹ EMERGENCY STOP"**
2. Or say **"stop"** (voice command)
3. Power off robot if necessary
4. Check workspace for obstructions
5. Restart system after clearing issue

#### Problem: Software crash or freeze
**Action:**
1. Use **Ctrl+C** in command window
2. Force close application if necessary
3. Power cycle robot controller
4. Restart application
5. Check error logs

---

## 🛡️ Safety Guidelines

### Pre-Operation Safety

#### Robot Workspace
- **Clear Area**: Ensure 1-meter clearance around robot
- **Emergency Stop**: Know location of robot emergency stop button
- **Protective Equipment**: Safety glasses recommended
- **Authorized Personnel**: Only trained operators

#### System Checks
- Verify robot calibration is current
- Check all network connections
- Test emergency stop function
- Ensure drawing surface is secure

### During Operation Safety

#### Monitoring
- **Never leave unattended** during drawing
- Monitor robot movements continuously
- Watch for unusual sounds or movements
- Keep emergency stop easily accessible

#### Workspace Safety
- **No human intervention** while robot is active
- Keep hands away from robot workspace
- Do not place objects in drawing area
- Ensure good lighting for operator visibility

### Post-Operation Safety

#### Shutdown Procedure
1. Complete current drawing operation
2. Use normal stop (not emergency)
3. Disconnect software safely
4. Power down robot controller
5. Secure workspace

#### Maintenance
- Regular calibration checks
- Clean drawing tools after use
- Inspect cables and connections
- Log any unusual behavior

### Emergency Procedures

#### Software Emergency Stop
1. Click **"⏹ EMERGENCY STOP"** button
2. Wait for robot to stop completely
3. Check for any issues
4. Reset system before continuing

#### Hardware Emergency Stop
1. Press robot's physical emergency stop button
2. Wait for complete shutdown
3. Investigate cause before reset
4. Follow robot manufacturer's reset procedure

#### Communication Loss
1. Use emergency stop if robot continues moving
2. Check network connections
3. Power cycle robot if necessary
4. Restart software connection

---

## 📞 Support and Maintenance

### Regular Maintenance Tasks

#### Daily
- Check robot workspace is clear
- Verify network connections
- Test emergency stop function

#### Weekly
- Clean drawing tools
- Check software for updates
- Verify robot calibration

#### Monthly
- Review error logs
- Check network equipment
- Update configuration backups

### Getting Help

#### Software Issues
1. Check this manual first
2. Review error messages in application
3. Check log files for detailed errors
4. Document exact steps to reproduce issue

#### Robot Issues
1. Check robot status indicators
2. Review robot controller logs
3. Verify robot calibration
4. Contact robot manufacturer if hardware issue

#### Contact Information
- **Software Support**: [Your contact information]
- **Robot Support**: ABB Robotics support
- **Network Support**: IT department

---

## 📚 Appendices

### A. Default Configuration Values
```json
{
  "robot_ip": "192.168.125.1",
  "robot_port": "1025",
  "robot_port_l": "1026",
  "max_x": 290,
  "max_y": 210,
  "margin_x": 10,
  "margin_y": 10,
  "quality_var": "high",
  "detection_method": "threshold",
  "enable_tsp": true,
  "use_batch_mode": true,
  "dual_arm_mode": false,
  "forbidden_buffer": 40
}
```

### B. Supported File Formats
- **Images**: JPG, JPEG, PNG, BMP, TIFF
- **Maximum Size**: 10MB per image
- **Recommended Resolution**: 1024x768 to 2048x1536
- **Color Support**: Grayscale and color (converted to grayscale)

### C. Performance Specifications
- **Processing Time**: 2-5 seconds per image
- **Drawing Speed**: 40-60mm/s typical
- **Positioning Accuracy**: ±0.1mm
- **Maximum Workspace**: 500mm × 400mm
- **Minimum Feature Size**: 2mm

### D. Voice Commands Reference
| Polish Command | English Meaning | Function |
|---------------|----------------|----------|
| "uchwyć" | Capture | Take picture from robot camera |
| "połącz" | Connect | Connect/disconnect robot |
| "start" | Start | Begin drawing process |
| "stop" | Stop | Emergency stop |
| "portret" | Portrait | Switch to portrait mode |
| "karykatura" | Caricature | Switch to caricature mode |
| "podgląd" | Preview | Show drawing preview |

---

*User Manual Version 1.0*  
*Last Updated: September 2024*  
*For Robot Drawing System v1.0*

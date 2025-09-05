# 🚀 Robot Drawing System - Quick Reference Guide
**Essential Information at a Glance**

---

## ⚡ Quick Start (60 Seconds)

1. **Launch**: Double-click `launcher.py`
2. **Connect**: Click **"🔗 CONNECT ROBOT"** → Wait for green status
3. **Image**: Click **"📷 TAKE PICTURE"** → Image appears in preview
4. **Style**: Click **👤 Portrait** or **😄 Caricature** 
5. **Draw**: Click **"🤖 START DRAWING"** → Monitor progress
6. **Emergency**: Click **"⏹ STOP"** if needed

---

## 🎤 Voice Commands (Polish)

| Say This | System Does |
|----------|-------------|
| **"uchwyć"** | 📷 Take picture |
| **"połącz"** | 🔗 Connect robot |
| **"start"** | 🤖 Start drawing |
| **"stop"** | ⏹ Emergency stop |
| **"portret"** | 👤 Portrait mode |
| **"karykatura"** | 😄 Caricature mode |

---

## 🎛️ Interface Layout

```
┌─────────────────────────────────────────────────────┐
│  Robot Drawing System - EXPO MODE                  │
├─────────────────┬───────────────────────────────────┤
│ 1. TAKE PICTURE │ 2. SEE YOUR PHOTO                │
│     📷          │     🖼️ Preview Area              │
│ Click to capture│     Shows captured image         │
├─────────────────┼───────────────────────────────────┤
│ 3. STYLE SELECT │ 4. START DRAWING                 │
│ 👤 Portrait     │     🤖                           │
│ 😄 Caricature   │ Begin robot art!                │
└─────────────────┴───────────────────────────────────┘
│ 🟢 Robot: Connected    Ready to start! ⚙️ Setup │
└─────────────────────────────────────────────────────┘
```

---

## 🔧 Essential Settings

### Basic Configuration
- **Robot IP**: `192.168.125.1` (default)
- **Drawing Area**: `290mm × 210mm` (A4)
- **Quality**: `High` (recommended)
- **Detection**: `Threshold` (recommended)

### Quick Adjustments
- **Faster Drawing**: Enable "Batch mode"
- **Better Quality**: Set quality to "Ultra" 
- **Dual Arms**: Check "Dual-arm drawing mode"
- **Safety**: Increase margins to 15mm

---

## 🚨 Troubleshooting Quick Fixes

### ❌ Robot Won't Connect
1. Check robot is powered on
2. Verify cable: `ping 192.168.125.1`
3. Try IP: `192.168.0.100` (alternative)

### ❌ No Image Captured  
1. Check robot camera is working
2. Ensure good lighting
3. Try manual file upload instead

### ❌ Poor Drawing Quality
1. Increase quality to "Ultra"
2. Try "Adaptive" detection method
3. Use better lighting for photos

### ❌ Drawing Too Slow
1. Enable "Batch mode"
2. Reduce quality to "Standard"
3. Enable "TSP optimization"

### ❌ Emergency Situations
1. **Click "⏹ EMERGENCY STOP"** immediately
2. Or say **"stop"** (voice command)
3. Check workspace for obstructions

---

## 📊 Performance Tips

### For Speed
- ✅ Enable batch mode
- ✅ Use "Standard" quality
- ✅ Enable TSP optimization
- ✅ Use dual-arm mode
- ✅ Reduce image resolution

### For Quality  
- ✅ Use "Ultra" quality
- ✅ Try "Adaptive" detection
- ✅ Use individual move mode
- ✅ Increase drawing area margins
- ✅ Use high-resolution images

---

## 🎯 Best Image Types

### ✅ Works Great
- **Portraits**: Clear faces, good lighting
- **Line Art**: Black lines on white background
- **Sketches**: High contrast drawings
- **Text**: Large, clear handwriting

### ⚠️ May Need Adjustment
- **Photos**: Use Portrait/Caricature mode
- **Complex Images**: Reduce quality setting
- **Dark Images**: Increase contrast first
- **Small Details**: Use Ultra quality

---

## 📐 Workspace Setup

### Standard Setup (A4)
```
┌─────────────────────────────────────┐
│ ←────── 290mm (max_x) ──────→       │
│ ┌─────────────────────────────────┐ ↑
│ │                                 │ │
│ │     Safe Drawing Area           │ │ 210mm
│ │   (with 10mm margins)           │ │ (max_y)
│ │                                 │ │
│ └─────────────────────────────────┘ ↓
└─────────────────────────────────────┘
    Robot Workspace Boundary
```

### Dual-Arm Setup
```
LEFT ARM ←→ FORBIDDEN ZONE ←→ RIGHT ARM
   🦾              🚫              🦾
                Buffer: 40mm
```

---

## 🔄 Common Workflows

### Photo Portrait
1. **"📷 TAKE PICTURE"** → Good lighting, clear face
2. **👤 Portrait** → Enhanced facial features  
3. **🔗 CONNECT** → Verify green status
4. **🤖 START** → 3-5 minute drawing

### Quick Sketch
1. **⚙️ Setup** → **Browse Images** → Upload sketch
2. **📄 Normal** → Clean line reproduction
3. **Quality: Ultra** → Maximum detail
4. **🤖 START** → 2-8 minutes depending on complexity

### Fun Caricature
1. **"📷 TAKE PICTURE"** → Expressive face
2. **😄 Caricature** → Exaggerated features
3. **Dual-arm: ON** → Faster drawing
4. **🤖 START** → 2-4 minute fun drawing

---

## 📱 Status Indicators

### Connection Status
- 🟢 **Green**: Connected and ready
- 🔴 **Red**: Not connected
- 🟡 **Yellow**: Connecting...

### Progress Indicators
- **Processing image...** → Computer working
- **Sending START command...** → Robot initializing
- **Drawing contour X/Y** → Robot drawing
- **Drawing completed!** → Finished successfully

### Error Messages
- **"No image selected"** → Load image first
- **"Robot not connected"** → Connect robot first
- **"Communication error"** → Check network
- **"No edges detected"** → Try different detection method

---

## 🛡️ Safety Reminders

### Before Starting
- ✅ Clear 1-meter area around robot
- ✅ Know emergency stop location
- ✅ Ensure drawing surface is secure
- ✅ Check robot is properly calibrated

### During Operation
- 👁️ **Never leave unattended**
- 🚫 **Keep hands away from workspace**
- 👂 **Listen for unusual sounds**
- 🚨 **Emergency stop if anything unusual**

### Emergency Actions
1. **Software**: Click **"⏹ EMERGENCY STOP"**
2. **Voice**: Say **"stop"** loudly
3. **Hardware**: Press robot's red emergency button
4. **Power**: Turn off robot controller if necessary

---

## 📞 Quick Support

### Check First
1. **Error Message**: Note exact wording
2. **Robot Status**: Green/red indicators
3. **Network**: Can you ping robot IP?
4. **Recent Changes**: Any new settings?

### Common Solutions
- **Restart Application**: Close and reopen
- **Reconnect Robot**: Disconnect and connect
- **Restart Robot**: Power cycle controller
- **Check Cables**: Network and power connections

---

## 🎯 Pro Tips

### Efficiency
- 💡 Use voice commands for hands-free operation
- 💡 Save good settings in config file
- 💡 Process multiple images in sequence
- 💡 Use templates for testing

### Quality
- 💡 Good lighting = better results
- 💡 High contrast images work best  
- 💡 Clean backgrounds improve processing
- 💡 A4 size gives optimal detail

### Troubleshooting
- 💡 Try different detection methods
- 💡 Adjust quality based on image complexity
- 💡 Use margins to prevent edge clipping
- 💡 Emergency stop is always safe to use

---

*Quick Reference v1.0 - Keep this handy!*  
*For detailed information, see USER_MANUAL.md*

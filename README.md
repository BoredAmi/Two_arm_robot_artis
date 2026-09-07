# Robot Drawing System

A Python system for turning images (loaded, sketched, or AI-generated) into pen drawings executed by an ABB industrial robot (tested on an ABB YuMi dual-arm robot). It converts an image into optimized drawing paths, sends them to the robot controller over TCP/IP, and can drive one or two arms at once.

A full user manual (setup, GUI walkthrough, RobotStudio/RAPID configuration, troubleshooting) is available in [Drawing_robot_Yumi_manual.pdf](Drawing_robot_Yumi_manual.pdf).

## Features

- **GUI** ([simple_gui.py](simple_gui.py)) — load an image, sketch on a canvas, capture from a webcam, or generate one from a text prompt via OpenAI, then preview and send it to the robot.
- **Image processing** ([image_processor.py](image_processor.py)) — Canny edge detection, contour extraction/simplification, and optional TSP path-order optimization so the robot draws efficiently.
- **AI line-art generation** ([convert_to_lineart.py](convert_to_lineart.py)) — turns a photo into a minimalist or caricature line-art portrait using the OpenAI API.
- **Coordinate transformation** ([coordinate_transformer.py](coordinate_transformer.py)) — maps image-space contours to robot workspace coordinates, with collision/forbidden-zone handling for dual-arm setups.
- **Robot communication** ([robot_communication.py](robot_communication.py)) — TCP/IP client for ABB robot controllers, plus the corresponding RAPID modules ([Left_arm.mod](Left_arm.mod), [Right_arm.mod](Right_arm.mod)) that run on the controller.
- **Voice commands** ([voice_commands.py](voice_commands.py)) — optional hands-free control using [Vosk](https://alphacephei.com/vosk/) offline speech recognition (Polish model by default).
- **Preview/animation** ([visualizer.py](visualizer.py), [matplotlib_anim_helper.py](matplotlib_anim_helper.py), [matplotlib_anim_point_helper.py](matplotlib_anim_point_helper.py)) — matplotlib-based preview of paths before/while drawing.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your own OpenAI API key (only needed for the AI image generation / line-art features):
   ```
   OPENAI_API_KEY=sk-...
   ```
3. (Optional, for voice commands) Download a [Vosk](https://alphacephei.com/vosk/models) speech model — the code defaults to `vosk-model-small-pl-0.22` — and place the extracted folder in the project root.
4. Set your robot controller's IP/port in the GUI settings or in `robot_gui_config.json` (defaults to the standard ABB service port `192.168.125.1`).

## Running

```
python simple_gui.py
```

To build a standalone Windows executable:
```
pip install pyinstaller
pyinstaller RobotDrawingSystem.spec
```

## Robot-side setup

Load [Left_arm.mod](Left_arm.mod) and [Right_arm.mod](Right_arm.mod) into the corresponding RAPID tasks on the ABB controller — they implement the socket server that receives drawing commands from this Python client. See the manual PDF for full RobotStudio configuration steps.

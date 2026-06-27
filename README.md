# 🤖 Tracking_Bot: AI-Powered Vision & Hardware Control System
#Overview
Tracking_Bot demonstrates a robust software-to-hardware pipeline bridging Python applications with an Arduino UNO. By utilizing pyfirmata2, the system establishes a seamless serial connection to control physical actuators (servos/buzzers) using standard Python scripts.

Instead of writing low-level C++ for the microcontroller, the Arduino simply runs the StandardFirmata protocol. This shifts the entire processing load including complex computer vision, multi-threading, voice recognition, and AI logic onto the computer, treating the Arduino purely as a physical API endpoint.

🛠️ The Architecture: 4 Major Modules
This repository is structured around four major code iterations, scaling from basic state management to a fully integrated multi-modal AI assistant:

1. The Hardware Interface (button_c.py)
The foundational script. It establishes the serial connection and handles asynchronous hardware inputs. It demonstrates software-side debouncing, state management, and basic PWM servo control via callback functions without blocking the main thread.

2. Face Tracking System (facetracking.py)
Integrates OpenCV and cvzone for real time face detection.

Logic: Calculates the bounding box center, compares it against the camera's center to determine the X/Y error margin, and applies a smoothing algorithm (interpolation) to dynamically drive the pan tilt servos. Includes a visual UI and buzzer based "target lock" feedback.

3. Hand Gesture Tracking (hand_gesture.py)
Upgrades the vision pipeline using Google's MediaPipe.

Logic: Extracts complex hand-landmark data, specifically isolating the palm coordinates to direct the camera. This highlights the system's ability to parse complex neural-network data (21 3D landmarks) into simple, real-time hardware actuation.

4. J.A.R.V.I.S. Multi-Modal Assistant (jarvis.py)
The flagship integration. This script combines all previous modules into a single, multi-threaded application with offline AI processing:

Computer Vision: Dynamically switches between Face Tracking and Hand Tracking states.

Offline Voice Recognition: Utilizes the Vosk library running on a dedicated audio thread to capture and parse voice commands continuously without interrupting the video feed.

Local LLM Integration: Connects to a local Ollama server (TinyLlama/Qwen) via REST API to generate conversational responses based on voice triggers.

TTS: Uses pyttsx3 for audio feedback, creating a fully interactive loop. 


# ⚙️ Setup
To run this project, you must first flash your Arduino UNO with the StandardFirmata protocol:

Open the Arduino IDE.

Go to File > Examples > Firmata > StandardFirmata.

Upload to your Arduino UNO.

On your IDE (Vs code Pycham etc..) Open terminal 
enter .

**pip install pyfirmata2 opencv-python numpy cvzone mediapipe requests sounddevice pyttsx3 vosk**

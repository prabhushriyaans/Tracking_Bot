# ==========================================
# JARVIS MULTI-TRACKING + QWEN + VOSK
# ==========================================
import cv2
import mediapipe as mp
import numpy as np
import time
import threading
import queue
import json
import requests
import sounddevice as sd
import pyttsx3
import os

from vosk import Model, KaldiRecognizer
from pyfirmata2 import Arduino

# ==========================================
# SETTINGS
# ==========================================

PORT = "COM4"

CAM_W = 1280
CAM_H = 720

SERVO_X_PIN = 9
SERVO_Y_PIN = 8
BUZZER_PIN = 11

SMOOTHING = 0.12
DEADZONE = 25

VOSK_MODEL = "vosk-model-en-in-0.5"

# ==========================================
# MEMORY & STATES
# ==========================================

MEMORY_FILE = "memory.json"

if os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
else:
    memory = {}

def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

ai_state = "hands"  
manual_target_x = 90
manual_target_y = 90

# ==========================================
# TTS
# ==========================================

tts = pyttsx3.init()

def speak(text):
    print("Jarvis:", text)
    try:
        tts.say(text)
        tts.runAndWait()
    except:
        pass

# ==========================================
# LLM (OLLAMA / QWEN)
# ==========================================

def ask_tinyllama(prompt):
    try:
        print("Sending request to Ollama...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "tinyllama:latest",
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        print("Ollama response received")
        return response.json()["response"]
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# ARDUINO
# ==========================================

print("Connecting Arduino...")

board = Arduino(PORT)

servoX = board.get_pin(f'd:{SERVO_X_PIN}:s')
servoY = board.get_pin(f'd:{SERVO_Y_PIN}:s')
buzzer = board.get_pin(f'd:{BUZZER_PIN}:o')

currentX = 90
currentY = 90

servoX.write(currentX)
servoY.write(currentY)

# ==========================================
# CAMERA
# ==========================================

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

centerX = CAM_W // 2
centerY = CAM_H // 2

# ==========================================
# MEDIAPIPE (HANDS & FACE)
# ==========================================

mpHands = mp.solutions.hands
hands = mpHands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mpFaceDetection = mp.solutions.face_detection
face_detection = mpFaceDetection.FaceDetection(
    min_detection_confidence=0.6
)

mpDraw = mp.solutions.drawing_utils

# ==========================================
# VOSK
# ==========================================

audio_queue = queue.Queue()
model = Model(VOSK_MODEL)
recognizer = KaldiRecognizer(model, 16000)

# ==========================================
# GLOBALS
# ==========================================

tracking_enabled = True
jarvis_running = True
last_seen_text = "Nothing"

# ==========================================
# AUDIO CALLBACK
# ==========================================

def audio_callback(indata, frames, time_info, status):
    audio_queue.put(bytes(indata))

# ==========================================
# VOICE THREAD
# ==========================================

def voice_thread():
    global tracking_enabled
    global currentX, currentY
    global ai_state, manual_target_x, manual_target_y

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=audio_callback
    ):
        print("Voice Assistant Ready")

        while jarvis_running:
            data = audio_queue.get()

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()

                if text == "":
                    continue

                print("Recognized:", text)
                print("You:", text)

                memory["last_command"] = text
                save_memory()

                # --- TRACKING MODE SWITCHES ---
                if any(word in text for word in ["hands on", "track hands","hand"]):
                    ai_state = "hands"
                    speak("Switching to hand tracking.")
                    continue
                elif "get back" in text or "face on" in text or "track face" in text or "back" in text or "get" in text:
                    ai_state = "face"
                    speak("Returning to normal face tracking.")
                    continue

                # --- MANUAL DIRECTIONAL COMMANDS ---
                elif "look up" in text:
                    ai_state = "manual"
                    manual_target_y = 180 
                    speak("Looking up")
                    continue
                elif "look down" in text:
                    ai_state = "manual"
                    manual_target_y = 0    
                    speak("Looking down")
                    continue
                elif any(word in text for word in ["look left", "look less", "loop less", "luke left"]):
                    ai_state = "manual"
                    manual_target_x = 180  
                    speak("Looking left")
                    continue
                elif any(word in text for word in ["look right", "look bright", "luke ride", "luke right", "noob right"]):
                    ai_state = "manual"
                    manual_target_x = 0    
                    speak("Looking right")
                    continue

                # --- SYSTEM COMMANDS ---
                elif "enable tracking" in text:
                    tracking_enabled = True
                    speak("Tracking enabled")
                    continue
                elif "disable tracking" in text:
                    tracking_enabled = False
                    speak("Tracking disabled")
                    continue
                elif "center servos" in text:
                    ai_state = "manual"
                    manual_target_x = 90
                    manual_target_y = 90
                    speak("Servos centered")
                    continue
                elif "what do you see" in text:
                    speak(f"I currently see {last_seen_text}")
                    continue

                # --- WAKE WORD & LLM TRIGGER ---
                elif any(w in text for w in ["jarvis", "gervais", "jervis", "ai"]):
                    
                    if ai_state != "face":
                        ai_state = "face"
                        speak("I am paying attention.")

                    # Simplified, rigid prompt to stop hallucinated rules
                    prompt = f"Respond strictly as Jarvis, a robotic AI assistant. Reply in exactly one concise sentence. No emojis. User: {text}\nJarvis:"
                    
                    print("Calling Qwen...")
                    reply = ask_tinyllama(prompt)
                    
                    # Clean up any leftover labels from the LLM
                    reply = reply.replace("Jarvis:", "").strip()
                    
                    print("Qwen replied:")
                    print(reply)
                    speak(reply)

# ==========================================
# START VOICE THREAD
# ==========================================

threading.Thread(target=voice_thread, daemon=True).start()

# ==========================================
# MAIN LOOP
# ==========================================

print("Jarvis Multi-Tracking System Ready. Press ESC or Ctrl+C to exit.")

try:
    while True:
        success, img = cap.read()
        
        # Safety check to prevent mediapipe crash on dropped frames
        if not success or img is None or img.size == 0:
            continue

        img = cv2.flip(img, 1)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        hand_results = hands.process(rgb)
        face_results = face_detection.process(rgb)

        cv2.line(img, (centerX, 0), (centerX, CAM_H), (0,255,0), 1)
        cv2.line(img, (0, centerY), (CAM_W, centerY), (0,255,0), 1)

        target_px = None
        target_py = None
        locked_text = ""

        # 1. FACE TRACKING MODE
        if ai_state == "face":
            if face_results.detections:
                detection = face_results.detections[0]
                bboxC = detection.location_data.relative_bounding_box
                
                target_px = int((bboxC.xmin + bboxC.width / 2) * CAM_W)
                target_py = int((bboxC.ymin + bboxC.height / 2) * CAM_H)

                last_seen_text = "your face"
                cv2.circle(img, (target_px, target_py), 15, (255, 255, 0), -1)
                mpDraw.draw_detection(img, detection)
                locked_text = "FACE LOCKED"
            else:
                last_seen_text = "nobody"

        # 2. HAND TRACKING MODE
        elif ai_state == "hands" and tracking_enabled:
            if hand_results.multi_hand_landmarks:
                hand = hand_results.multi_hand_landmarks[0]
                mpDraw.draw_landmarks(img, hand, mpHands.HAND_CONNECTIONS)

                palm_ids = [0, 5, 9, 13, 17]
                xs = [int(hand.landmark[idx].x * CAM_W) for idx in palm_ids]
                ys = [int(hand.landmark[idx].y * CAM_H) for idx in palm_ids]

                target_px = int(sum(xs) / len(xs))
                target_py = int(sum(ys) / len(ys))

                last_seen_text = "a hand"
                cv2.circle(img, (target_px, target_py), 15, (0, 0, 255), -1)
                locked_text = "HAND LOCKED"
            else:
                last_seen_text = "nothing"

        # 3. APPLY MOVEMENT LOGIC
        if ai_state == "manual":
            currentX += SMOOTHING * (manual_target_x - currentX)
            currentY += SMOOTHING * (manual_target_y - currentY)
            buzzer.write(0)
            cv2.putText(img, "MANUAL OVERRIDE", (850, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 3)

        else:
            if target_px is not None and target_py is not None:
                errorX = target_px - centerX
                errorY = target_py - centerY

                if abs(errorX) > DEADZONE:
                    targetX = np.interp(target_px, [0, CAM_W], [0, 180])
                    currentX += SMOOTHING * (targetX - currentX)

                if abs(errorY) > DEADZONE:
                    targetY = np.interp(target_py, [0, CAM_H], [180, 0])
                    currentY += SMOOTHING * (targetY - currentY)

                if abs(errorX) < 40 and abs(errorY) < 40:
                    buzzer.write(1)
                    cv2.putText(img, locked_text, (850, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                else:
                    buzzer.write(0)
            else:
                buzzer.write(0)

        currentX = max(0, min(180, currentX))
        currentY = max(0, min(180, currentY))
        
        servoX.write(int(currentX))
        servoY.write(int(currentY))

        cv2.putText(img, f"Servo X : {int(currentX)}", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,0,0), 2)
        cv2.putText(img, f"Servo Y : {int(currentY)}", (20,80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,0,0), 2)
        cv2.putText(img, f"Mode: {ai_state.upper()}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imshow("Jarvis Multi-Tracking", img)

        key = cv2.waitKey(1)
        if key == 27:
            break

except KeyboardInterrupt:
    print("\nManual shutdown initiated...")

# ==========================================
# CLEANUP
# ==========================================
finally:
    print("Cleaning up resources...")
    jarvis_running = False
    cap.release()
    try:
        buzzer.write(0)
        board.exit()
    except:
        pass
    cv2.destroyAllWindows()
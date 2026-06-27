import cv2
import numpy as np
import time
from cvzone.FaceDetectionModule import FaceDetector
from pyfirmata2 import Arduino

# ----------------------------
# SETTINGS
# ----------------------------

PORT = "COM4"

CAM_W = 1280
CAM_H = 720

SERVO_X_PIN = 9
SERVO_Y_PIN = 8
BUZZER_PIN = 11

SMOOTHING = 0.12
DEADZONE = 25

# ----------------------------

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

if not cap.isOpened():
    print("Camera not accessible")
    exit()

print("Connecting to Arduino...")

board = Arduino(PORT)

servoX = board.get_pin(f'd:{SERVO_X_PIN}:s')
servoY = board.get_pin(f'd:{SERVO_Y_PIN}:s')
buzzer = board.get_pin(f'd:{BUZZER_PIN}:o')

currentX = 90
currentY = 90

servoX.write(currentX)
servoY.write(currentY)

detector = FaceDetector()

centerX = CAM_W // 2
centerY = CAM_H // 2

last_beep = 0

print("System Ready")

while True:

    success, img = cap.read()

    if not success:
        continue

    img, bboxs = detector.findFaces(img, draw=False)

    cv2.line(img, (centerX, 0), (centerX, CAM_H), (0, 255, 0), 1)
    cv2.line(img, (0, centerY), (CAM_W, centerY), (0, 255, 0), 1)

    target_locked = False

    if bboxs:

        fx, fy = bboxs[0]["center"]

        cv2.circle(img, (fx, fy), 15, (0, 0, 255), -1)

        errorX = fx - centerX
        errorY = fy - centerY

        if abs(errorX) > DEADZONE:

            targetX = np.interp(
                fx,
                [0, CAM_W],
                [180, 0]
            )

            currentX += SMOOTHING * (targetX - currentX)

        if abs(errorY) > DEADZONE:

            targetY = np.interp(
                fy,
                [0, CAM_H],
                [180, 0]
            )

            currentY += SMOOTHING * (targetY - currentY)

        currentX = max(0, min(180, currentX))
        currentY = max(0, min(180, currentY))

        servoX.write(int(currentX))
        servoY.write(int(currentY))

        # ----------------------------------
        # TARGET LOCK LOGIC
        # ----------------------------------

        if 75 <= currentX <= 85 and 75 <= currentY <= 85:
            target_locked = True

        distance = (abs(errorX) + abs(errorY)) / 2

        now = time.time()

        if target_locked:

            buzzer.write(1)

            cv2.putText(
                img,
                "TARGET LOCKED",
                (850, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                3
            )

            cv2.rectangle(
                img,
                (fx - 60, fy - 60),
                (fx + 60, fy + 60),
                (0, 255, 0),
                3
            )

        else:

            buzzer.write(0)

            interval = np.interp(
                distance,
                [0, 500],
                [0.05, 1.0]
            )

            if now - last_beep > interval:

                buzzer.write(1)
                time.sleep(0.03)
                buzzer.write(0)

                last_beep = now

            cv2.putText(
                img,
                "TRACKING",
                (950, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2
            )

    else:

        buzzer.write(0)

        cv2.putText(
            img,
            "NO TARGET",
            (950, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            2
        )

    cv2.putText(
        img,
        f"Servo X : {int(currentX)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2
    )

    cv2.putText(
        img,
        f"Servo Y : {int(currentY)}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 0, 0),
        2
    )

    cv2.imshow("Face Tracking System", img)

    key = cv2.waitKey(1)

    if key == 27:
        break

cap.release()

buzzer.write(0)

board.exit()

cv2.destroyAllWindows()
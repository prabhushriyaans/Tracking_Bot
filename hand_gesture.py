import cv2
import mediapipe as mp
import numpy as np
import time
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

print("Connecting Arduino...")

board = Arduino(PORT)

servoX = board.get_pin(f'd:{SERVO_X_PIN}:s')
servoY = board.get_pin(f'd:{SERVO_Y_PIN}:s')
buzzer = board.get_pin(f'd:{BUZZER_PIN}:o')

currentX = 90
currentY = 90

servoX.write(currentX)
servoY.write(currentY)

cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

centerX = CAM_W // 2
centerY = CAM_H // 2

# ----------------------------
# MEDIAPIPE HAND DETECTOR
# ----------------------------

mpHands = mp.solutions.hands
hands = mpHands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mpDraw = mp.solutions.drawing_utils

last_beep = 0

print("Hand Tracking Ready")

while True:

    success, img = cap.read()

    if not success:
        continue

    img = cv2.flip(img, 1)

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    results = hands.process(rgb)

    cv2.line(img, (centerX, 0), (centerX, CAM_H), (0, 255, 0), 1)
    cv2.line(img, (0, centerY), (CAM_W, centerY), (0, 255, 0), 1)

    if results.multi_hand_landmarks:

        hand = results.multi_hand_landmarks[0]

        mpDraw.draw_landmarks(
            img,
            hand,
            mpHands.HAND_CONNECTIONS
        )

        # Palm center approximation
        palm_ids = [0, 5, 9, 13, 17]

        xs = []
        ys = []

        for idx in palm_ids:
            lm = hand.landmark[idx]

            px = int(lm.x * CAM_W)
            py = int(lm.y * CAM_H)

            xs.append(px)
            ys.append(py)

        handX = int(sum(xs) / len(xs))
        handY = int(sum(ys) / len(ys))

        cv2.circle(img, (handX, handY), 15, (0, 0, 255), -1)

        errorX = handX - centerX
        errorY = handY - centerY

        if abs(errorX) > DEADZONE:

            targetX = np.interp(
                handX,
                [0, CAM_W],
                [0, 180]
            )

            currentX += SMOOTHING * (targetX - currentX)

        if abs(errorY) > DEADZONE:

            targetY = np.interp(
                handY,
                [0, CAM_H],
                [180, 0]
            )

            currentY += SMOOTHING * (targetY - currentY)

        currentX = max(0, min(180, currentX))
        currentY = max(0, min(180, currentY))

        servoX.write(int(currentX))
        servoY.write(int(currentY))

        distance = (abs(errorX) + abs(errorY)) / 2

        target_locked = (
            abs(errorX) < 40 and
            abs(errorY) < 40
        )

        now = time.time()

        if target_locked:

            buzzer.write(1)

            cv2.putText(
                img,
                "HAND LOCKED",
                (900, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                3
            )

            cv2.rectangle(
                img,
                (handX - 70, handY - 70),
                (handX + 70, handY + 70),
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
                "TRACKING HAND",
                (900, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                2
            )

    else:

        buzzer.write(0)

        cv2.putText(
            img,
            "NO HAND",
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

    cv2.imshow("Hand Tracking System", img)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
buzzer.write(0)
board.exit()
cv2.destroyAllWindows()
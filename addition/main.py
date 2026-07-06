"""
Candy Turret - Hand Gesture Trigger ("6-7" seesaw motion)
-----------------------------------------------------------
Runs on your PC. Watches your webcam for BOTH hands moving up and down
(the "6-7" gesture) and sends a single byte 'F' over serial to the
XIAO RP2040, same as face_gesture_serial.py does for mouth-open.

Unlike mouth-open detection, this needs to look at motion over time,
not just a single frame - so it tracks each hand's vertical position
over the last ~1.5 seconds and checks for enough up/down reversals
with enough amplitude to count as a real wave, not just jitter.

Install deps:
    pip install opencv-python mediapipe pyserial certifi

Then edit SERIAL_PORT below to match your board (check Thonny's port
dropdown - it changes on macOS every time the board reconnects):
    Windows:      "COM5"
    macOS:        "/dev/cu.usbmodemXXXX"  (NOT "tty.", use "cu.")
"""

import os
import ssl
import time
import urllib.request
from collections import deque

import cv2
import mediapipe as mp
import serial
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = None

# ---------------- Config ----------------
SERIAL_PORT = "/dev/cu.usbmodem1101"   # <-- CHANGE THIS to match Thonny's port dropdown
BAUD_RATE = 115200

TRIGGER_COOLDOWN = 2.0       # seconds between allowed shots (debounce)

WINDOW_SECONDS = 1.5         # how far back we look for the wave pattern
MIN_AMPLITUDE = 0.12         # normalized (0-1 of frame height) vertical range required
MIN_REVERSALS = 3            # direction changes needed within the window (e.g. up-down-up)
NOISE_EPS = 0.01             # ignore tiny frame-to-frame jitter below this when counting reversals

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


def ensure_model():
    if os.path.exists(MODEL_PATH):
        return
    print("Downloading hand landmark model (one-time, ~8MB)...")
    try:
        if SSL_CONTEXT is not None:
            with urllib.request.urlopen(MODEL_URL, context=SSL_CONTEXT) as resp:
                data = resp.read()
            with open(MODEL_PATH, "wb") as f:
                f.write(data)
        else:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Done.")
    except Exception as e:
        print(f"[!] Download failed: {e}")
        print("    Try: pip install certifi")
        print('    Or on macOS: /Applications/Python\\ 3.13/Install\\ Certificates.command')
        raise


def connect_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Connected to {SERIAL_PORT}")
        return ser
    except Exception as e:
        print(f"[!] Could not open serial port {SERIAL_PORT}: {e}")
        print("    Continuing without serial - gestures will only print to console.")
        return None


def open_camera():
    for index in range(4):
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            continue
        ok, frame = cap.read()
        if ok and frame is not None:
            print(f"Using camera index {index}")
            return cap
        cap.release()
    return None


def count_reversals(values):
    """Count direction changes in a sequence, ignoring tiny jitter."""
    diffs = []
    for a, b in zip(values, values[1:]):
        d = b - a
        if abs(d) > NOISE_EPS:
            diffs.append(1 if d > 0 else -1)
    reversals = 0
    for a, b in zip(diffs, diffs[1:]):
        if a != b:
            reversals += 1
    return reversals


def is_waving(history):
    """history: deque of (timestamp, y) for one hand."""
    if len(history) < 5:
        return False
    ys = [y for _, y in history]
    amplitude = max(ys) - min(ys)
    if amplitude < MIN_AMPLITUDE:
        return False
    return count_reversals(ys) >= MIN_REVERSALS


def main():
    ensure_model()

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        running_mode=mp_vision.RunningMode.VIDEO,
    )
    landmarker = mp_vision.HandLandmarker.create_from_options(options)

    ser = connect_serial()
    cap = open_camera()
    if cap is None:
        print("[!] Could not get a working camera stream.")
        return

    # rolling per-hand wrist position history (WRIST landmark = index 0)
    hand_histories = [deque(), deque()]

    last_trigger = 0.0
    start_time = time.time()

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            print("[!] Lost camera frame - stopping.")
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - start_time) * 1000)

        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        now = time.time()
        num_hands = len(result.hand_landmarks) if result.hand_landmarks else 0

        # update history for up to 2 hands, drop old points outside the window
        for i in range(2):
            if i < num_hands:
                wrist = result.hand_landmarks[i][0]  # landmark 0 = wrist
                hand_histories[i].append((now, wrist.y))
                cx, cy = int(wrist.x * w), int(wrist.y * h)
                cv2.circle(frame, (cx, cy), 8, (0, 255, 255), -1)
            while hand_histories[i] and now - hand_histories[i][0][0] > WINDOW_SECONDS:
                hand_histories[i].popleft()

        triggered = False
        if num_hands >= 2:
            both_waving = is_waving(hand_histories[0]) and is_waving(hand_histories[1])
            if both_waving and (now - last_trigger) > TRIGGER_COOLDOWN:
                triggered = True
                last_trigger = now
                print("6-7 gesture detected - FIRE!")
                if ser:
                    ser.write(b"F\n")

        color = (0, 0, 255) if triggered else (0, 255, 0)
        cv2.putText(frame, f"Hands detected: {num_hands}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, "Wave both hands up/down to fire | 'q' to quit", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.imshow("Candy Turret - 6-7 Gesture Trigger", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    if ser:
        ser.close()


if __name__ == "__main__":
    main()
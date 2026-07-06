"""
Candy Turret - Face Gesture Trigger
------------------------------------
Runs on your PC (not the RP2040). Watches your webcam, detects when you
open your mouth (the "gesture") using MediaPipe's FaceLandmarker task,
and sends a single byte 'F' over serial to the XIAO RP2040, which is
running main.py (MicroPython) and will fire the shooting motors when it
receives that byte.

NOTE: newer mediapipe versions (0.10.3x+) removed the old
mp.solutions.face_mesh API. This script uses the current replacement,
the MediaPipe Tasks API, which needs a small model file - it will be
downloaded automatically the first time you run this script (needs
internet once, ~4MB).

Install deps:
    pip install opencv-python mediapipe pyserial

Then edit SERIAL_PORT below to match your board:
    Windows:      "COM5"  (check Device Manager)
    macOS/Linux:  "/dev/ttyACM0" or "/dev/tty.usbmodemXXXX" (check `ls /dev/tty.*`)
"""

import os
import ssl
import time
import urllib.request

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
SERIAL_PORT = "/dev/cu.usbmodem101" 
BAUD_RATE = 115200

JAW_OPEN_THRESHOLD = 0.5    # 0.0-1.0, how far mouth must open to count as "open"
CONSEC_FRAMES = 3           # frames mouth must stay open before it counts
TRIGGER_COOLDOWN = 1.5      # seconds between allowed shots (debounce)

MODEL_PATH = "face_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)


def ensure_model():
    if os.path.exists(MODEL_PATH):
        return

    print("Downloading face landmark model (one-time, ~4MB)...")
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
        print("    On macOS, this is usually a missing-certificates issue. Try running:")
        print('    /Applications/Python\\ 3.13/Install\\ Certificates.command')
        print("    (adjust the version folder name to match your Python install),")
        print("    or run: pip install certifi")
        raise


def connect_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # let the board reset after opening the port
        print(f"Connected to {SERIAL_PORT}")
        return ser
    except Exception as e:
        print(f"[!] Could not open serial port {SERIAL_PORT}: {e}")
        print("    Continuing without serial - gestures will only print to console.")
        return None


def get_jaw_open_score(result):
    if not result.face_blendshapes:
        return 0.0
    for category in result.face_blendshapes[0]:
        if category.category_name == "jawOpen":
            return category.score
    return 0.0


def draw_landmarks(frame, result):
    if not result.face_landmarks:
        return
    h, w = frame.shape[:2]
    for landmark in result.face_landmarks[0]:
        x = int(landmark.x * w)
        y = int(landmark.y * h)
        cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)


def main():
    ensure_model()

    base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=False,
        num_faces=1,
        running_mode=mp_vision.RunningMode.VIDEO,
    )
    landmarker = mp_vision.FaceLandmarker.create_from_options(options)

    ser = connect_serial()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[!] Could not open webcam.")
        return

    consec = 0
    last_trigger = 0.0
    start_time = time.time()

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.time() - start_time) * 1000)

        result = landmarker.detect_for_video(mp_image, timestamp_ms)
        jaw_open = get_jaw_open_score(result)
        draw_landmarks(frame, result)

        triggered = False
        if jaw_open > JAW_OPEN_THRESHOLD:
            consec += 1
        else:
            consec = 0

        now = time.time()
        if consec >= CONSEC_FRAMES and (now - last_trigger) > TRIGGER_COOLDOWN:
            triggered = True
            last_trigger = now
            consec = 0

            print("FIRE gesture detected!")
            if ser:
                ser.write(b"F\n")

        color = (0, 0, 255) if triggered else (0, 255, 0)
        cv2.putText(frame, f"jawOpen: {jaw_open:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, "Open mouth to fire | 'q' to quit", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.imshow("Candy Turret - Face Gesture Trigger", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()
    if ser:
        ser.close()


if __name__ == "__main__":
    main()
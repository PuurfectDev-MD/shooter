"""
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

TRIGGER_COOLDOWN = 2.0       # seconds between allowed shots (shared by both gestures)

# --- mouth-open settings ---
JAW_OPEN_THRESHOLD = 0.5
CONSEC_FRAMES = 3

# --- hand-wave settings ---
WINDOW_SECONDS = 2.0         # longer window = easier to catch a full up-down-up wave
MIN_AMPLITUDE = 0.06         # lowered from 0.12 - smaller waves now count
MIN_REVERSALS = 2            # lowered from 3 - just one full up-down now counts
NOISE_EPS = 0.006            # lowered from 0.01 - counts smaller direction changes
HAND_STALE_SECONDS = 0.4     # keep treating a hand as "present" for this long after
                             # MediaPipe briefly loses track of it (flicker tolerance)

FACE_MODEL_PATH = "face_landmarker.task"
FACE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

HAND_MODEL_PATH = "hand_landmarker.task"
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)


def ensure_model(path, url, label):
    if os.path.exists(path):
        return
    print(f"Downloading {label} model (one-time)...")
    try:
        if SSL_CONTEXT is not None:
            with urllib.request.urlopen(url, context=SSL_CONTEXT) as resp:
                data = resp.read()
            with open(path, "wb") as f:
                f.write(data)
        else:
            urllib.request.urlretrieve(url, path)
        print("Done.")
    except Exception as e:
        print(f"[!] Download failed: {e}")
        print("    Try: pip install certifi")
        print('    Or on macOS: /Applications/Python\\ 3.13/Install\\ Certificates.command')
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


# ---------------- Mouth-open helpers ----------------

def get_jaw_open_score(result):
    if not result.face_blendshapes:
        return 0.0
    for category in result.face_blendshapes[0]:
        if category.category_name == "jawOpen":
            return category.score
    return 0.0


def draw_face_landmarks(frame, result):
    if not result.face_landmarks:
        return
    h, w = frame.shape[:2]
    for landmark in result.face_landmarks[0]:
        x = int(landmark.x * w)
        y = int(landmark.y * h)
        cv2.circle(frame, (x, y), 1, (0, 255, 0), -1)


# ---------------- Hand-wave helpers ----------------

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
    ensure_model(FACE_MODEL_PATH, FACE_MODEL_URL, "face landmark")
    ensure_model(HAND_MODEL_PATH, HAND_MODEL_URL, "hand landmark")

    face_options = mp_vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=FACE_MODEL_PATH),
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=False,
        num_faces=1,
        running_mode=mp_vision.RunningMode.VIDEO,
    )
    face_landmarker = mp_vision.FaceLandmarker.create_from_options(face_options)

    hand_options = mp_vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=HAND_MODEL_PATH),
        num_hands=2,
        running_mode=mp_vision.RunningMode.VIDEO,
    )
    hand_landmarker = mp_vision.HandLandmarker.create_from_options(hand_options)

    ser = connect_serial()
    cap = open_camera()
    if cap is None:
        print("[!] Could not get a working camera stream.")
        return

    consec_mouth = 0
    hand_histories = [deque(), deque()]
    hand_last_seen = [0.0, 0.0]

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

        # Run both detectors on the same frame
        face_result = face_landmarker.detect_for_video(mp_image, timestamp_ms)
        hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

        now = time.time()

        # --- mouth-open check ---
        jaw_open = get_jaw_open_score(face_result)
        draw_face_landmarks(frame, face_result)
        if jaw_open > JAW_OPEN_THRESHOLD:
            consec_mouth += 1
        else:
            consec_mouth = 0
        mouth_ready = consec_mouth >= CONSEC_FRAMES

        # --- hand-wave check ---
        num_hands = len(hand_result.hand_landmarks) if hand_result.hand_landmarks else 0
        for i in range(2):
            if i < num_hands:
                wrist = hand_result.hand_landmarks[i][0]  # landmark 0 = wrist
                hand_histories[i].append((now, wrist.y))
                hand_last_seen[i] = now
                cx, cy = int(wrist.x * w), int(wrist.y * h)
                cv2.circle(frame, (cx, cy), 8, (0, 255, 255), -1)
            while hand_histories[i] and now - hand_histories[i][0][0] > WINDOW_SECONDS:
                hand_histories[i].popleft()
        # treat a hand as "present" if seen recently, even if MediaPipe briefly
        # dropped it this exact frame (fast waving motion causes flicker)
        hands_present = sum(1 for t in hand_last_seen if now - t <= HAND_STALE_SECONDS)
        wave0 = is_waving(hand_histories[0])
        wave1 = is_waving(hand_histories[1])
        hands_ready = hands_present >= 2 and wave0 and wave1

        # --- fire on whichever gesture happened, shared cooldown ---
        triggered = False
        cooldown_ok = (now - last_trigger) > TRIGGER_COOLDOWN
        source = None
        if cooldown_ok and mouth_ready:
            triggered = True
            source = "mouth-open"
            consec_mouth = 0
        elif cooldown_ok and hands_ready:
            triggered = True
            source = "hand-wave"

        if triggered:
            last_trigger = now
            print(f"FIRE gesture detected! ({source})")
            if ser:
                ser.write(b"F\n")

        def hand_debug(history):
            if len(history) < 2:
                return "amp=0.00 rev=0"
            ys = [y for _, y in history]
            return f"amp={max(ys) - min(ys):.2f} rev={count_reversals(ys)}"

        color = (0, 0, 255) if triggered else (0, 255, 0)
        cv2.putText(frame, f"jawOpen: {jaw_open:.2f}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Hands present: {hands_present}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame, f"Hand0: {hand_debug(hand_histories[0])}  Hand1: {hand_debug(hand_histories[1])}",
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)
        cv2.putText(frame, f"(need amp>={MIN_AMPLITUDE} rev>={MIN_REVERSALS})", (10, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, "Open mouth OR wave both hands to fire | 'q' to quit", (10, 145),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.imshow("Candy Turret - Combined Gesture Trigger", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    face_landmarker.close()
    hand_landmarker.close()
    if ser:
        ser.close()


if __name__ == "__main__":
    main()
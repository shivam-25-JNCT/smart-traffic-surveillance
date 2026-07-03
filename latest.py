"""
plate_pipeline.py  —  SMOOTH real-time ANPR.

Why it's smooth: display, detection, OCR, and saving are DECOUPLED so the video
never waits on heavy work.

  [Capture thread]  reads frames -> keeps latest + rolling buffer
  [Detect thread]   runs YOLO on the latest frame -> boxes + feeds OCR
  [OCR process]     reads plate text -> validates/corrects -> results
  [Saver thread]    writes snapshot + 5s clip + POSTs to the database
  [Main/display]    shows the latest frame + latest boxes at FULL fps

Detection can be slow and the video still plays smoothly, because the display
loop never blocks on it — it just draws the most recent boxes it has.

Accuracy: Indian-plate domain rules (plate_rules.py) + consensus voting.
"""

import os
import sys
import time
import queue
import logging
import threading
import multiprocessing as mp
from collections import defaultdict, Counter, deque
from datetime import datetime

import os as _os
_os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2
import requests
from ultralytics import YOLO
from paddleocr import PaddleOCR
from plate_rules import validate_or_correct

# ============================================================
# CONFIG
# ============================================================
SOURCE = "videos/bike1.mp4"   # FILE demo (safe). For live: paste the RTSP URL here.
PLATE_MODEL = "model/best.pt"
PLATE_CONF = 0.35
OCR_MIN_CONF = 0.45
INFER_WIDTH = 480
VOTES_NEEDED = 1                     # 1 = save on first valid/corrected read
USE_CPU = False

CLIP_PRE = 3
CLIP_POST = 2
FALLBACK_FPS = 20

API_URL = "http://127.0.0.1:8000/api/v1/alerts/trigger"
CAMERA_ID = 201
EVIDENCE_DIR = "evidence"


# ============================================================
# OCR (inside worker process)
# ============================================================
def preprocess(crop):
    if crop is None or crop.size == 0:
        return None
    h, w = crop.shape[:2]
    if max(h, w) < 200:
        crop = cv2.resize(crop, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    elif max(h, w) < 320:
        crop = cv2.resize(crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


def extract_pairs(result):
    pairs = []
    if not result:
        return pairs
    res = result[0]
    try:
        for t, s in zip(res["rec_texts"], res["rec_scores"]):
            if t and t.strip():
                pairs.append((t, float(s)))
        return pairs
    except (KeyError, TypeError, IndexError):
        pass
    if isinstance(res, (list, tuple)):
        for line in res:
            try:
                pairs.append((line[1][0], float(line[1][1])))
            except (IndexError, TypeError):
                continue
    return pairs


def read_plate(ocr, crop):
    img = preprocess(crop)
    if img is None:
        return None, 0.0
    try:
        result = ocr.predict(img)
    except AttributeError:
        result = ocr.ocr(img)
    pairs = [(t, s) for (t, s) in extract_pairs(result) if s >= OCR_MIN_CONF]
    if not pairs:
        return None, 0.0
    cands = []
    text, score = max(pairs, key=lambda p: p[1])
    cands.append((text, score))
    if len(pairs) > 1:                        # stacked bike plates
        cands.append(("".join(t for t, _ in pairs),
                      sum(s for _, s in pairs) / len(pairs)))
    # apply domain rules (validate or correct)
    fixed = []
    for t, c in cands:
        p = validate_or_correct(t)
        if p:
            fixed.append((p, c))
    if fixed:
        return max(fixed, key=lambda x: x[1])
    return None, 0.0


def ocr_worker(task_queue, result_queue, ready_event):
    logging.getLogger("ppocr").setLevel(logging.ERROR)
    ocr = PaddleOCR(lang="en")
    print("🧠 OCR worker ready.")
    ready_event.set()
    while True:
        item = task_queue.get()
        if item is None:
            break
        crop, = item
        plate, conf = read_plate(ocr, crop)
        if plate:
            result_queue.put((plate, conf, crop))


# ============================================================
# SAVE + API (runs in the saver thread, off the display path)
# ============================================================
def save_snapshot(crop, plate):
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(EVIDENCE_DIR, f"{plate}_{ts}.jpg")
    cv2.imwrite(path, crop)
    return path


def save_clip(frames, fps, plate):
    if not frames:
        return None
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(EVIDENCE_DIR, f"{plate}_{ts}.mp4")
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    for f in frames:
        writer.write(f)
    writer.release()
    return path


def post_to_db(plate, conf, snap, clip):
    payload = {
        "camera_id": CAMERA_ID,
        "alert_category": f"ANPR_{plate}",
        "severity_level": 1,
        "confidence_score": round(float(conf), 2),
        "frame_path": snap,
        "clip_path": clip,
        "plate_number": plate,
        "violation_type": "ANPR",
    }
    try:
        r = requests.post(API_URL, json=payload, timeout=10)
        print(f"   📤 db: {plate}" if r.status_code == 200
              else f"   ⚠️ api {r.status_code}: {r.text}")
    except Exception as e:
        print(f"   ❌ api unreachable ({e})")


def saver_thread(save_queue, fps, stop):
    while not stop.is_set() or not save_queue.empty():
        try:
            plate, conf, snap_crop, clip_frames = save_queue.get(timeout=0.5)
        except queue.Empty:
            continue
        snap = save_snapshot(snap_crop, plate)
        clip = save_clip(clip_frames, fps, plate)
        print(f"✅ SAVED {plate} ({conf:.2f})  snap+clip")
        with open("detected_plates_log.txt", "a") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}, {plate}, {conf:.2f}, {snap}, {clip}\n")
        post_to_db(plate, conf, snap, clip)


# ============================================================
# CAPTURE THREAD — always holds the latest frame + rolling buffer
# ============================================================
class Capture:
    def __init__(self, source, pre_frames):
        self.cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.lock = threading.Lock()
        self.frame = None
        self.ok = self.cap.isOpened()
        self.rolling = deque(maxlen=pre_frames)
        self.pending = {}          # plate -> [frames, remaining, conf, snap_crop]
        self.ready = queue.Queue()  # finished clips -> saver
        self.stop = threading.Event()
        self.t = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self.t.start()

    def _loop(self):
        while not self.stop.is_set():
            ok, f = self.cap.read()
            if not ok:
                time.sleep(0.02)      # RTSP hiccup — retry, don't die
                continue
            with self.lock:
                self.frame = f
                self.rolling.append(f.copy())
                for plate in list(self.pending.keys()):
                    frames, rem, conf, snap = self.pending[plate]
                    frames.append(f.copy())
                    rem -= 1
                    if rem <= 0:
                        self.ready.put((plate, conf, snap, frames))
                        del self.pending[plate]
                    else:
                        self.pending[plate] = [frames, rem, conf, snap]

    def read(self):
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def start_clip(self, plate, conf, snap_crop, post_frames):
        with self.lock:
            self.pending[plate] = [list(self.rolling), post_frames, conf, snap_crop]

    def release(self):
        self.stop.set()
        self.t.join(timeout=2)
        self.cap.release()


# ============================================================
# DETECTION THREAD — runs YOLO on latest frame, never blocks display
# ============================================================
def detect_loop(cap, model, device, task_queue, boxes_ref, stop):
    last_ocr = 0.0
    OCR_INTERVAL = 0.5
    MAX_OCR_PLATES = 3     # never OCR more than this many plates per cycle          # only submit crops to OCR ~2-3x per second
    while not stop.is_set():
        frame = cap.read()
        if frame is None:
            time.sleep(0.01)
            continue
        scale = 1.0
        inf = frame
        if frame.shape[1] > INFER_WIDTH:
            scale = INFER_WIDTH / frame.shape[1]
            inf = cv2.resize(frame, None, fx=scale, fy=scale)
        res = model(inf, verbose=False, conf=PLATE_CONF, device=device)[0]
        time.sleep(0.01)  # yield so display stays smooth

        now = time.time()
        submit = (now - last_ocr) >= OCR_INTERVAL   # throttle OCR submissions
        new_boxes = []
        boxes_list = []
        for b in res.boxes:
            x1, y1, x2, y2 = (int(v / scale) for v in b.xyxy[0])
            new_boxes.append((x1, y1, x2, y2))
            boxes_list.append((x1, y1, x2, y2))
        boxes_ref[0] = new_boxes   # draw ALL boxes (cheap)

        if submit and boxes_list:
            # Only OCR the MAX_OCR_PLATES largest (closest) plates this cycle.
            boxes_list.sort(key=lambda b: (b[2]-b[0])*(b[3]-b[1]), reverse=True)
            for (x1, y1, x2, y2) in boxes_list[:MAX_OCR_PLATES]:
                pad = 5
                yy1, yy2 = max(0, y1 - pad), min(frame.shape[0], y2 + pad)
                xx1, xx2 = max(0, x1 - pad), min(frame.shape[1], x2 + pad)
                crop = frame[yy1:yy2, xx1:xx2].copy()
                if crop.size == 0:
                    continue
                try:
                    task_queue.put_nowait((crop,))
                    last_ocr = now
                except queue.Full:
                    break      # worker busy — stop, don't thrash


# ============================================================
# MAIN / DISPLAY  (main thread — smooth, full fps)
# ============================================================
def main(source=SOURCE):
    print("⏳ Loading plate model...")
    model = YOLO(PLATE_MODEL)
    device = "cpu" if USE_CPU else "mps"

    fps = FALLBACK_FPS
    probe = cv2.VideoCapture(source)
    if probe.isOpened():
        f = probe.get(cv2.CAP_PROP_FPS)
        if f and f > 0:
            fps = f
    probe.release()
    pre_frames, post_frames = int(fps * CLIP_PRE), int(fps * CLIP_POST)

    cap = Capture(source, pre_frames)
    if not cap.ok:
        print(f"❌ Cannot open source: {source}")
        return
    cap.start()

    task_queue = mp.Queue(maxsize=8)
    result_queue = mp.Queue()
    ready_event = mp.Event()
    worker = mp.Process(target=ocr_worker,
                        args=(task_queue, result_queue, ready_event), daemon=True)
    worker.start()
    print("⏳ Waiting for PaddleOCR...")
    ready_event.wait()

    save_queue = queue.Queue()
    stop = threading.Event()
    threading.Thread(target=saver_thread, args=(save_queue, fps, stop), daemon=True).start()

    boxes_ref = [[]]
    threading.Thread(target=detect_loop,
                     args=(cap, model, device, task_queue, boxes_ref, stop),
                     daemon=True).start()

    votes = defaultdict(Counter)
    best_conf, last_crop, saved = {}, {}, set()
    print("🚀 Running smoothly. Press 'q' to quit.")

    while True:
        frame = cap.read()
        if frame is None:
            if not cap.ok:
                break
            time.sleep(0.01)
            continue

        # move finished clips to the saver
        while not cap.ready.empty():
            plate, conf, snap, frames = cap.ready.get()
            save_queue.put((plate, conf, snap, frames))

        # drain OCR results -> vote -> confirm
        while True:
            try:
                plate, conf, crop = result_queue.get_nowait()
            except queue.Empty:
                break
            if plate in saved:
                continue
            votes[plate][plate] += 1
            if conf > best_conf.get(plate, 0.0):
                best_conf[plate] = conf
                last_crop[plate] = crop
            if votes[plate][plate] >= VOTES_NEEDED:
                saved.add(plate)
                cap.start_clip(plate, best_conf.get(plate, conf),
                               last_crop.get(plate, crop), post_frames)

        # draw latest boxes (read-only, never blocks)
        for (x1, y1, x2, y2) in boxes_ref[0]:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.imshow("Plate Pipeline", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stop.set()
    time.sleep(0.5)
    task_queue.put(None)
    worker.join(timeout=5)
    if worker.is_alive():
        worker.terminate()
    cap.release()
    cv2.destroyAllWindows()
    print(f"\n📊 Total unique plates saved: {len(saved)}")


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    main(sys.argv[1] if len(sys.argv) > 1 else SOURCE)
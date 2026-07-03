"""
anpr_tracked.py  —  ANPR structured like the Computer Vision Engineer repo,
but with PaddleOCR (not EasyOCR) + YOUR requirements (snapshot, 5s clip, DB).

Structure (same as the reference):
  1. Detect VEHICLES with a general YOLO model.
  2. Track them with SORT -> each vehicle gets a persistent ID.
  3. Detect PLATES with your trained model.
  4. Match each plate to the vehicle it sits inside (by its car_id).
  5. OCR the plate; keep the BEST read per vehicle ID.
  6. On a confident read: save snapshot + 5s clip + POST to the database.

Because we track per-vehicle, each car is ONE record with its best plate —
no per-frame duplicates.
"""

import os as _os
_os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

import os
import sys
import time
from collections import deque
from datetime import datetime

import cv2
import numpy as np
import requests
from ultralytics import YOLO
from paddleocr import PaddleOCR

from sort import Sort
from plate_rules import validate_or_correct

# SOURCE = "rtsp://admin:admin@192.168.10.19:554/ch0_0.264"
SOURCE = "videos/bike1.mp4"           # file for demo; RTSP URL for live
VEHICLE_MODEL = "yolov8n.pt"
PLATE_MODEL = "model/best.pt"
VEHICLE_CLASSES = [2, 3, 5, 7]       # car, motorcycle, bus, truck (COCO ids)
VEHICLE_CONF = 0.25
PLATE_CONF = 0.20
OCR_MIN_CONF = 0.35
USE_CPU = True

CLIP_PRE_SEC = 3
CLIP_POST_SEC = 2
FALLBACK_FPS = 20
#please change this. 
API_URL = "http://127.0.0.1:8000/api/v1/alerts/trigger"
CAMERA_ID = 201
EVIDENCE_DIR = "evidence"


# ============================================================
# OCR
# ============================================================
_ocr = PaddleOCR(lang="en")


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


def read_plate(crop):
    """crop -> (plate, conf) using PaddleOCR + domain rules. None if unreadable."""
    img = preprocess(crop)
    if img is None:
        return None, 0.0
    try:
        result = _ocr.predict(img)
    except AttributeError:
        result = _ocr.ocr(img)
    if not result:
        return None, 0.0
    res = result[0]
    pairs = []
    try:
        for t, s in zip(res["rec_texts"], res["rec_scores"]):
            if t and t.strip() and float(s) >= OCR_MIN_CONF:
                pairs.append((t, float(s)))
    except (KeyError, TypeError, IndexError):
        if isinstance(res, (list, tuple)):
            for line in res:
                try:
                    if float(line[1][1]) >= OCR_MIN_CONF:
                        pairs.append((line[1][0], float(line[1][1])))
                except (IndexError, TypeError):
                    continue
    if not pairs:
        return None, 0.0
    # single best line + all-lines-joined (stacked bike plates)
    cands = [max(pairs, key=lambda p: p[1])]
    if len(pairs) > 1:
        cands.append(("".join(t for t, _ in pairs),
                      sum(s for _, s in pairs) / len(pairs)))
    fixed = [(validate_or_correct(t), c) for t, c in cands]
    fixed = [(p, c) for p, c in fixed if p]
    if not fixed:
        return None, 0.0
    return max(fixed, key=lambda x: x[1])


# ============================================================
# helper: which tracked car does this plate belong to?
# ============================================================
def get_car(plate_box, tracked_ids):
    px1, py1, px2, py2 = plate_box
    for j in range(tracked_ids.shape[0]):
        cx1, cy1, cx2, cy2, cid = tracked_ids[j]
        if px1 > cx1 and py1 > cy1 and px2 < cx2 and py2 < cy2:
            return cx1, cy1, cx2, cy2, cid
    return -1, -1, -1, -1, -1


# ============================================================
# SAVE + DB
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
    out = cv2.VideoWriter(path, fourcc, fps, (w, h))
    for f in frames:
        out.write(f)
    out.release()
    return path


def post_to_db(plate, conf, snap, clip):
    payload = {
        "camera_id": CAMERA_ID, "alert_category": f"ANPR_{plate}",
        "severity_level": 1, "confidence_score": round(float(conf), 2),
        "frame_path": snap, "clip_path": clip,
        "plate_number": plate, "violation_type": "ANPR",
    }
    try:
        r = requests.post(API_URL, json=payload, timeout=10)
        print(f"   📤 db: {plate}" if r.status_code == 200 else f"   ⚠️ {r.status_code}")
    except Exception as e:
        print(f"   ❌ api unreachable ({e})")


# ============================================================
# MAIN
# ============================================================
def main(source=SOURCE):
    print("⏳ Loading models...")
    vehicle_model = YOLO(VEHICLE_MODEL)
    plate_model = YOLO(PLATE_MODEL)
    tracker = Sort()
    device = "cpu" if USE_CPU else "mps"

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"❌ Cannot open source: {source}")
        return
    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = FALLBACK_FPS
    rolling = deque(maxlen=int(fps * CLIP_PRE_SEC))

    # per-vehicle best read: car_id -> {plate, conf, crop}
    best = {}
    saved = set()
    pending_clips = {}   # plate -> [frames, remaining, conf, snap]
    frame_idx = 0
    ocr_interval = 1   # OCR every frame -> catch as many plates as possible

    print("🚀 Running. Press 'q' to quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1
        
        rolling.append(frame.copy())

        # advance pending clips
        for plate in list(pending_clips.keys()):
            frames, rem, conf, snap = pending_clips[plate]
            frames.append(frame.copy())
            rem -= 1
            if rem <= 0:
                clip = save_clip(frames, fps, plate)
                print(f"✅ SAVED {plate} ({conf:.2f}) snap+clip")
                post_to_db(plate, conf, snap, clip)
                del pending_clips[plate]
            else:
                pending_clips[plate] = [frames, rem, conf, snap]

        # 1. vehicles
        vres = vehicle_model(frame, verbose=False, conf=VEHICLE_CONF, device=device)[0]
        dets = []
        for b in vres.boxes:
            if int(b.cls[0]) in VEHICLE_CLASSES:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                dets.append([x1, y1, x2, y2, float(b.conf[0])])
        dets = np.asarray(dets) if dets else np.empty((0, 5))

        # 2. track
        tracks = tracker.update(dets)  # type: ignore[arg-type]
        for x1, y1, x2, y2, cid in tracks:
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, f"ID {int(cid)}", (int(x1), int(y1) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 3. plates + 4. match to a tracked car + 5. OCR (throttled)
        if frame_idx % ocr_interval == 0:
            pres = plate_model(frame, verbose=False, conf=PLATE_CONF, device=device)[0]
            for pb in pres.boxes:
                px1, py1, px2, py2 = map(int, pb.xyxy[0])
                cx1, cy1, cx2, cy2, cid = get_car((px1, py1, px2, py2), tracks)
                if cid == -1:
                    continue
                pad = 5
                crop = frame[max(0, py1-pad):py2+pad, max(0, px1-pad):px2+pad].copy()
                if crop.size == 0:
                    continue
                plate, conf = read_plate(crop)
                if not plate:
                    continue
                # keep the best read for this vehicle ID
                if cid not in best or conf > best[cid]["conf"]:
                    best[cid] = {"plate": plate, "conf": conf, "crop": crop}

        # 6. commit each vehicle's best read once
        for cid, info in list(best.items()):
            if cid in saved:
                continue
            saved.add(cid)
            plate, conf, crop = info["plate"], info["conf"], info["crop"]
            snap = save_snapshot(crop, plate)
            pending_clips[plate] = [list(rolling), int(fps * CLIP_POST_SEC), conf, snap]

        cv2.imshow("ANPR (tracked)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # flush remaining clips
    for plate, (frames, rem, conf, snap) in pending_clips.items():
        clip = save_clip(frames, fps, plate)
        post_to_db(plate, conf, snap, clip)

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n📊 Vehicles with saved plates: {len(saved)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else SOURCE)
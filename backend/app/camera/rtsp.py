import cv2
import time
import os
import logging
import threading
from queue import Queue
from app.detector.vehicle import vehicle_detector
from app.detector.plate import plate_detector
from app.ocr.paddle import ocr_reader  
from app.database import crud
from app.database.db import SessionLocal
from app.config import RTSP_URL

logger = logging.getLogger("traffic-anpr")

class RTSPCameraStreamer:
    def __init__(self):
        self.is_running = False
        self.stream_source = RTSP_URL
        self.recently_detected = {} 
        
        # Dual-Queue Memory Allocation Pipelines
        self.raw_frame = None       
        self.display_queue = Queue(maxsize=10) 
        
        self.capture_thread = None
        self.ai_thread = None

    def start(self):
        if self.is_running:
            return {"status": "Camera already running"}
        
        self.is_running = True
        
        vehicle_detector.load_model()
        plate_detector.load_model()  
        ocr_reader.load_model()
        
        # THREAD 1: Un-delayed raw physical frames capture hardware injector
        self.capture_thread = threading.Thread(target=self._raw_capture_loop, daemon=True)
        self.capture_thread.start()
        
        # THREAD 2: Background Parallel AI Frame Analysis Processing matrix
        self.ai_thread = threading.Thread(target=self._ai_processing_loop, daemon=True)
        self.ai_thread.start()
        
        logger.info(f"⚡ Asynchronous Async-Dual Engine launched on: {self.stream_source}")
        return {"status": "Camera stream started"}

    def _raw_capture_loop(self):
        cap = cv2.VideoCapture(self.stream_source)
        
        if not cap.isOpened():
            logger.error(f"CRITICAL: Video stream source error: {self.stream_source}")
            self.is_running = False
            return

        while self.is_running and cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            frame = cv2.resize(frame, (960, 540))
            self.raw_frame = frame.copy() 
            
            # Continuous streaming matrix compression
            ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret:
                frame_bytes = buffer.tobytes()
                if self.display_queue.full():
                    try: self.display_queue.get_nowait()
                    except Exception: pass
                self.display_queue.put(frame_bytes)
            
            time.sleep(0.03) # Match raw video frame rate dynamics smoothly

        cap.release()

    def _ai_processing_loop(self):
        db = SessionLocal()
        
        while self.is_running:
            if self.raw_frame is None:
                time.sleep(0.01)
                continue
                
            processing_frame = self.raw_frame.copy()
            vehicles = vehicle_detector.detect(processing_frame)

            for obj in vehicles:
                v_bbox = obj["bbox"]
                v_type = obj["vehicle_type"]
                
                cropped_plate, plate_bbox = plate_detector.crop_plate(processing_frame, v_bbox)
                
                if cropped_plate is None or cropped_plate.size == 0:
                    vx1, vy1, vx2, vy2 = v_bbox
                    h, w, _ = processing_frame.shape
                    cropped_plate = processing_frame[max(0, vy1):min(h, vy2), max(0, vx1):min(w, vx2)]
                
                if cropped_plate is not None and cropped_plate.size > 0:
                    plate_text, ocr_conf = ocr_reader.extract_text(cropped_plate)
                    
                    if plate_text and ocr_conf > 0.35:
                        current_time = time.time()
                        if plate_text not in self.recently_detected or (current_time - self.recently_detected[plate_text] > 15):
                            try:
                                crud.create_detection(
                                    db=db, camera_id="CAM_MAIN_ENTRY",
                                    plate_number=plate_text, vehicle_type=v_type,
                                    confidence=float(ocr_conf),
                                    evidence_url=f"/evidence/{plate_text}_{int(current_time)}.jpg"
                                )
                                logger.info(f"💾 [DB CAPTURE - EASYOCR] Plate: {plate_text} | Conf: {ocr_conf:.2f}")
                                self.recently_detected[plate_text] = current_time
                            except Exception as db_err:
                                logger.error(f"PostgreSQL Thread write error: {db_err}")
                                
            time.sleep(0.1) # Save CPU hardware execution spinlock cycles
            
        db.close()

    def stop(self):
        if not self.is_running:
            return {"status": "Camera stream stopped"}
        self.is_running = False
        while not self.display_queue.empty():
            try: self.display_queue.get_nowait()
            except Exception: pass
        return {"status": "Camera stream stopped"}

    def get_frame_generator(self):
        while self.is_running:
            if not self.display_queue.empty():
                frame_bytes = self.display_queue.get()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                time.sleep(0.005)

video_streamer = RTSPCameraStreamer()
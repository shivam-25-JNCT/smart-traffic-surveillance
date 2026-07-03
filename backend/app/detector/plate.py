import logging
from ultralytics import YOLO
import cv2
import os


logger = logging.getLogger("traffic-anpr")

class PlateDetector:
    def __init__(self):
        self.model_path = "weights/license_plate_detector.pt"
        self.model = None
        

    def load_model(self):
        if self.model is None:
            try:
                self.model = YOLO(self.model_path)
                logger.info("✅ Custom License Plate Detector Loaded!")
            except Exception:
                logger.warning("⚠️ Custom weights file missing in weights/ directory. Activating Fallback Parser...")
                # Global anchor fallback initialization
                self.model = YOLO("yolov8n.pt") 
    print(os.path.exists("weights/license_plate_detector.pt"))
    def crop_plate(self, frame, vehicle_bbox):
        if self.model is None:
            self.load_model()

        vx1, vy1, vx2, vy2 = vehicle_bbox
        h, w, _ = frame.shape
        
        vx1, vy1 = max(0, vx1), max(0, vy1)
        vx2, vy2 = min(w, vx2), min(h, vy2)
        
        vehicle_roi = frame[vy1:vy2, vx1:vx2]
        if vehicle_roi.size == 0:
            return None, None

        # Agar fallback nano chal raha h, toh threshold lower (conf=0.15) karna hoga 
        # taaki choti plates bhi scan me pakad me aayein
        is_fallback = self.model.overrides.get('model') == 'yolov8n.pt'
        confidence_threshold = 0.15 if is_fallback else 0.30

        results = self.model(vehicle_roi, verbose=False, conf=confidence_threshold)[0]
        
        for box in results.boxes:
            px1, py1, px2, py2 = box.xyxy[0].cpu().numpy().astype(int)
            global_plate_bbox = [vx1 + px1, vy1 + py1, vx1 + px2, vx1 + py2]
            
            cropped_plate = frame[global_plate_bbox[1]:global_plate_bbox[3], global_plate_bbox[0]:global_plate_bbox[2]]
            return cropped_plate, global_plate_bbox
            
        return None, None

plate_detector = PlateDetector()
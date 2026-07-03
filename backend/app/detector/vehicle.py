import logging
from ultralytics import YOLO
import numpy
logger = logging.getLogger("traffic-anpr")

class VehicleDetector:
    def __init__(self):
        # YOLOv8 Nano model - Fast aur lightweight hai live RTSP processing ke liye
        self.model_path = "weights/yolov8n.pt"
        self.model = None

    def load_model(self):
        
        if self.model is None:
            try:
                logger.info(f"Loading YOLOv8 Vehicle Detector ({self.model_path})...")
                self.model = YOLO(self.model_path)
                logger.info("✅ YOLOv8 Vehicle Detector loaded successfully!")
            except Exception as e:
                logger.error(f"❌ Failed to load YOLOv8 model: {e}")
                raise e

    def detect(self, frame):
        """
        Live RTSP frame me se target vehicles detect karne ka function.
        Returns: Detections metadata list bounding boxes ke sath.
        """
        if self.model is None:
            self.load_model()

        # COCO Dataset Classes: 2: car, 3: motorcycle, 5: bus, 7: truck
        target_classes = [2, 3, 5, 7]
        
        # Inference Run (conf=0.45 matlab 45% sure hone par hi filter karega)
        results = self.model(frame, verbose=False,imgsz=640, conf=0.45)[0]
        
        detections = []
        
        for box in results.boxes:
            class_id = int(box.cls[0])
            
            if class_id in target_classes:
                # Bounding box coordinates [x1, y1, x2, y2]
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                confidence = float(box.conf[0])
                label = results.names[class_id]
                
                detections.append({
                    "bbox": xyxy.tolist(),  # [x1, y1, x2, y2]
                    "confidence": confidence,
                    "vehicle_type": label
                })
                
        return detections

# Global module footprint architecture instance
vehicle_detector = VehicleDetector()
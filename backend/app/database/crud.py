from sqlalchemy.orm import Session
from app.database import models
from datetime import datetime

def get_all_detections(db: Session, skip: int = 0, limit: int = 100):
    """
    Database se saare logs ulte order (latest first) me nikalta h.
    Skip aur Limit pagination ke liye h taaki dashboard slow na ho.
    """
    return (
        db.query(models.DetectionLog)
        .order_by(models.DetectionLog.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_detections_by_id(db: Session, detection_id: int):
    """Specific ID se pure data row ko fetch karta h."""
    return db.query(models.DetectionLog).filter(models.DetectionLog.id == detection_id).first()

def search_plate(db: Session, plate_text: str):
    """
    SQL LIKE query chalata h. Agar plate me partial word bhi match hua 
    (jaise sirf 'DL'), toh bhi saare results de dega.
    """
    return (
        db.query(models.DetectionLog)
        .filter(models.DetectionLog.plate_number.contains(plate_text.upper()))
        .all()
    )

def get_statistics(db: Session):
    """
    Real-time aggregation query dashboard ke metrics update rakhne ke liye.
    """
    total = db.query(models.DetectionLog).count()
    
    # Direct database counts grouped by type
    cars = db.query(models.DetectionLog).filter(models.DetectionLog.vehicle_type == "car").count()
    bikes = db.query(models.DetectionLog).filter(models.DetectionLog.vehicle_type == "bike").count()
    trucks = db.query(models.DetectionLog).filter(models.DetectionLog.vehicle_type == "truck").count()
    
    return {
        "total_detections": total,
        "today_count": total,  # Aage jaakar isme date check filter jodenge
        "vehicle_breakdown": {
            "cars": cars,
            "bikes": bikes,
            "trucks": trucks,
            "others": total - (cars + bikes + trucks)
        }
    }

def create_detection(db: Session, camera_id: str, plate_number: str, vehicle_type: str, confidence: float, evidence_url: str):
    """
    [NEW Stage Function]: Jab AI model successfully text nikal lega, 
    tab ye entry database table me permanently write karega.
    """
    db_log = models.DetectionLog(
        camera_id=camera_id,
        plate_number=plate_number.upper(),
        vehicle_type=vehicle_type,
        confidence=confidence,
        evidence_url=evidence_url,
        timestamp=datetime.utcnow()
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log
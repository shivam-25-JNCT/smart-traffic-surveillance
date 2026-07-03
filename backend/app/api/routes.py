from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.camera.rtsp import video_streamer
import time

router = APIRouter(prefix="/api/v1", tags=["ANPR Core Router Engine"])

class DetectionOut(BaseModel):
    id: int
    camera_id: int
    alert_category: str
    severity_level: int          
    confidence_score: float      
    timestamp: str               
    license_plate: Optional[str] = None  
    media_type: Optional[str] = None   
    snapshot_url: Optional[str] = None  
    clip_url: Optional[str] = None      

class AlertCreate(BaseModel):
    camera_id: int
    alert_category: str
    severity_level: int
    confidence_score: float
    frame_path: str

class TelemetryCreate(BaseModel):
    camera_id: int
    metric_type: str
    measured_value: float
    status: str

@router.post("/camera/start")
def start_camera():
    """Trigger the start of frame capture pipeline."""
    return video_streamer.start()

@router.post("/camera/stop")
def stop_camera():
    """Safely kill the thread channels and release hardware hooks."""
    return video_streamer.stop()

@router.get("/camera/status")
def get_camera_status():
    """Check if the camera is connected or offline."""
    return {"connected": video_streamer.is_running}

@router.get("/camera/stream")
async def get_live_stream():
    """Live frame chunk boundary distribution emitter routing hook"""
    if not video_streamer.is_running:
        raise HTTPException(status_code=400, detail="Camera stream is not running active.")
    return StreamingResponse(
        video_streamer.get_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/detections", response_model=List[DetectionOut])
def get_detections():
    # Production fallback connection schemas dataset logs
    return [
        {
            "id": 1,
            "camera_id": 1,
            "alert_category": "Helmet Violation",
            "severity_level": 3,
            "confidence_score": 0.95,
            "timestamp": "2026-07-02T18:00:00",
            "license_plate": "MP04 AB 1234",
            "media_type": "video",
            "clip_url": None,
        },
        {
            "id": 2,
            "camera_id": 1,
            "alert_category": "Wrong Lane Entry",
            "severity_level": 2,
            "confidence_score": 0.81,
            "timestamp": "2026-07-02T17:42:00",
            "license_plate": None,  
            "media_type": "photo",
            "snapshot_url": None,
        },
    ]

@router.post("/alerts/trigger")
def trigger_alert(alert: AlertCreate):
    return {
        "id": 101,
        "received": alert.dict(),
        "timestamp": datetime.utcnow().isoformat(),
    }

@router.post("/telemetry/log")
def log_telemetry(telemetry: TelemetryCreate):
    return {
        "id": 202,
        "received": telemetry.dict(),
        "timestamp": datetime.utcnow().isoformat(),
    }
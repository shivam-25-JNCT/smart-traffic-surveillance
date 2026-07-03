import logging
from app.database import crud
from app.camera.rtsp import video_streamer
from sqlalchemy.orm import Session

CAMERA_RUNNING = False
logger = logging.getLogger("traffic-anpr")

def backend_status():
    
    return {
        "status": "Backend Running",
        "database_connected": True,
        "streamer_initialized": True
    }

def start_camera():
    # Yahan OpenCV ya RTSP ka thread start karne ka logic aayega
    global CAMERA_RUNNING
    CAMERA_RUNNING=True
    return video_streamer.start()

def stop_camera():
    # Yahan RTSP stream thread ko kill karne ka logic aayega
    global CAMERA_RUNNING
    CAMERA_RUNNING=False
    logger.info("Service Layer: Triggering RTSP stream startup...")
    return video_streamer.stop()

def camera_status():
    # Active camera thread check karne ka logic
    status_str = "Running" if video_streamer.is_running else "Stopped"

    return {"camera": status_str, 
            "fps": 30 if video_streamer.is_running else 0,
            "source":str(video_streamer.stream_source)
            }
def get_stream_generator():
    
    return video_streamer.get_frame_generator()

def get_all_detections(db:Session):
    # Database se saari entries fetch hongi yahan se
    return crud.get_all_detections(db)

def get_detection_by_id(db:Session,detection_id: int):
    # Database se single record query hoga
    return crud.get_detections_by_id(db,detection_id)

def search_plate(db: Session,plate: str):
    # DB me LIKE query chalegi: WHERE plate LIKE '%XYZ%'
    return crud.search_plate(db,plate)

def statistics(db:Session):
    # Charts ke liye aggregations (COUNT queries)
    return crud.get_statistics(db)
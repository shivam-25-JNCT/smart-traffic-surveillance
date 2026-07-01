from fastapi import APIRouter
from app.services import anpr_service
router=APIRouter()

@router.get("/status")
def status():
    return {
        "statys":"backend Running"
    }

# home
@router.get("/")
def home():
    return {
        "message": "Smart Traffic Surveillance Backend Running"
    }
# backend status
@router.get("/status")
def backend_status():
    return anpr_service.backend_status()


@router.post("/camera/start")
def start_camera():
    return anpr_service.start_camera()


@router.post("/camera/stop")
def stop_camera():
    return anpr_service.stop_camera()


@router.get("/camera/status")
def camera_status():
    return anpr_service.camera_status()


@router.get("/detections")
def get_detection():
    return anpr_service.get_detection


@router.get("/detections/{detection_id}")
def get_detection(detection_id:int):
    return anpr_service.get_all_detections(detection_id)

@router.get("/search")
def search_plate(plate: str):
    return anpr_service.search_plate(plate)

@router.get("/statistics")
def statistics():
    return anpr_service.statistics()
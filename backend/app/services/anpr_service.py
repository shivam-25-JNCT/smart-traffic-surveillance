from fastapi import FastAPI

app=FastAPI(
    title="Smart Trafic Survelliance System",
    description="Backend APIs for ANPR System",
    version="1.0.0"
)



def backend_status():
    return {"status": "Backend Running"}


def start_camera():
    return {"message": "Camera Started"}


def stop_camera():
    return {"message": "Camera Stopped"}


def camera_status():
    return {"camera": "Stopped"}


def get_all_detections():
    return []


def get_detection(detection_id):
    return {
        "id": detection_id
    }


def search_plate(plate):
    return {
        "plate": plate
    }


def statistics():
    return {
        "total_detections": 0,
        "today": 0
    }
from datetime import datetime

from pydantic import BaseModel


class DetectionResponse(BaseModel):
    id: int
    vehicle_type: str
    plate_number: str
    confidence: float
    timestamp: datetime
    image_path: str
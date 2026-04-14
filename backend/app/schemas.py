from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: int
    name: str
    upload_time: datetime
    status: str
    processed_video_url: Optional[str] = None
    stream_url: str
    error_message: Optional[str] = None
    unique_person_count: Optional[int] = None

    class Config:
        from_attributes = True


class DetectionResponse(BaseModel):
    frame_id: int
    timestamp: float
    object_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    class Config:
        from_attributes = True

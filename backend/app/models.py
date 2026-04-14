from sqlalchemy import BIGINT, DOUBLE_PRECISION, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    upload_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String, nullable=False, default="uploaded")
    processed_video_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    unique_person_count = Column(Integer, nullable=True)  # confirmed unique people via tracking

    detections = relationship("Detection", back_populates="video", cascade="all, delete-orphan")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(BIGINT, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    frame_id = Column(Integer, nullable=False)
    timestamp = Column(DOUBLE_PRECISION, nullable=False)
    object_name = Column(String, nullable=False, index=True)
    confidence = Column(DOUBLE_PRECISION, nullable=False)
    x1 = Column(DOUBLE_PRECISION, nullable=False)
    y1 = Column(DOUBLE_PRECISION, nullable=False)
    x2 = Column(DOUBLE_PRECISION, nullable=False)
    y2 = Column(DOUBLE_PRECISION, nullable=False)
    track_id = Column(Integer, nullable=True, index=True)  # YOLOv8 tracker ID

    video = relationship("Video", back_populates="detections")

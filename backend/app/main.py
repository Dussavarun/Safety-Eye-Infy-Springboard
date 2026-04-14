import os
import shutil
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db, SessionLocal
from app.models import Detection, Video
from app.schemas import DetectionResponse, VideoResponse
from app.video_processor import frame_stream_generator, process_video

app = FastAPI(title="Model-Agnostic Video Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
Path(settings.processed_dir).mkdir(parents=True, exist_ok=True)

# Reset any videos left in 'processing' from a previous crashed/stopped run
_startup_db = SessionLocal()
try:
    _startup_db.query(Video).filter(Video.status == "processing").update(
        {"status": "failed", "error_message": "Interrupted: server restarted during processing. Please re-upload."},
        synchronize_session=False,
    )
    _startup_db.commit()
finally:
    _startup_db.close()


def to_video_response(video: Video) -> VideoResponse:
    processed_video_url = f"/videos/{video.id}/processed" if video.processed_video_path else None
    return VideoResponse(
        id=video.id,
        name=video.name,
        upload_time=video.upload_time,
        status=video.status,
        processed_video_url=processed_video_url,
        stream_url=f"/videos/{video.id}/stream",
        error_message=video.error_message,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/videos/upload", response_model=VideoResponse)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    video = Video(name=file.filename, status="uploaded")
    db.add(video)
    db.commit()
    db.refresh(video)

    ext = Path(file.filename).suffix or ".mp4"
    upload_path = os.path.join(settings.uploads_dir, f"{video.id}{ext}")
    output_path = os.path.join(settings.processed_dir, f"{video.id}_processed.mp4")

    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    background_tasks.add_task(process_video, video.id, upload_path, output_path)
    return to_video_response(video)


@app.get("/videos", response_model=list[VideoResponse])
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.upload_time.desc()).all()
    return [to_video_response(video) for video in videos]


@app.get("/videos/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="Video not found.")
    return to_video_response(video)


@app.get("/videos/{video_id}/detections", response_model=list[DetectionResponse])
def list_detections(video_id: int, db: Session = Depends(get_db)):
    rows = db.query(Detection).filter(Detection.video_id == video_id).all()
    return rows


@app.get("/videos/{video_id}/stream")
def stream_video_preview(video_id: int):
    return StreamingResponse(
        frame_stream_generator(video_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/videos/{video_id}/processed")
def get_processed_video(video_id: int, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video or not video.processed_video_path:
        raise HTTPException(status_code=404, detail="Processed video not found.")
    return FileResponse(video.processed_video_path, media_type="video/mp4")

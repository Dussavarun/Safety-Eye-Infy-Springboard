import os
import threading
from pathlib import Path
from typing import Dict, Optional

import cv2

from app.config import settings
from app.database import SessionLocal
from app.detector import ObjectDetector
from app.models import Detection, Video


class PreviewStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frames: Dict[int, bytes] = {}
        self._seq: Dict[int, int] = {}

    def set_frame(self, video_id: int, frame_bytes: bytes) -> None:
        with self._lock:
            self._frames[video_id] = frame_bytes
            self._seq[video_id] = self._seq.get(video_id, 0) + 1

    def get_frame(self, video_id: int) -> tuple[Optional[bytes], int]:
        with self._lock:
            return self._frames.get(video_id), self._seq.get(video_id, 0)

    def clear(self, video_id: int) -> None:
        with self._lock:
            self._frames.pop(video_id, None)
            self._seq.pop(video_id, None)


preview_store = PreviewStore()
detector = ObjectDetector()


def process_video(video_id: int, input_path: str, output_path: str) -> None:
    db = SessionLocal()
    cap = cv2.VideoCapture(input_path)
    video = db.get(Video, video_id)

    if not cap.isOpened() or video is None:
        if video:
            video.status = "failed"
            video.error_message = "Unable to read uploaded video."
            db.commit()
        db.close()
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    Path(os.path.dirname(output_path)).mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    video.status = "processing"
    db.commit()

    frame_id = 0
    # Run inference every N frames — 8 = good balance of speed vs coverage at 30fps
    inference_every = 8
    # Update MJPEG preview every N frames
    preview_every = 4
    pending_detections: list[Detection] = []
    last_detections: list = []  # carry forward last known boxes for preview overlay

    # --- Tracking state (person counting) ---
    # track_id → how many inference frames this ID has been seen
    track_history: dict[int, int] = {}
    # track IDs confirmed stable (seen >= STABILITY_THRESHOLD frames)
    confirmed_ids: set[int] = set()
    STABILITY_THRESHOLD = 5  # must appear in 5 inference frames before counting

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            timestamp = frame_id / fps
            is_inference_frame = (frame_id % inference_every == 0)
            if is_inference_frame:
                # Use track() so YOLOv8 assigns persistent IDs across frames
                last_detections = detector.track(frame)

                # --- Update tracking state for person counting ---
                for det in last_detections:
                    if detector.get_object_name(det.class_id).lower() != "person":
                        continue
                    tid = det.track_id
                    if tid is None:
                        continue
                    track_history[tid] = track_history.get(tid, 0) + 1
                    if track_history[tid] >= STABILITY_THRESHOLD:
                        confirmed_ids.add(tid)

            for detection in last_detections:
                x1, y1, x2, y2 = detection.bbox
                object_name = detector.get_object_name(detection.class_id)
                label = f"{object_name} {detection.confidence:.2f}"
                # Show track ID on person boxes
                if detection.track_id is not None and object_name.lower() == "person":
                    label = f"Person#{detection.track_id} {detection.confidence:.2f}"
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (10, 220, 90), 2)
                cv2.putText(
                    frame,
                    label,
                    (int(x1), max(20, int(y1) - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (10, 220, 90),
                    2,
                    cv2.LINE_AA,
                )
                # Only write to DB on inference frames — not on every carried-forward frame
                if is_inference_frame:
                    pending_detections.append(
                        Detection(
                            video_id=video_id,
                            frame_id=frame_id,
                            timestamp=float(timestamp),
                            object_name=object_name,
                            confidence=float(detection.confidence),
                            x1=float(x1),
                            y1=float(y1),
                            x2=float(x2),
                            y2=float(y2),
                            track_id=detection.track_id,
                        )
                    )

            writer.write(frame)

            # Only encode JPEG for preview on select frames
            if frame_id % preview_every == 0:
                ok_jpg, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok_jpg:
                    preview_store.set_frame(video_id, buffer.tobytes())
            # Batch-insert detections every 30 frames
            if frame_id % 30 == 0 and pending_detections:
                db.add_all(pending_detections)
                db.commit()
                pending_detections.clear()

            frame_id += 1

        # Flush remaining detections
        if pending_detections:
            db.add_all(pending_detections)
            db.commit()
            pending_detections.clear()

        video.status = "completed"
        video.processed_video_path = output_path
        video.unique_person_count = len(confirmed_ids)
        db.commit()
    except Exception as exc:
        video.status = "failed"
        video.error_message = str(exc)
        db.commit()
    finally:
        cap.release()
        writer.release()
        db.close()
        preview_store.clear(video_id)


def frame_stream_generator(video_id: int):
    import time

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video is None:
            return
    finally:
        db.close()

    last_seq = -1
    idle_ticks = 0
    max_idle = 60  # ~6 s of no new frames after processing ends → close stream

    while True:
        frame, seq = preview_store.get_frame(video_id)
        if frame is not None and seq != last_seq:
            last_seq = seq
            idle_ticks = 0
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        else:
            idle_ticks += 1
            if idle_ticks % 30 == 0:
                db = SessionLocal()
                try:
                    v = db.get(Video, video_id)
                    if v and v.status in ("completed", "failed") and idle_ticks >= max_idle:
                        break
                finally:
                    db.close()
        time.sleep(0.1)

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import onnxruntime as ort
import yaml
from ultralytics import YOLO

from app.config import settings


@dataclass
class DetectionItem:
    class_id: int
    confidence: float
    bbox: List[float]
    track_id: Optional[int] = None


class ObjectDetector:
    def __init__(self) -> None:
        self.model_type = settings.model_type.lower()
        self.class_map = self._load_class_map()
        # Use 320 for faster CPU inference — good enough for PPE detection
        self.input_size = 320

        if self.model_type == "onnx":
            if not Path(settings.model_path).exists():
                raise FileNotFoundError(
                    f"Model file not found: {settings.model_path}\n"
                    "Ensure the models/ folder is present and MODEL_PATH is correct in .env"
                )
            self.session = ort.InferenceSession(
                settings.model_path, providers=["CPUExecutionProvider"]
            )
            model_meta = self.session.get_modelmeta().custom_metadata_map
            self._merge_model_meta_classes(model_meta)
        elif self.model_type == "ultralytics":
            if not Path(settings.model_path).exists():
                raise FileNotFoundError(
                    f"Model file not found: {settings.model_path}\n"
                    "Ensure the models/ folder is present and MODEL_PATH is correct in .env"
                )
            self.model = YOLO(settings.model_path)
            model_names = getattr(self.model, "names", {}) or {}
            self._merge_names_dict(model_names)
            # Warm up the model with a dummy frame so the first real inference is instant
            import numpy as _np
            _dummy = _np.zeros((self.input_size, self.input_size, 3), dtype=_np.uint8)
            self.model.predict(source=_dummy, imgsz=self.input_size, device="cpu", verbose=False)
        else:
            raise ValueError("MODEL_TYPE must be 'onnx' or 'ultralytics'")

    def _load_class_map(self) -> Dict[int, str]:
        class_map_path = Path(settings.class_map_path)
        if not class_map_path.exists():
            return {}

        with class_map_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        names = data.get("names", data)
        if isinstance(names, list):
            return {idx: value for idx, value in enumerate(names)}
        if isinstance(names, dict):
            return {int(key): value for key, value in names.items()}
        return {}

    def _merge_model_meta_classes(self, metadata: Dict[str, str]) -> None:
        names_raw = metadata.get("names")
        if not names_raw:
            return
        try:
            parsed = ast.literal_eval(names_raw)
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    self.class_map[int(key)] = str(value)
        except (ValueError, SyntaxError):
            return
    
    def _merge_names_dict(self, names: Dict[int, str]) -> None:
        for key, value in names.items():
            self.class_map[int(key)] = str(value)

    def get_object_name(self, class_id: int) -> str:
        return self.class_map.get(class_id, f"class_{class_id}")

    def detect(self, frame: np.ndarray) -> List[DetectionItem]:
        if self.model_type == "onnx":
            return self._detect_onnx(frame)
        return self._detect_ultralytics(frame)

    def track(self, frame: np.ndarray) -> List[DetectionItem]:
        """
        Run YOLOv8 tracking (persist=True keeps IDs across frames).
        Falls back to plain detect() for ONNX models.
        """
        if self.model_type != "ultralytics":
            return self.detect(frame)

        results = self.model.track(
            source=frame,
            conf=settings.confidence_threshold,
            iou=settings.nms_threshold,
            persist=True,          # maintain track IDs across calls
            verbose=False,
            imgsz=self.input_size,
            device="cpu",
        )
        if not results:
            return []

        detections: List[DetectionItem] = []
        boxes = results[0].boxes
        if boxes is None:
            return detections

        xyxy     = boxes.xyxy.cpu().numpy()  if boxes.xyxy  is not None else []
        confs    = boxes.conf.cpu().numpy()  if boxes.conf  is not None else []
        class_ids = boxes.cls.cpu().numpy() if boxes.cls   is not None else []
        # track IDs are None when tracker hasn't assigned yet
        ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else [None] * len(confs)

        for bbox, conf, class_id, tid in zip(xyxy, confs, class_ids, ids):
            x1, y1, x2, y2 = bbox.tolist()
            detections.append(DetectionItem(
                class_id=int(class_id),
                confidence=float(conf),
                bbox=[float(x1), float(y1), float(x2), float(y2)],
                track_id=int(tid) if tid is not None else None,
            ))
        return detections

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        resized = cv2.resize(frame, self.input_size)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        return np.expand_dims(transposed, axis=0)

    def _detect_onnx(self, frame: np.ndarray) -> List[DetectionItem]:
        input_tensor = self._preprocess(frame)
        input_name = self.session.get_inputs()[0].name
        raw_outputs = self.session.run(None, {input_name: input_tensor})
        return self._postprocess_generic(raw_outputs, frame.shape)

    def _detect_ultralytics(self, frame: np.ndarray) -> List[DetectionItem]:
        results = self.model.predict(
            source=frame,
            conf=settings.confidence_threshold,
            iou=settings.nms_threshold,
            verbose=False,
            imgsz=self.input_size,
            device="cpu",
        )
        if not results:
            return []

        detections: List[DetectionItem] = []
        boxes = results[0].boxes
        if boxes is None:
            return detections

        xyxy = boxes.xyxy.cpu().numpy() if boxes.xyxy is not None else []
        confs = boxes.conf.cpu().numpy() if boxes.conf is not None else []
        class_ids = boxes.cls.cpu().numpy() if boxes.cls is not None else []
        for bbox, conf, class_id in zip(xyxy, confs, class_ids):
            x1, y1, x2, y2 = bbox.tolist()
            detections.append(
                DetectionItem(
                    class_id=int(class_id),
                    confidence=float(conf),
                    bbox=[float(x1), float(y1), float(x2), float(y2)],
                )
            )
        return detections

    def _postprocess_generic(self, raw_outputs, frame_shape) -> List[DetectionItem]:
        """
        Generic parser for outputs shaped like Nx6:
        [x1, y1, x2, y2, confidence, class_id]
        """
        if not raw_outputs:
            return []

        output = np.array(raw_outputs[0]).squeeze()
        if output.size == 0:
            return []
        if output.ndim == 1:
            output = np.expand_dims(output, axis=0)

        height, width = frame_shape[:2]
        detections: List[DetectionItem] = []
        for row in output:
            if len(row) < 6:
                continue
            x1, y1, x2, y2, conf, class_id = row[:6]
            if float(conf) < settings.confidence_threshold:
                continue
            detections.append(
                DetectionItem(
                    class_id=int(class_id),
                    confidence=float(conf),
                    bbox=[
                        float(np.clip(x1, 0, width)),
                        float(np.clip(y1, 0, height)),
                        float(np.clip(x2, 0, width)),
                        float(np.clip(y2, 0, height)),
                    ],
                )
            )
        return detections


# Imported lazily to avoid heavy import path at module top.
import cv2  # noqa: E402

# Safety-Eye Video Detection Platform

This project is a complete Dockerized stack for video object detection:

- FastAPI backend (video upload, frame processing, live preview stream)
- PostgreSQL (stores videos + detections)
- Grafana (dynamic dashboards from detection labels)
- React frontend (upload page, live page, dashboard embed)

The data flow is fully model-agnostic:

`model class_id -> object_name mapping -> DB object_name -> Grafana queries -> frontend`

No schema or dashboard hardcoding is required for new class labels.

## Project Structure

```text
.
├── backend
│   ├── app
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── detector.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── video_processor.py
│   ├── model_data/classes.yaml
│   ├── Dockerfile
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── pages
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── LiveDetectionPage.jsx
│   │   │   └── UploadPage.jsx
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
├── grafana
│   ├── dashboards/object-detection.json
│   └── provisioning
│       ├── dashboards/dashboards.yml
│       └── datasources/postgres.yml
├── sql/init.sql
├── docker-compose.yml
└── .env.example
```

## Main DashBoard

![Dashboard](https://raw.githubusercontent.com/Dussavarun/Safety-Eye-Infy-Springboard/main/frontend/images/b5ec828b-6ccd-4ed2-bcf2-ce6f576c2111.jpg)




## Backend API

- `POST /videos/upload` -> upload video and start async processing
- `GET /videos` -> list all videos and processing status
- `GET /videos/{video_id}` -> get one video status
- `GET /videos/{video_id}/detections` -> all detections for a video
- `GET /videos/{video_id}/stream` -> MJPEG live preview while processing
- `GET /videos/{video_id}/processed` -> processed MP4 with drawn labels

Each detection contains:

- `frame_id`
- `timestamp`
- `object_name` (dynamic)
- `confidence`
- `x1, y1, x2, y2`

## Database Schema

Defined in `sql/init.sql`:

- `videos (id, name, upload_time, status, processed_video_path, error_message)`
- `detections (id, video_id, frame_id, timestamp, object_name, confidence, x1, y1, x2, y2)`

`object_name` is `TEXT` and is not tied to fixed class columns.


## Grafana Dashboard (Dynamic)

Pre-provisioned dashboard: `Object Detection Overview`

Panels:

- Detections over time (grouped by object_name)
- Object count grouped by object_name
- Safety violations table (labels matching `no-%` or `%violation%`)

Embedded URL used by frontend:

`http://localhost:3001/d/detection-overview/object-detection-overview?orgId=1&refresh=5s&kiosk`

## Environment Setup

1. Copy env file:

```bash
cp .env.example .env
```

2. Update values if needed, especially:

- `MODEL_PATH` (default: `/models/best.pt`)
- `MODEL_TYPE` (`ultralytics` for `.pt`, or `onnx` for `.onnx`)
- `CLASS_MAP_PATH`

3. Place your model file in `./models` on host (for your case: `./models/best.pt`).

## Run Locally (One Command)

```bash
docker compose up --build
```

Backend uses CPU-only PyTorch (`torch==2.3.1+cpu`) to reduce image size and avoid CUDA wheel downloads.

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Grafana: `http://localhost:3001`
- PostgreSQL: `localhost:5432`

## How to Use

1. Open frontend Upload page.
2. Upload a video file.
3. Open Live Detection page:
   - See MJPEG processing preview while backend processes frames.
   - See processed MP4 once completed.
4. Open Dashboard page for embedded Grafana analytics.

## Notes on Adapting to Any Model

- `.pt` models are run with Ultralytics directly and class labels are read from `model.names`.
- `.onnx` models still use the generic parser in `backend/app/detector.py`.
- If a class is missing in mapping, it is saved as `class_<id>`.

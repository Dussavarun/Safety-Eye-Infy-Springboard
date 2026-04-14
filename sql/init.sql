CREATE TABLE IF NOT EXISTS videos (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  upload_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  status TEXT NOT NULL DEFAULT 'uploaded',
  processed_video_path TEXT,
  error_message TEXT,
  unique_person_count INTEGER
);

CREATE TABLE IF NOT EXISTS detections (
  id BIGSERIAL PRIMARY KEY,
  video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  frame_id INTEGER NOT NULL,
  timestamp DOUBLE PRECISION NOT NULL,
  object_name TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  x1 DOUBLE PRECISION NOT NULL,
  y1 DOUBLE PRECISION NOT NULL,
  x2 DOUBLE PRECISION NOT NULL,
  y2 DOUBLE PRECISION NOT NULL,
  track_id INTEGER
);

CREATE INDEX IF NOT EXISTS idx_detections_video_id ON detections(video_id);
CREATE INDEX IF NOT EXISTS idx_detections_object_name ON detections(object_name);
CREATE INDEX IF NOT EXISTS idx_detections_timestamp ON detections(timestamp);

CREATE OR REPLACE VIEW detection_events AS
SELECT
  d.id,
  d.video_id,
  d.frame_id,
  d.timestamp,
  d.object_name,
  d.confidence,
  d.x1,
  d.y1,
  d.x2,
  d.y2,
  v.upload_time + (d.timestamp * INTERVAL '1 second') AS event_time
FROM detections d
JOIN videos v ON v.id = d.video_id;

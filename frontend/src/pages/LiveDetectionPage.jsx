import { useEffect, useMemo, useState } from "react";
import { getDetections, getProcessedUrl, getStreamUrl } from "../api";
import { useAppState } from "../AppState";

export default function LiveDetectionPage() {
  const { videos, selectedVideoId, selectedVideo, setSelectedVideoId } = useAppState();
  const [detections, setDetections] = useState([]);
  const [error, setError] = useState("");
  const [streamTick, setStreamTick] = useState(0);

  useEffect(() => {
    if (!selectedVideoId) {
      setDetections([]);
      return;
    }
    const load = async () => {
      try {
        const rows = await getDetections(selectedVideoId);
        setDetections(rows);
      } catch (err) {
        setError(err.message);
      }
    };
    load();
    const interval = setInterval(load, 1500);
    return () => clearInterval(interval);
  }, [selectedVideoId]);

  useEffect(() => {
    if (selectedVideo?.status !== "processing") return;
    const interval = setInterval(() => setStreamTick((value) => value + 1), 5000);
    return () => clearInterval(interval);
  }, [selectedVideo?.status]);

  const streamUrl = useMemo(() => {
    if (!selectedVideoId) return "";
    return `${getStreamUrl(selectedVideoId)}?tick=${streamTick}`;
  }, [selectedVideoId, streamTick]);

  const status = selectedVideo?.status ?? "idle";
  const latestTimestamp = detections.length ? detections[detections.length - 1].timestamp.toFixed(2) : "0.00";

  return (
    <section>
      <h2 className="page-header">Live Detection</h2>
      <div className="card">
        <label htmlFor="videoSelector">Select uploaded video</label>
        <select
          id="videoSelector"
          value={selectedVideoId}
          onChange={(e) => {
            setSelectedVideoId(e.target.value);
            setDetections([]);
          }}
        >
          <option value="">-- Select video --</option>
          {videos.map((item) => (
            <option key={item.id} value={item.id}>
              #{item.id} - {item.name}
            </option>
          ))}
        </select>
      </div>

      {selectedVideoId && (
        <div className="grid">
          <div className="card">
            <h3>Processing Stream (MJPEG)</h3>
            <img src={streamUrl} alt="live stream preview" className="preview" />
            <p>Status: {status}</p>
            <p>Live detections: {detections.length}</p>
            <p>Last detection timestamp: {latestTimestamp}s</p>
          </div>
          <div className="card">
            <h3>Processed Video</h3>
            {selectedVideo?.status === "completed" ? (
              <video controls className="preview">
                <source src={getProcessedUrl(selectedVideoId)} type="video/mp4" />
              </video>
            ) : (
              <div className="placeholder">Processed video becomes available after processing completes.</div>
            )}
          </div>
        </div>
      )}

      {error && <p>{error}</p>}
    </section>
  );
}

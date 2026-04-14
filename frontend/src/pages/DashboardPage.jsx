import { useEffect, useMemo, useState } from "react";
import { useAppState } from "../AppState";
import StatCard from "../components/StatCard";
import { getDetections } from "../api";

const GRAFANA_IFRAME_URL =
  import.meta.env.VITE_GRAFANA_IFRAME_URL ||
  "http://localhost:3001/d/safety-eye-like/safety-eye-like-dashboard?orgId=1&refresh=5s&kiosk";

export default function DashboardPage() {
  const { selectedVideoId, selectedVideo } = useAppState();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    if (!selectedVideoId) {
      setRows([]);
      return;
    }
    const load = async () => {
      try {
        const detections = await getDetections(selectedVideoId);
        setRows(detections);
      } catch {
        setRows([]);
      }
    };
    load();
    const id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [selectedVideoId]);

  const uniqueLabels = new Set(rows.map((item) => item.object_name)).size;
  const violationCount = rows.filter((item) => item.object_name.toLowerCase().includes("no-") || item.object_name.toLowerCase().includes("violation")).length;

  const dashboardUrl = useMemo(() => {
    // Pass 0 when no video selected — matches allValue="0" in Grafana variable (shows all data)
    const vidParam = selectedVideoId || "0";
    const separator = GRAFANA_IFRAME_URL.includes("?") ? "&" : "?";
    return `${GRAFANA_IFRAME_URL}${separator}var-video_id=${vidParam}`;
  }, [selectedVideoId]);

  return (
    <section>
      <h2 className="page-header">Dashboard</h2>
      <div className="stat-grid">
        <StatCard label="Selected Video" value={selectedVideoId || "-"} sub={selectedVideo?.name || "No active video"} />
        <StatCard label="Detections" value={rows.length} sub="Live from backend" />
        <StatCard label="Violation Rows" value={violationCount} sub="no-* or violation labels" />
        <StatCard label="Unique Labels" value={uniqueLabels} sub="Model agnostic classes" />
      </div>
      <div className="card">
        <p>Auto-refresh is enabled every 5 seconds for near real-time updates.</p>
        <iframe
          src={dashboardUrl}
          title="Grafana Dashboard"
          className="grafana-frame"
          allowFullScreen
        />
      </div>
    </section>
  );
}

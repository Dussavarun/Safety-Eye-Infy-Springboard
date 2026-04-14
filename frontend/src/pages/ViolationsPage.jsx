import { useEffect, useMemo, useState } from "react";
import { getDetections } from "../api";
import { useAppState } from "../AppState";

export default function ViolationsPage() {
  const { selectedVideoId } = useAppState();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!selectedVideoId) {
      setRows([]);
      return;
    }
    const load = async () => {
      try {
        const detections = await getDetections(selectedVideoId);
        setRows(
          detections
            .filter((item) => item.object_name.toLowerCase().includes("no-") || item.object_name.toLowerCase().includes("violation"))
            .slice(-200)
            .reverse()
        );
      } catch (err) {
        setError(err.message);
      }
    };
    load();
    const id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [selectedVideoId]);

  const highCount = useMemo(() => rows.filter((item) => item.object_name.toLowerCase().includes("no-")).length, [rows]);

  return (
    <section>
      <h2 className="page-header">Violations</h2>
      {!selectedVideoId ? <p>Select a video from Live or Upload first.</p> : null}
      <div className="card">
        <p>Total active rows: {rows.length}</p>
        <p>Critical no-* labels: {highCount}</p>
      </div>
      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Frame</th>
              <th>Time (s)</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item, index) => (
              <tr key={`${item.frame_id}-${index}`}>
                <td>{item.object_name}</td>
                <td>{item.frame_id}</td>
                <td>{item.timestamp.toFixed(2)}</td>
                <td>{(item.confidence * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length ? <p>No violations in selected range.</p> : null}
      </div>
      {error ? <p>{error}</p> : null}
    </section>
  );
}

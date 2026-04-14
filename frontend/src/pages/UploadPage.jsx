import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadVideo } from "../api";
import { useAppState } from "../AppState";

export default function UploadPage() {
  const navigate = useNavigate();
  const { setSelectedVideoId, refreshVideos } = useAppState();
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    if (!file || loading) return;

    try {
      setLoading(true);
      const response = await uploadVideo(file);
      setSelectedVideoId(String(response.id));
      await refreshVideos();
      setMessage(`Uploaded video #${response.id}. Processing started.`);
      navigate("/live");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h2 className="page-header">Process Video</h2>
      <form onSubmit={onSubmit} className="card">
        <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button type="submit" disabled={!file || loading}>
          {loading ? "Uploading..." : "Upload and Process"}
        </button>
      </form>
      {message && <p>{message}</p>}
    </section>
  );
}

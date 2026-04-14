const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function uploadVideo(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE_URL}/videos/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function getVideos() {
  const res = await fetch(`${API_BASE_URL}/videos`);
  if (!res.ok) throw new Error("Failed to load videos");
  return res.json();
}

export async function getVideo(videoId) {
  const res = await fetch(`${API_BASE_URL}/videos/${videoId}`);
  if (!res.ok) throw new Error("Failed to load video");
  return res.json();
}

export async function getDetections(videoId) {
  const res = await fetch(`${API_BASE_URL}/videos/${videoId}/detections`);
  if (!res.ok) throw new Error("Failed to load detections");
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error("API is unavailable");
  return res.json();
}

export function getStreamUrl(videoId) {
  return `${API_BASE_URL}/videos/${videoId}/stream`;
}

export function getProcessedUrl(videoId) {
  return `${API_BASE_URL}/videos/${videoId}/processed`;
}

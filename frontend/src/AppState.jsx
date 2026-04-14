import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getVideo, getVideos } from "./api";

const AppStateContext = createContext(null);

const SELECTED_VIDEO_KEY = "selectedVideoId";

export function AppStateProvider({ children }) {
  const [videos, setVideos] = useState([]);
  const [selectedVideoId, setSelectedVideoId] = useState(() => localStorage.getItem(SELECTED_VIDEO_KEY) || "");
  const [selectedVideo, setSelectedVideo] = useState(null);

  async function refreshVideos() {
    const data = await getVideos();
    setVideos(data);
    return data;
  }

  async function refreshSelectedVideo(videoId = selectedVideoId) {
    if (!videoId) {
      setSelectedVideo(null);
      return null;
    }
    const data = await getVideo(videoId);
    setSelectedVideo(data);
    return data;
  }

  useEffect(() => {
    localStorage.setItem(SELECTED_VIDEO_KEY, selectedVideoId || "");
  }, [selectedVideoId]);

  useEffect(() => {
    refreshVideos().catch(() => {});
    const id = setInterval(() => {
      refreshVideos().catch(() => {});
    }, 4000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    refreshSelectedVideo(selectedVideoId).catch(() => {});
    if (!selectedVideoId) return;
    const id = setInterval(() => {
      refreshSelectedVideo(selectedVideoId).catch(() => {});
    }, 1500);
    return () => clearInterval(id);
  }, [selectedVideoId]);

  const value = useMemo(
    () => ({
      videos,
      selectedVideoId,
      selectedVideo,
      setSelectedVideoId,
      refreshVideos,
      refreshSelectedVideo,
    }),
    [videos, selectedVideoId, selectedVideo]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const value = useContext(AppStateContext);
  if (!value) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return value;
}

import { Route, Routes } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import DashboardPage from "./pages/DashboardPage";
import LiveDetectionPage from "./pages/LiveDetectionPage";
import UploadPage from "./pages/UploadPage";
import ViolationsPage from "./pages/ViolationsPage";

export default function App() {
  return (
    <div className="layout app-shell">
      <Sidebar />
      <main className="main app-main">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/live" element={<LiveDetectionPage />} />
          <Route path="/violations" element={<ViolationsPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
    </div>
  );
}

import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { healthCheck } from "../api";

const links = [
  { to: "/", label: "Dashboard", icon: "▦" },
  { to: "/upload", label: "Upload", icon: "↑" },
  { to: "/violations", label: "Violations", icon: "⚠" },
  { to: "/live", label: "Live", icon: "◉" },
];

export default function Sidebar() {
  const [apiOk, setApiOk] = useState(null);

  useEffect(() => {
    const ping = async () => {
      try {
        await healthCheck();
        setApiOk(true);
      } catch {
        setApiOk(false);
      }
    };
    ping();
    const id = setInterval(ping, 8000);
    return () => clearInterval(id);
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-title">Safety Eye</div>
        <div className="sidebar-subtitle">PPE Monitoring</div>
      </div>
      <nav className="sidebar-nav">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/"}
            className={({ isActive }) => (isActive ? "sidebar-link active" : "sidebar-link")}
          >
            <span>{link.icon}</span>
            {link.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-status">
        <span className={`dot ${apiOk === null ? "" : apiOk ? "ok" : "bad"}`} />
        API {apiOk === null ? "..." : apiOk ? "Online" : "Offline"}
      </div>
    </aside>
  );
}

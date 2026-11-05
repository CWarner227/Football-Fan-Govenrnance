import { NavLink, Route, Routes } from "react-router-dom";
import {
  Activity,
  ArrowLeftRight,
  BookOpen,
  FlaskConical,
  History as HistoryIcon,
  LayoutDashboard,
  Menu,
  Microscope,
  Plug,
  Settings as SettingsIcon,
  SlidersHorizontal,
} from "lucide-react";
import { useState } from "react";
import Builder from "./pages/Builder";
import Results from "./pages/Results";
import {
  Compare,
  History,
  Integrations,
  Overview,
  Scenarios,
  Settings,
} from "./pages/Workspace";
export const navigation = [
  { path: "/", label: "Overview", icon: LayoutDashboard },
  { path: "/builder", label: "Simulation Builder", icon: SlidersHorizontal },
  { path: "/scenarios", label: "Scenarios", icon: BookOpen },
  { path: "/experiments", label: "Experiments", icon: FlaskConical },
  { path: "/results", label: "Results Explorer", icon: Activity },
  { path: "/history", label: "Run History", icon: HistoryIcon },
  { path: "/compare", label: "Compare", icon: ArrowLeftRight },
  { path: "/integrations", label: "Integrations", icon: Plug },
  { path: "/settings", label: "Settings", icon: SettingsIcon },
];
export default function App() {
  const [open, setOpen] = useState(false);
  return (
    <div className="app-shell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <LinkBrand />
        <div className="sidebar-caption">RESEARCH WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ path, label, icon: Icon }) => (
            <NavLink
              end={path === "/"}
              key={path}
              to={path}
              onClick={() => setOpen(false)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="connection-dot" />
          Local research environment
          <small>Phase 3.5 · Simulation control center</small>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="mobile-menu subtle"
            aria-label="Toggle navigation"
            onClick={() => setOpen(!open)}
          >
            <Menu size={22} />
          </button>
          <div>
            <span className="muted">Workspace</span>
            <span className="divider">/</span>Football governance
          </div>
          <span className="local-badge">
            <span className="connection-dot" /> Local engine
          </span>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/builder" element={<Builder />} />
            <Route path="/scenarios" element={<Scenarios />} />
            <Route path="/experiments" element={<Builder experiment />} />
            <Route path="/results" element={<Results />} />
            <Route path="/results/:id" element={<Results />} />
            <Route path="/history" element={<History />} />
            <Route path="/compare" element={<Compare />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<p>Page not found.</p>} />
          </Routes>
        </main>
        <footer className="workspace-footer">
          FOOTBALL GOVERNANCE LAB{" "}
          <span>Research tools · Python simulation engine</span>
        </footer>
      </div>
    </div>
  );
}
function LinkBrand() {
  return (
    <div className="brand">
      <span className="brand-icon">
        <Microscope size={23} />
      </span>
      <div>
        Governance Lab<small>Football research platform</small>
      </div>
    </div>
  );
}

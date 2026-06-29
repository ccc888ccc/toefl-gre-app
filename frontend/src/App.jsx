import { useState, useEffect } from "react";
import { getToken, clearToken } from "./api.js";
import Login from "./components/Login.jsx";
import ReviewView from "./components/ReviewView.jsx";
import StatsView from "./components/StatsView.jsx";
import AddWordView from "./components/AddWordView.jsx";

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [tab, setTab] = useState("review");

  useEffect(() => {
    const onStorage = () => setAuthed(!!getToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  const logout = () => {
    clearToken();
    setAuthed(false);
  };

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">GRE 字彙 SRS</span>
        <button className="link" onClick={logout}>登出</button>
      </header>

      <main className="content">
        {tab === "review" && <ReviewView onAuthLost={logout} />}
        {tab === "stats" && <StatsView onAuthLost={logout} />}
        {tab === "add" && <AddWordView />}
      </main>

      <nav className="tabbar">
        <button className={tab === "review" ? "active" : ""} onClick={() => setTab("review")}>
          <span className="ico">📚</span>今日複習
        </button>
        <button className={tab === "stats" ? "active" : ""} onClick={() => setTab("stats")}>
          <span className="ico">📊</span>統計
        </button>
        <button className={tab === "add" ? "active" : ""} onClick={() => setTab("add")}>
          <span className="ico">➕</span>加生字
        </button>
      </nav>
    </div>
  );
}

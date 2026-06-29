import { useState, useEffect } from "react";
import { getToken, clearToken } from "./api.js";
import Login from "./components/Login.jsx";
import ReviewView from "./components/ReviewView.jsx";
import StatsView from "./components/StatsView.jsx";
import VocabView from "./components/VocabView.jsx";
import GraderView from "./components/GraderView.jsx";
import PracticeView from "./components/PracticeView.jsx";

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [tab, setTab] = useState("review");

  useEffect(() => {
    const onStorage = () => setAuthed(!!getToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  const logout = () => { clearToken(); setAuthed(false); };

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">GRE / TOEFL 衝刺</span>
        <button className="link" onClick={logout}>登出</button>
      </header>

      <main className="content">
        {tab === "review" && <ReviewView onAuthLost={logout} />}
        {tab === "vocab" && <VocabView />}
        {tab === "grader" && <GraderView onAuthLost={logout} />}
        {tab === "practice" && <PracticeView onAuthLost={logout} />}
        {tab === "stats" && <StatsView onAuthLost={logout} />}
      </main>

      <nav className="tabbar">
        <button className={tab === "review" ? "active" : ""} onClick={() => setTab("review")}>
          <span className="ico">📚</span>複習
        </button>
        <button className={tab === "vocab" ? "active" : ""} onClick={() => setTab("vocab")}>
          <span className="ico">📖</span>字庫
        </button>
        <button className={tab === "grader" ? "active" : ""} onClick={() => setTab("grader")}>
          <span className="ico">✍️</span>批改
        </button>
        <button className={tab === "practice" ? "active" : ""} onClick={() => setTab("practice")}>
          <span className="ico">🔍</span>檢討
        </button>
        <button className={tab === "stats" ? "active" : ""} onClick={() => setTab("stats")}>
          <span className="ico">📊</span>統計
        </button>
      </nav>
    </div>
  );
}

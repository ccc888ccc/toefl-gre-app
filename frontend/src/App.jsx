import { useState, useEffect } from "react";
import { api, getToken, clearToken } from "./api.js";
import Login from "./components/Login.jsx";
import StudyView from "./components/StudyView.jsx";
import StatsView from "./components/StatsView.jsx";
import VocabView from "./components/VocabView.jsx";
import GraderView from "./components/GraderView.jsx";
import PracticeView from "./components/PracticeView.jsx";
import AdminUsersView from "./components/AdminUsersView.jsx";

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const [me, setMe] = useState(null);       // { username, role } once loaded
  const [tab, setTab] = useState("review");

  // Load the current account (for role) whenever we're authed.
  useEffect(() => {
    let alive = true;
    if (!authed) { setMe(null); return; }
    api.me()
      .then((u) => { if (alive) setMe(u); })
      .catch(() => { clearToken(); if (alive) { setAuthed(false); setMe(null); } });
    return () => { alive = false; };
  }, [authed]);

  useEffect(() => {
    const onStorage = () => setAuthed(!!getToken());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;
  if (!me) return <div className="app"><div className="card center muted">載入中…</div></div>;

  const isAdmin = me.role === "admin";
  const logout = () => { clearToken(); setAuthed(false); setMe(null); setTab("review"); };

  // Guard: if a member ever lands on an admin-only tab, send them back.
  const adminTabs = new Set(["grader", "practice", "users"]);
  const activeTab = (!isAdmin && adminTabs.has(tab)) ? "review" : tab;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">GRE / TOEFL 衝刺</span>
        <span className="topbar-right">
          <span className="muted who">{me.username}{isAdmin ? "（管理員）" : ""}</span>
          <button className="link" onClick={logout}>登出</button>
        </span>
      </header>

      <main className="content">
        {activeTab === "review" && <StudyView onAuthLost={logout} />}
        {activeTab === "vocab" && <VocabView />}
        {activeTab === "stats" && <StatsView onAuthLost={logout} />}
        {isAdmin && activeTab === "grader" && <GraderView onAuthLost={logout} />}
        {isAdmin && activeTab === "practice" && <PracticeView onAuthLost={logout} />}
        {isAdmin && activeTab === "users" && <AdminUsersView />}
      </main>

      <nav className="tabbar">
        <button className={activeTab === "review" ? "active" : ""} onClick={() => setTab("review")}>
          <span className="ico">📚</span>背單字
        </button>
        <button className={activeTab === "vocab" ? "active" : ""} onClick={() => setTab("vocab")}>
          <span className="ico">📖</span>字庫
        </button>
        {isAdmin && (
          <button className={activeTab === "grader" ? "active" : ""} onClick={() => setTab("grader")}>
            <span className="ico">✍️</span>批改
          </button>
        )}
        {isAdmin && (
          <button className={activeTab === "practice" ? "active" : ""} onClick={() => setTab("practice")}>
            <span className="ico">🔍</span>檢討
          </button>
        )}
        <button className={activeTab === "stats" ? "active" : ""} onClick={() => setTab("stats")}>
          <span className="ico">📊</span>統計
        </button>
        {isAdmin && (
          <button className={activeTab === "users" ? "active" : ""} onClick={() => setTab("users")}>
            <span className="ico">👥</span>帳號
          </button>
        )}
      </nav>
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";
import { api } from "../api.js";

const SECTIONS = [{ k: "reading", label: "閱讀" }, { k: "listening", label: "聽力" }];

export default function PracticeView({ onAuthLost }) {
  const [section, setSection] = useState("reading");
  const [source, setSource] = useState("");
  const [qtext, setQtext] = useState("");
  const [qtype, setQtype] = useState("");
  const [userChoice, setUserChoice] = useState("");
  const [correctChoice, setCorrectChoice] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState([]);

  const loadStats = useCallback(() => { api.typeStats().then(setStats).catch(() => {}); }, []);
  useEffect(() => { loadStats(); }, [loadStats]);

  const submit = async (e) => {
    e.preventDefault();
    if (!qtext.trim()) { setErr("請貼上題目"); return; }
    setBusy(true); setErr("");
    try {
      const r = await api.practiceSubmit({
        section, source: source || null, question_text: qtext,
        question_type: qtype || null, user_choice: userChoice || null,
        correct_choice: correctChoice || null,
      });
      setResult(r); loadStats();
    } catch (e) {
      setErr(e.message);
      if (/登入/.test(e.message)) onAuthLost?.();
    } finally { setBusy(false); }
  };

  if (busy) {
    return (
      <div className="card center grading">
        <div className="spinner" />
        <p>檢討中… Claude 正在解析這題</p>
      </div>
    );
  }

  if (result) {
    const ex = result.explanation || {};
    return (
      <div className="result">
        <div className="card score-card">
          <div className={`pc-flag ${result.is_correct === null ? "" : result.is_correct ? "ok" : "no"}`}>
            {result.is_correct === null ? "—" : result.is_correct ? "答對" : "答錯"}
          </div>
          <div className="muted">
            {section === "reading" ? "閱讀" : "聽力"}{result.question_type ? ` · ${result.question_type}` : ""}
          </div>
        </div>
        {ex.summary_zh && <div className="card"><h3>重點</h3><p className="summary">{ex.summary_zh}</p></div>}
        {ex.why_correct_zh && <div className="card"><h3>為何正解對</h3><p className="summary">{ex.why_correct_zh}</p></div>}
        {ex.why_wrong_zh && <div className="card"><h3>為何你的選項錯</h3><p className="summary">{ex.why_wrong_zh}</p></div>}
        {ex.type_strategy_zh && <div className="card"><h3>題型策略</h3><p className="summary">{ex.type_strategy_zh}</p></div>}
        <button className="primary" onClick={() => setResult(null)}>檢討下一題</button>
      </div>
    );
  }

  return (
    <div className="practice">
      {stats.length > 0 && (
        <div className="card">
          <h3>題型正確率（最弱在前）</h3>
          {stats.map((s) => (
            <div className="dim" key={s.question_type}>
              <div className="dim-top">
                <span>{s.question_type}</span>
                <span>{Math.round(s.accuracy * 100)}%（{s.correct}/{s.total}）</span>
              </div>
              <div className="dim-track"><div className="dim-fill" style={{ width: `${s.accuracy * 100}%` }} /></div>
            </div>
          ))}
        </div>
      )}

      <form className="card" onSubmit={submit}>
        <h3>閱讀 / 聽力錯題檢討</h3>
        <label className="fld-label">Section</label>
        <div className="segmented">
          {SECTIONS.map((s) => (
            <button type="button" key={s.k} className={section === s.k ? "on" : ""} onClick={() => setSection(s.k)}>{s.label}</button>
          ))}
        </div>
        <label className="fld-label">題目</label>
        <textarea className="taller" placeholder="貼上題目(可含選項)" value={qtext} onChange={(e) => setQtext(e.target.value)} />
        <label className="fld-label">題型</label>
        <input placeholder="如 推論題 / 主旨題 / 細節題" value={qtype} onChange={(e) => setQtype(e.target.value)} />
        <div className="two-col">
          <div>
            <label className="fld-label">你的選擇</label>
            <input placeholder="如 B" value={userChoice} onChange={(e) => setUserChoice(e.target.value)} />
          </div>
          <div>
            <label className="fld-label">正確答案</label>
            <input placeholder="如 C" value={correctChoice} onChange={(e) => setCorrectChoice(e.target.value)} />
          </div>
        </div>
        <label className="fld-label">來源(選填)</label>
        <input placeholder="如 學而思 set 12" value={source} onChange={(e) => setSource(e.target.value)} />
        {err && <div className="error">{err}</div>}
        <button className="primary">送出檢討</button>
      </form>
    </div>
  );
}

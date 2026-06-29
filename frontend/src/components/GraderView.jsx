import { useState, useEffect, useCallback } from "react";
import { api } from "../api.js";

function scaleMax(taskTypes, key) {
  const t = taskTypes.find((x) => x.key === key);
  if (!t) return 5;
  const m = /(\d+)\s*$/.exec(t.scale || "");
  return m ? Number(m[1]) : 5;
}

const DIM_LABEL = {
  development: "內容發展", organization: "組織結構", language_use: "語言運用",
  delivery: "口語表達", topic_development: "主題發展",
  analysis: "分析", support: "論證支持", language: "語言",
};

export default function GraderView({ onAuthLost }) {
  const [taskTypes, setTaskTypes] = useState([]);
  const [taskType, setTaskType] = useState("toefl_writing_academic_discussion");
  const [bank, setBank] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  const [parentId, setParentId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);
  const [weak, setWeak] = useState([]);

  const loadWeak = useCallback(() => {
    api.weaknesses().then(setWeak).catch(() => {});
  }, []);

  useEffect(() => {
    api.taskTypes().then(setTaskTypes).catch((e) => {
      if (/登入/.test(e.message)) onAuthLost?.();
    });
    api.prompts().then(setBank).catch(() => {});
    loadWeak();
  }, [onAuthLost, loadWeak]);

  const fillFromBank = () => {
    const choices = bank.filter((b) => b.task_type === taskType);
    if (choices.length) setPrompt(choices[Math.floor(Math.random() * choices.length)].prompt);
  };

  const submit = async (e) => {
    e?.preventDefault();
    if (!answer.trim()) { setErr("請先貼上你的作答"); return; }
    setBusy(true); setErr("");
    try {
      const res = await api.gradeSubmit({
        task_type: taskType, prompt: prompt || null, user_answer: answer,
        parent_id: parentId,
      });
      setResult(res);
      loadWeak();
    } catch (e) {
      setErr(e.message);
      if (/登入/.test(e.message)) onAuthLost?.();
    } finally {
      setBusy(false);
    }
  };

  const startRewrite = () => {
    setParentId(result.id);
    setAnswer(result.user_answer);
    setPrompt(result.prompt || "");
    setTaskType(result.task_type);
    setResult(null);
    setErr("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const reset = () => {
    setResult(null); setParentId(null); setAnswer(""); setErr("");
  };

  if (busy) {
    return (
      <div className="card center grading">
        <div className="spinner" />
        <p>批改中… Claude 正在依官方 rubric 逐項評分</p>
        <p className="muted">作答較長時可能要 20–40 秒,請稍候</p>
      </div>
    );
  }

  if (result) {
    return (
      <Result
        result={result} max={scaleMax(taskTypes, result.task_type)}
        onRewrite={startRewrite} onReset={reset}
      />
    );
  }

  return (
    <div className="grader">
      {weak.length > 0 && <WeaknessBar weak={weak} />}

      <form className="card" onSubmit={submit}>
        <h3>{parentId ? "重寫同題 (會跟上次分數對照)" : "寫作 / 口說批改"}</h3>

        <label className="fld-label">題型</label>
        <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
          {taskTypes.map((t) => (
            <option key={t.key} value={t.key}>{t.label}（{t.scale}）</option>
          ))}
        </select>

        <div className="row-between">
          <label className="fld-label">題目</label>
          <button type="button" className="link" onClick={fillFromBank}>用內建題庫</button>
        </div>
        <textarea
          className="tall" placeholder="貼上題目 (口說題也貼這裡)"
          value={prompt} onChange={(e) => setPrompt(e.target.value)}
        />

        <label className="fld-label">你的作答{taskType === "toefl_speaking" ? "（口說逐字稿）" : ""}</label>
        <textarea
          className="taller" placeholder="貼上你的作答 / 逐字稿"
          value={answer} onChange={(e) => setAnswer(e.target.value)}
        />

        {err && <div className="error">{err}</div>}
        <button className="primary">送出批改</button>
        {parentId && (
          <button type="button" className="ghost" onClick={reset}>取消重寫</button>
        )}
      </form>
    </div>
  );
}

function Result({ result, max, onRewrite, onReset }) {
  const fb = result.feedback || {};
  const before = result.parent_score;
  const after = fb.score_overall;
  return (
    <div className="result">
      <div className="card score-card">
        <div className="score-big">{after != null ? after : "—"}<span className="score-max">/{max}</span></div>
        <div className="muted">總評分</div>
        {before != null && (
          <div className={`delta ${after >= before ? "up" : "down"}`}>
            重寫前 {before} → 後 {after}（{after - before >= 0 ? "+" : ""}{(after - before).toFixed(1)}）
          </div>
        )}
      </div>

      {Object.keys(fb.breakdown || {}).length > 0 && (
        <div className="card">
          <h3>各維度</h3>
          {Object.entries(fb.breakdown).map(([k, v]) => (
            <div className="dim" key={k}>
              <div className="dim-top">
                <span>{DIM_LABEL[k] || k}</span><span>{v}/{max}</span>
              </div>
              <div className="dim-track"><div className="dim-fill" style={{ width: `${(v / max) * 100}%` }} /></div>
            </div>
          ))}
        </div>
      )}

      {fb.summary_zh && (
        <div className="card"><h3>總評</h3><p className="summary">{fb.summary_zh}</p></div>
      )}

      {(fb.problem_sentences || []).length > 0 && (
        <div className="card">
          <h3>問題句 & 改寫</h3>
          {fb.problem_sentences.map((p, i) => (
            <div className="prob" key={i}>
              <div className="prob-orig">✗ {p.original}</div>
              <div className="prob-issue">{p.issue}</div>
              <div className="prob-fix">✓ {p.rewrite}</div>
            </div>
          ))}
        </div>
      )}

      {(fb.weaknesses || []).length > 0 && (
        <div className="card">
          <h3>本次弱點</h3>
          <div className="tags">{fb.weaknesses.map((w) => <span className="tag" key={w}>{w}</span>)}</div>
        </div>
      )}

      {fb.model_high_score_version && (
        <div className="card">
          <h3>高分改寫示範</h3>
          <p className="model-ver">{fb.model_high_score_version}</p>
        </div>
      )}

      <button className="primary" onClick={onRewrite}>依建議重寫</button>
      <button className="ghost" onClick={onReset}>批改新的一篇</button>
    </div>
  );
}

function WeaknessBar({ weak }) {
  const maxC = Math.max(1, ...weak.map((w) => w.count));
  return (
    <div className="card">
      <h3>弱點儀表板（累積最常犯）</h3>
      {weak.slice(0, 8).map((w) => (
        <div className="dim" key={w.category}>
          <div className="dim-top"><span>{w.category}</span><span>{w.count}</span></div>
          <div className="dim-track"><div className="dim-fill warn" style={{ width: `${(w.count / maxC) * 100}%` }} /></div>
        </div>
      ))}
    </div>
  );
}

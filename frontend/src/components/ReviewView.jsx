import { useState, useEffect, useCallback } from "react";
import { api } from "../api.js";
import { speak } from "../tts.js";

const GRADES = [
  { key: "again", label: "忘記", hint: "Again", cls: "g-again" },
  { key: "hard", label: "勉強", hint: "Hard", cls: "g-hard" },
  { key: "good", label: "記得", hint: "Good", cls: "g-good" },
  { key: "easy", label: "秒答", hint: "Easy", cls: "g-easy" },
];

// Review zone: words already learned AND due today (SM-2 schedule), served in a
// shuffled order each session. Flip to see the answer, then self-grade.
export default function ReviewView({ onAuthLost }) {
  const [queue, setQueue] = useState(null);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [due, setDue] = useState(0);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setErr("");
    try {
      const q = await api.reviewQueue();
      setQueue(q.cards);
      setDue(q.due_count);
      setIdx(0);
      setFlipped(false);
    } catch (e) {
      setErr(e.message);
      if (/登入/.test(e.message)) onAuthLost?.();
    }
  }, [onAuthLost]);

  useEffect(() => { load(); }, [load]);

  const grade = async (g) => {
    const card = queue[idx];
    try {
      await api.review(card.id, g);
    } catch (e) {
      setErr(e.message);
      return;
    }
    setFlipped(false);
    setIdx((i) => i + 1);
  };

  if (err && !queue) return <div className="card center">{err}</div>;
  if (!queue) return <div className="card center muted">載入中…</div>;

  const remaining = queue.length - idx;
  if (remaining <= 0) {
    return (
      <div className="card center done">
        <div className="big-emoji">✅</div>
        <h2>今日複習完成</h2>
        <p className="muted">今天到期 {due} 張，已全部複習。</p>
        <button className="primary" onClick={load}>重新整理</button>
      </div>
    );
  }

  const card = queue[idx];
  return (
    <div className="review">
      <div className="progress-row">
        <span>剩餘 {remaining}</span>
        <span className="muted">今日到期 {due}</span>
      </div>

      <div className="flashcard" onClick={() => !flipped && setFlipped(true)}>
        <button type="button" className="tts card-tts" aria-label="發音"
          onClick={(e) => { e.stopPropagation(); speak(card.word); }}>🔊</button>
        <div className="word">{card.word}</div>

        {!flipped ? (
          <p className="tap-hint">點一下看解釋</p>
        ) : (
          <div className="back">
            {card.part_of_speech && <div className="pos">{card.part_of_speech}</div>}
            {card.definition_zh && <div className="zh">{card.definition_zh}</div>}
            {card.definition_en && <div className="en">{card.definition_en}</div>}
            {card.synonyms && (
              <div className="syn"><span className="syn-label">同義字</span>{card.synonyms}</div>
            )}
            {card.example && <div className="ex">{card.example}</div>}
          </div>
        )}
      </div>

      {err && <div className="error">{err}</div>}

      {flipped ? (
        <div className="grades">
          {GRADES.map((g) => (
            <button key={g.key} className={`grade ${g.cls}`} onClick={() => grade(g.key)}>
              <span className="g-label">{g.label}</span>
              <span className="g-hint">{g.hint}</span>
            </button>
          ))}
        </div>
      ) : (
        <button className="primary wide" onClick={() => setFlipped(true)}>翻面</button>
      )}
    </div>
  );
}

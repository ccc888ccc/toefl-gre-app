import { useState, useEffect, useCallback } from "react";
import { api } from "../api.js";
import { speak } from "../tts.js";

// First-time learning zone: read each new word (definition shown up front, no
// flip, no self-grade), then tap "學會了" to move it into the review zone.
export default function LearnView({ onAuthLost }) {
  const [cards, setCards] = useState(null);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setErr("");
    try {
      const q = await api.learnQueue();
      setCards(q.cards);
      setIdx(0);
    } catch (e) {
      setErr(e.message);
      if (/登入/.test(e.message)) onAuthLost?.();
    }
  }, [onAuthLost]);

  useEffect(() => { load(); }, [load]);

  const learned = async () => {
    const card = cards[idx];
    setBusy(true);
    try {
      await api.markLearned(card.id);
      setIdx((i) => i + 1);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  if (err && !cards) return <div className="card center">{err}</div>;
  if (!cards) return <div className="card center muted">載入中…</div>;

  if (cards.length === 0) {
    return (
      <div className="card center done">
        <div className="big-emoji">📭</div>
        <h2>沒有新字了</h2>
        <p className="muted">字庫裡的字都學過了。去「字庫 → 加生字」新增，或之後補字腳本進來。</p>
        <button className="primary" onClick={load}>重新整理</button>
      </div>
    );
  }

  const remaining = cards.length - idx;
  if (remaining <= 0) {
    return (
      <div className="card center done">
        <div className="big-emoji">🎉</div>
        <h2>新字學完了</h2>
        <p className="muted">這些字明天會出現在「複習」分頁。</p>
        <button className="primary" onClick={load}>重新整理</button>
      </div>
    );
  }

  const card = cards[idx];
  return (
    <div className="review">
      <div className="progress-row">
        <span>新字 剩 {remaining}</span>
        <span className="muted">第 {idx + 1} / {cards.length}</span>
      </div>

      <div className="flashcard learn-card">
        <button type="button" className="tts card-tts" aria-label="發音"
          onClick={(e) => { e.stopPropagation(); speak(card.word); }}>🔊</button>
        <div className="word">{card.word}</div>
        <span className="badge">新字</span>

        <div className="back">
          {card.part_of_speech && <div className="pos">{card.part_of_speech}</div>}
          {card.definition_zh && <div className="zh">{card.definition_zh}</div>}
          {card.definition_en && <div className="en">{card.definition_en}</div>}
          {card.synonyms && (
            <div className="syn"><span className="syn-label">同義字</span>{card.synonyms}</div>
          )}
          {card.example && <div className="ex">{card.example}</div>}
        </div>
      </div>

      {err && <div className="error">{err}</div>}

      <button className="primary wide" disabled={busy} onClick={learned}>
        {busy ? "處理中…" : "學會了，下一個 →"}
      </button>
    </div>
  );
}

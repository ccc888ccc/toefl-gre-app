import { useState, useEffect } from "react";
import { api } from "../api.js";
import { speak } from "../tts.js";
import AddWordView from "./AddWordView.jsx";

function Browse() {
  const [cards, setCards] = useState(null);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api.cards().then(setCards).catch((e) => setErr(e.message));
  }, []);

  if (err) return <div className="card center">{err}</div>;
  if (!cards) return <div className="card center muted">載入中…</div>;
  if (cards.length === 0) return <div className="card center muted">字庫還沒有單字,先去「加生字」或跑補字腳本。</div>;

  const groups = {};
  for (const c of cards) {
    const L = (c.word[0] || "#").toUpperCase();
    (groups[L] = groups[L] || []).push(c);
  }
  const letters = Object.keys(groups).sort();

  return (
    <div className="browse">
      <div className="muted browse-count">共 {cards.length} 字</div>
      {letters.map((L) => (
        <div className="card letter-group" key={L}>
          <div className="letter-head">{L}</div>
          {groups[L].map((c) => (
            <div className="vocab-row" key={c.id}>
              <button type="button" className="tts" onClick={() => speak(c.word)} aria-label="發音">🔊</button>
              <div className="vocab-main" onClick={() => setOpen(open === c.id ? null : c.id)}>
                <div className="vocab-word">
                  {c.word} {c.part_of_speech && <span className="vocab-pos">{c.part_of_speech}</span>}
                </div>
                {c.definition_zh && <div className="vocab-zh">{c.definition_zh}</div>}
                {open === c.id && (
                  <div className="vocab-detail">
                    {c.definition_en && <div className="ven">{c.definition_en}</div>}
                    {c.synonyms && <div className="vsyn"><span className="syn-label">同義</span>{c.synonyms}</div>}
                    {c.example && <div className="vex">{c.example}</div>}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export default function VocabView() {
  const [mode, setMode] = useState("browse");
  return (
    <div className="vocabview">
      <div className="segmented">
        <button className={mode === "browse" ? "on" : ""} onClick={() => setMode("browse")}>瀏覽字庫</button>
        <button className={mode === "add" ? "on" : ""} onClick={() => setMode("add")}>加生字</button>
      </div>
      {mode === "browse" ? <Browse /> : <AddWordView />}
    </div>
  );
}

import { useState } from "react";
import { api } from "../api.js";

const EMPTY = {
  word: "", part_of_speech: "", definition_zh: "",
  definition_en: "", synonyms: "", example: "", tags: "custom",
};

export default function AddWordView() {
  const [f, setF] = useState(EMPTY);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (!f.word.trim()) return;
    setBusy(true);
    setMsg("");
    try {
      await api.addCard(f);
      setMsg(`已加入「${f.word.trim()}」，今天就會出現在複習佇列。`);
      setF(EMPTY);
    } catch (e) {
      setMsg(`失敗：${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card add-form" onSubmit={submit}>
      <h3>加生字</h3>
      <p className="muted">把學而思或做題時遇到的生字隨手記下來。只有「單字」是必填。</p>
      <input placeholder="單字 *" value={f.word} autoCapitalize="none" onChange={set("word")} />
      <input placeholder="詞性 (adj / n / v)" value={f.part_of_speech} onChange={set("part_of_speech")} />
      <input placeholder="中文意思" value={f.definition_zh} onChange={set("definition_zh")} />
      <textarea placeholder="英文定義" value={f.definition_en} onChange={set("definition_en")} />
      <input placeholder="同義字 (用 ; 分隔)" value={f.synonyms} onChange={set("synonyms")} />
      <textarea placeholder="例句" value={f.example} onChange={set("example")} />
      {msg && <div className="info">{msg}</div>}
      <button className="primary" disabled={busy}>{busy ? "儲存中…" : "加入卡片"}</button>
    </form>
  );
}

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
  const [filling, setFilling] = useState(false);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const autofill = async () => {
    if (!f.word.trim()) { setMsg("請先打單字再自動補齊"); return; }
    setFilling(true); setMsg("");
    try {
      const d = await api.autofill(f.word.trim());
      setF((cur) => ({
        ...cur,
        part_of_speech: d.part_of_speech || cur.part_of_speech,
        definition_zh: d.definition_zh || cur.definition_zh,
        definition_en: d.definition_en || cur.definition_en,
        synonyms: d.synonyms || cur.synonyms,
        example: d.example || cur.example,
      }));
      setMsg("已自動補齊,確認無誤再按「加入卡片」。");
    } catch (e) {
      setMsg(`自動補齊失敗：${e.message}`);
    } finally {
      setFilling(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!f.word.trim()) return;
    setBusy(true); setMsg("");
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
      <p className="muted">只打單字,按「自動補齊」讓 Claude 填好其餘欄位,你確認後再加入。</p>

      <label className="fld-label">單字 *</label>
      <input placeholder="例如 ubiquitous" value={f.word} autoCapitalize="none" onChange={set("word")} />
      <button type="button" className="ghost" onClick={autofill} disabled={filling}>
        {filling ? "補齊中…" : "✨ 自動補齊其餘欄位"}
      </button>

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

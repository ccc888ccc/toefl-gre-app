import { useState, useEffect } from "react";
import { api } from "../api.js";

export default function StatsView({ onAuthLost }) {
  const [s, setS] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.stats().then(setS).catch((e) => {
      setErr(e.message);
      if (/登入/.test(e.message)) onAuthLost?.();
    });
  }, [onAuthLost]);

  if (err) return <div className="card center">{err}</div>;
  if (!s) return <div className="card center muted">載入中…</div>;

  const maxF = Math.max(1, ...s.forecast.map((d) => d.count));
  const fmt = (iso) => {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  };

  return (
    <div className="stats">
      <div className="stat-grid">
        <Stat n={s.streak_days} label="連續天數" suffix="天" accent />
        <Stat n={s.reviewed_today} label="今日已複習" />
        <Stat n={s.mastered} label="已掌握" />
        <Stat n={s.total_cards} label="總字數" />
        <Stat n={s.due_today} label="今日待複習" />
        <Stat n={s.new_available} label="尚未學的新卡" />
      </div>

      <div className="card">
        <h3>未來 7 天複習量</h3>
        <div className="forecast">
          {s.forecast.map((d) => (
            <div className="bar-col" key={d.day}>
              <div className="bar-val">{d.count || ""}</div>
              <div
                className="bar"
                style={{ height: `${(d.count / maxF) * 100}%` }}
                title={`${d.count}`}
              />
              <div className="bar-label">{fmt(d.day)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ n, label, suffix, accent }) {
  return (
    <div className={`stat ${accent ? "accent" : ""}`}>
      <div className="stat-n">
        {n}
        {suffix && <span className="stat-suffix">{suffix}</span>}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

import { useState, useEffect } from "react";
import { api } from "../api.js";

const ROLE_LABEL = { admin: "管理員", member: "成員" };

export default function AdminUsersView() {
  const [users, setUsers] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("member");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.listUsers().then(setUsers).catch((e) => setMsg(e.message));
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) { setMsg("帳號和密碼皆為必填"); return; }
    setBusy(true); setMsg("");
    try {
      await api.createUser(username.trim(), password, role);
      setMsg(`已建立${ROLE_LABEL[role]}帳號「${username.trim()}」。`);
      setUsername(""); setPassword(""); setRole("member");
      load();
    } catch (e) {
      setMsg(`失敗：${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin-users">
      <form className="card add-form" onSubmit={submit}>
        <h3>新增帳號</h3>
        <p className="muted">成員只能用單字功能（共用字庫、各自進度，可新增單字）。管理員另有批改與檢討。</p>

        <label className="fld-label">帳號 *</label>
        <input placeholder="例如 friend1" value={username} autoCapitalize="none"
          onChange={(e) => setUsername(e.target.value)} />

        <label className="fld-label">密碼 *</label>
        <input type="password" placeholder="設定登入密碼" value={password}
          onChange={(e) => setPassword(e.target.value)} />

        <label className="fld-label">角色</label>
        <div className="segmented">
          <button type="button" className={role === "member" ? "on" : ""}
            onClick={() => setRole("member")}>成員</button>
          <button type="button" className={role === "admin" ? "on" : ""}
            onClick={() => setRole("admin")}>管理員</button>
        </div>

        {msg && <div className="info">{msg}</div>}
        <button className="primary" disabled={busy}>{busy ? "建立中…" : "建立帳號"}</button>
      </form>

      <div className="card">
        <h3>現有帳號</h3>
        {!users ? (
          <div className="muted">載入中…</div>
        ) : (
          <div className="user-list">
            {users.map((u) => (
              <div className="user-row" key={u.id}>
                <span className="user-name">{u.username}</span>
                <span className={`role-badge ${u.role}`}>{ROLE_LABEL[u.role] || u.role}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

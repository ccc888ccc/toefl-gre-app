// Tiny fetch wrapper. JWT is kept in localStorage so login persists on the device.
const TOKEN_KEY = "gre_srs_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`/api${path}`, {
    method, headers, body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    clearToken();
    throw new Error("登入已過期，請重新登入");
  }
  if (!res.ok) {
    let detail = `${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  login: (username, password) =>
    request("/auth/login", { method: "POST", body: { username, password } }),
  learnQueue: () => request("/vocab/learn"),
  markLearned: (card_id) =>
    request("/vocab/learn", { method: "POST", body: { card_id } }),
  reviewQueue: () => request("/vocab/review"),
  review: (card_id, grade) =>
    request("/vocab/review", { method: "POST", body: { card_id, grade } }),
  addCard: (card) => request("/vocab/cards", { method: "POST", body: card }),
  autofill: (word) => request("/vocab/autofill", { method: "POST", body: { word } }),
  cards: (q) => request(`/vocab/cards?limit=3000${q ? `&q=${encodeURIComponent(q)}` : ""}`),
  stats: () => request("/stats"),

  // Tool 2: writing / speaking grader
  taskTypes: () => request("/writing/task-types"),
  prompts: () => request("/writing/prompts"),
  gradeSubmit: (body) => request("/writing/submit", { method: "POST", body }),
  submissions: () => request("/writing/submissions"),
  submission: (id) => request(`/writing/submissions/${id}`),
  weaknesses: () => request("/writing/weaknesses"),

  // Tool 3: reading / listening review
  practiceSubmit: (body) => request("/practice/submit", { method: "POST", body }),
  practiceLogs: () => request("/practice/logs"),
  typeStats: () => request("/practice/type-stats"),
};

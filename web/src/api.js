// Thin client over the FastAPI backend.
const base = "";

async function post(path, params) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  const r = await fetch(base + path + qs, { method: "POST" });
  return r.json();
}
async function get(path) {
  const r = await fetch(base + path);
  return r.json();
}

export const api = {
  health: () => get("/api/health"),
  state: () => get("/api/state"),
  newLive: () => post("/api/live/new"),
  stepLive: () => post("/api/live/step"),
  train: (n = 200) => post("/api/train", { n }),
  curve: () => get("/api/curve"),
  status: () => get("/api/status"),
  generations: () => get("/api/generations"),
};

const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

function response(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: JSON_HEADERS });
}

async function increment(db, name, amount) {
  await db.prepare(
    "INSERT INTO counters(name, value) VALUES(?, ?) " +
      "ON CONFLICT(name) DO UPDATE SET value = value + excluded.value"
  ).bind(name, amount).run();
}

async function recordUsage(request, env) {
  const contentLength = Number(request.headers.get("content-length") || 0);
  if (contentLength > 2048) return response({ error: "payload_too_large" }, 413);
  let payload;
  try {
    payload = await request.json();
  } catch {
    return response({ error: "invalid_json" }, 400);
  }
  const session = String(payload.session || "");
  const event = String(payload.event || "");
  const actions = Number(payload.actions);
  if (
    payload.schema !== 1 ||
    !/^[A-Za-z0-9_-]{20,64}$/.test(session) ||
    !["start", "heartbeat"].includes(event) ||
    !Number.isInteger(actions) || actions < 0 || actions > 10000
  ) return response({ error: "invalid_payload" }, 400);

  const now = Math.floor(Date.now() / 1000);
  const day = new Date().toISOString().slice(0, 10);
  await env.DB.prepare("DELETE FROM active_sessions WHERE last_seen < ?")
    .bind(now - 300).run();
  const inserted = await env.DB.prepare(
    "INSERT OR IGNORE INTO active_sessions(session, started_at, last_seen) VALUES(?, ?, ?)"
  ).bind(session, now, now).run();
  await env.DB.prepare("UPDATE active_sessions SET last_seen = ? WHERE session = ?")
    .bind(now, session).run();
  if (event === "start" && Number(inserted.meta?.changes || 0) === 1) {
    await increment(env.DB, "launches:total", 1);
    await increment(env.DB, `launches:${day}`, 1);
  }
  if (actions > 0) {
    await increment(env.DB, "actions:total", actions);
    await increment(env.DB, `actions:${day}`, actions);
  }
  return new Response(null, { status: 204, headers: { "cache-control": "no-store" } });
}

function authorized(request, env) {
  const expected = String(env.ADMIN_TOKEN || "");
  return expected.length >= 32 && request.headers.get("authorization") === `Bearer ${expected}`;
}

async function adminStats(request, env) {
  if (!authorized(request, env)) return response({ error: "unauthorized" }, 401);
  const now = Math.floor(Date.now() / 1000);
  const day = new Date().toISOString().slice(0, 10);
  const active = await env.DB.prepare(
    "SELECT COUNT(*) AS count FROM active_sessions WHERE last_seen >= ?"
  ).bind(now - 120).first();
  const rows = await env.DB.prepare(
    "SELECT name, value FROM counters WHERE name IN (?, ?, ?, ?)"
  ).bind("launches:total", `launches:${day}`, "actions:total", `actions:${day}`).all();
  const counters = Object.fromEntries((rows.results || []).map((row) => [row.name, row.value]));
  return response({
    active_now: Number(active?.count || 0),
    launches_today: Number(counters[`launches:${day}`] || 0),
    launches_total: Number(counters["launches:total"] || 0),
    actions_today: Number(counters[`actions:${day}`] || 0),
    actions_total: Number(counters["actions:total"] || 0),
    updated_at: new Date().toISOString(),
  });
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (request.method === "POST" && path === "/v1/usage") return recordUsage(request, env);
    if (request.method === "GET" && path === "/v1/admin/stats") return adminStats(request, env);
    if (request.method === "GET" && path === "/health") return response({ ok: true });
    return response({ error: "not_found" }, 404);
  },
};

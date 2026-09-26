const JSON_HEADERS = {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "no-store",
  "x-content-type-options": "nosniff",
};

const encoder = new TextEncoder();

function base64url(bytes) {
  return btoa(String.fromCharCode(...bytes))
    .replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/g, "");
}

function randomValue(byteCount = 32) {
  const bytes = new Uint8Array(byteCount);
  crypto.getRandomValues(bytes);
  return base64url(bytes);
}

async function sha256(value) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}

async function keyedHash(secret, value) {
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(secret), {name: "HMAC", hash: "SHA-256"}, false, ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, encoder.encode(value));
  return Array.from(new Uint8Array(signature), byte => byte.toString(16).padStart(2, "0")).join("");
}

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
  const installation = String(payload.installation || "");
  if (
    payload.schema !== 1 ||
    !/^[A-Za-z0-9_-]{20,64}$/.test(session) ||
    !["start", "heartbeat", "stop"].includes(event) ||
    !Number.isInteger(actions) || actions < 0 || actions > 10000 ||
    (installation && !/^[A-Za-z0-9_-]{20,64}$/.test(installation))
  ) return response({ error: "invalid_payload" }, 400);

  const now = Math.floor(Date.now() / 1000);
  const day = new Date().toISOString().slice(0, 10);
  if (installation) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(installation));
    const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
    await env.DB.prepare(
      "INSERT INTO installations(installation_hash, first_seen, last_seen) VALUES(?, ?, ?) " +
      "ON CONFLICT(installation_hash) DO UPDATE SET last_seen = excluded.last_seen"
    ).bind(hash, now, now).run();
  }
  await env.DB.prepare("DELETE FROM active_sessions WHERE last_seen < ?")
    .bind(now - 300).run();
  if (event === "stop") {
    await env.DB.prepare("DELETE FROM active_sessions WHERE session = ?")
      .bind(session).run();
    if (actions > 0) {
      await increment(env.DB, "actions:total", actions);
      await increment(env.DB, `actions:${day}`, actions);
    }
    return new Response(null, { status: 204, headers: { "cache-control": "no-store" } });
  }
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

function supporterConfigured(env) {
  return String(env.KOFI_VERIFICATION_TOKEN || "").length >= 16 &&
    String(env.SUPPORTER_HASH_SECRET || "").length >= 32;
}

function parseBoolean(value) {
  return value === true || String(value).toLowerCase() === "true";
}

async function koFiWebhook(request, env) {
  if (!supporterConfigured(env)) return response({error: "not_configured"}, 503);
  const contentLength = Number(request.headers.get("content-length") || 0);
  if (contentLength > 32 * 1024) return response({error: "payload_too_large"}, 413);

  let payload;
  try {
    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      payload = await request.json();
    } else {
      const form = await request.formData();
      payload = JSON.parse(String(form.get("data") || "{}"));
    }
  } catch {
    return response({error: "invalid_payload"}, 400);
  }

  if (String(payload.verification_token || "") !== String(env.KOFI_VERIFICATION_TOKEN)) {
    return response({error: "unauthorized"}, 401);
  }
  const expectedTier = String(env.KOFI_SUPPORTER_TIER || "HCD Supporter").trim().toLowerCase();
  const tierName = String(payload.tier_name || "").trim();
  const transactionId = String(payload.kofi_transaction_id || payload.transaction_id || "").trim();
  const email = String(payload.email || "").trim().toLowerCase();
  const isSubscription = parseBoolean(payload.is_subscription_payment) ||
    String(payload.type || "").toLowerCase() === "subscription";
  if (!isSubscription || tierName.toLowerCase() !== expectedTier || !email || !transactionId) {
    // Ko-fi also sends one-time tips to the same webhook. They support the
    // project but intentionally do not unlock the monthly Supporter tier.
    return response({ok: true, ignored: true});
  }

  const secret = String(env.SUPPORTER_HASH_SECRET);
  const emailHash = await keyedHash(secret, `email:${email}`);
  const transactionHash = await keyedHash(secret, `transaction:${transactionId}`);
  const duplicate = await env.DB.prepare(
    "SELECT membership_id FROM supporter_transactions WHERE transaction_hash = ?"
  ).bind(transactionHash).first();
  if (duplicate?.membership_id) return response({ok: true, duplicate: true});

  const now = Math.floor(Date.now() / 1000);
  const graceSeconds = 35 * 86400;
  let member = await env.DB.prepare(
    "SELECT id, active_until FROM supporter_memberships WHERE email_hash = ?"
  ).bind(emailHash).first();
  if (!member) {
    member = {id: randomValue(18), active_until: 0};
    await env.DB.prepare(
      "INSERT INTO supporter_memberships(id, email_hash, tier_name, active_until, last_payment_at, created_at, updated_at) " +
      "VALUES(?, ?, ?, ?, ?, ?, ?)"
    ).bind(member.id, emailHash, tierName, now + graceSeconds, now, now, now).run();
  } else {
    const activeUntil = Math.max(Number(member.active_until || 0), now) + graceSeconds;
    await env.DB.prepare(
      "UPDATE supporter_memberships SET tier_name = ?, active_until = ?, last_payment_at = ?, updated_at = ? WHERE id = ?"
    ).bind(tierName, activeUntil, now, now, member.id).run();
  }
  await env.DB.prepare(
    "INSERT INTO supporter_transactions(transaction_hash, membership_id, received_at) VALUES(?, ?, ?)"
  ).bind(transactionHash, member.id, now).run();
  return response({ok: true});
}

async function claimSupporter(request, env) {
  if (!supporterConfigured(env)) return response({error: "not_configured"}, 503);
  let payload;
  try { payload = await request.json(); } catch { return response({error: "invalid_json"}, 400); }
  const transactionId = String(payload.transaction_id || "").trim();
  if (transactionId.length < 8 || transactionId.length > 200) {
    return response({error: "invalid_transaction"}, 400);
  }
  const transactionHash = await keyedHash(
    String(env.SUPPORTER_HASH_SECRET), `transaction:${transactionId}`
  );
  const member = await env.DB.prepare(
    "SELECT m.id, m.tier_name, m.active_until FROM supporter_transactions t " +
    "JOIN supporter_memberships m ON m.id = t.membership_id WHERE t.transaction_hash = ?"
  ).bind(transactionHash).first();
  const now = Math.floor(Date.now() / 1000);
  if (!member || Number(member.active_until || 0) <= now) {
    return response({error: "membership_not_found"}, 404);
  }
  const token = `hcds_${randomValue(32)}`;
  const tokenHash = await sha256(token);
  await env.DB.prepare(
    "INSERT INTO supporter_tokens(token_hash, membership_id, created_at, last_seen) VALUES(?, ?, ?, ?)"
  ).bind(tokenHash, member.id, now, now).run();
  return response({
    active: true,
    token,
    tier: member.tier_name,
    active_until: new Date(Number(member.active_until) * 1000).toISOString(),
  });
}

async function supporterStatus(request, env) {
  const authorization = request.headers.get("authorization") || "";
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7).trim() : "";
  if (!token.startsWith("hcds_") || token.length > 128) {
    return response({active: false, error: "unauthorized"}, 401);
  }
  const tokenHash = await sha256(token);
  const member = await env.DB.prepare(
    "SELECT m.tier_name, m.active_until FROM supporter_tokens t " +
    "JOIN supporter_memberships m ON m.id = t.membership_id " +
    "WHERE t.token_hash = ? AND t.revoked_at IS NULL"
  ).bind(tokenHash).first();
  const now = Math.floor(Date.now() / 1000);
  if (!member) return response({active: false}, 401);
  await env.DB.prepare("UPDATE supporter_tokens SET last_seen = ? WHERE token_hash = ?")
    .bind(now, tokenHash).run();
  return response({
    active: Number(member.active_until || 0) > now,
    tier: member.tier_name,
    active_until: new Date(Number(member.active_until || 0) * 1000).toISOString(),
  });
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
  const unique = await env.DB.prepare(
    "SELECT COUNT(*) AS total, " +
    "COALESCE(SUM(CASE WHEN first_seen >= ? THEN 1 ELSE 0 END), 0) AS today, " +
    "COALESCE(SUM(CASE WHEN last_seen >= ? THEN 1 ELSE 0 END), 0) AS month " +
    "FROM installations"
  ).bind(Math.floor(Date.parse(`${day}T00:00:00Z`) / 1000), now - 30 * 86400).first();
  const rows = await env.DB.prepare(
    "SELECT name, value FROM counters WHERE name IN (?, ?, ?, ?)"
  ).bind("launches:total", `launches:${day}`, "actions:total", `actions:${day}`).all();
  const counters = Object.fromEntries((rows.results || []).map((row) => [row.name, row.value]));
  return response({
    active_now: Number(active?.count || 0),
    unique_installations_total: Number(unique?.total || 0),
    new_installations_today: Number(unique?.today || 0),
    unique_installations_30d: Number(unique?.month || 0),
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
    if (request.method === "POST" && path === "/v1/kofi/webhook") return koFiWebhook(request, env);
    if (request.method === "POST" && path === "/v1/supporter/claim") return claimSupporter(request, env);
    if (request.method === "GET" && path === "/v1/supporter/status") return supporterStatus(request, env);
    if (request.method === "GET" && path === "/v1/admin/stats") return adminStats(request, env);
    if (request.method === "GET" && path === "/health") return response({ ok: true });
    return response({ error: "not_found" }, 404);
  },
};

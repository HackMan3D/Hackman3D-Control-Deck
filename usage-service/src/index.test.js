import test from "node:test";
import assert from "node:assert/strict";
import worker from "./index.js";

function database() {
  const installations = new Map();
  const sessions = new Map();
  const counters = new Map();
  return { installations, prepare(sql) {
    let args;
    return { bind(...values) { args = values; return this; },
      async run() {
        if (sql.startsWith("INSERT INTO installations")) {
          installations.set(args[0], {first: installations.get(args[0])?.first ?? args[1], last: args[2]});
        } else if (sql.startsWith("DELETE FROM active_sessions WHERE last_seen")) {
          for (const [id, row] of sessions) if (row < args[0]) sessions.delete(id);
        } else if (sql.startsWith("DELETE FROM active_sessions WHERE session")) sessions.delete(args[0]);
        else if (sql.startsWith("INSERT OR IGNORE INTO active_sessions")) {
          const changes = sessions.has(args[0]) ? 0 : 1;
          sessions.set(args[0], args[2]); return {meta: {changes}};
        } else if (sql.startsWith("UPDATE active_sessions")) sessions.set(args[1], args[0]);
        else if (sql.startsWith("INSERT INTO counters")) counters.set(args[0], (counters.get(args[0]) || 0) + args[1]);
        return {meta: {changes: 1}};
      },
      async first() {
        if (sql.includes("FROM installations")) return {
          total: installations.size,
          today: [...installations.values()].filter(row => row.first >= args[0]).length,
          month: [...installations.values()].filter(row => row.last >= args[1]).length,
        };
        return {count: [...sessions.values()].filter(last => last >= args[0]).length};
      },
      async all() { return {results: args.filter(name => counters.has(name)).map(name => ({name, value: counters.get(name)}))}; }
    };
  }};
}
test("unique counts persist across sessions and 30-day counts expire", async () => {
  const DB = database();
  const env = {DB, ADMIN_TOKEN: "a".repeat(32)};
  const installation = "random-installation-12345";
  for (const session of ["random-session-first-12345", "random-session-second-12345"]) {
    const result = await worker.fetch(new Request("https://test/v1/usage", {
      method: "POST", body: JSON.stringify({schema: 1, session, event: "start", actions: 0, installation})
    }), env);
    assert.equal(result.status, 204);
  }
  assert.equal(DB.installations.size, 1);
  assert.ok(!DB.installations.has(installation));
  const request = new Request("https://test/v1/admin/stats", {headers: {authorization: `Bearer ${env.ADMIN_TOKEN}`}});
  let stats = await (await worker.fetch(request, env)).json();
  assert.equal(stats.unique_installations_total, 1);
  assert.equal(stats.new_installations_today, 1);
  assert.equal(stats.unique_installations_30d, 1);
  assert.equal(stats.active_now, 2);
  for (const row of DB.installations.values()) row.last -= 31 * 86400;
  stats = await (await worker.fetch(request, env)).json();
  assert.equal(stats.unique_installations_total, 1);
  assert.equal(stats.unique_installations_30d, 0);
});
test("admin endpoint is private and invalid installation IDs are rejected", async () => {
  const env = {DB: database(), ADMIN_TOKEN: "a".repeat(32)};
  assert.equal((await worker.fetch(new Request("https://test/v1/admin/stats"), env)).status, 401);
  assert.equal((await worker.fetch(new Request("https://test/v1/usage", {
    method: "POST", body: JSON.stringify({schema: 1, session: "random-session-first-12345", event: "start", actions: 0, installation: "bad"})
  }), env)).status, 400);
});

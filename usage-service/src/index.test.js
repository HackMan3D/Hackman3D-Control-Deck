import test from "node:test";
import assert from "node:assert/strict";
import worker from "./index.js";

function database() {
  const installations = new Map();
  const sessions = new Map();
  const counters = new Map();
  const membersByEmail = new Map();
  const membersById = new Map();
  const transactions = new Map();
  const tokens = new Map();
  return { installations, membersByEmail, transactions, tokens, prepare(sql) {
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
        else if (sql.startsWith("INSERT INTO supporter_memberships")) {
          const member = {id: args[0], email_hash: args[1], tier_name: args[2], active_until: args[3]};
          membersByEmail.set(args[1], member); membersById.set(args[0], member);
        } else if (sql.startsWith("UPDATE supporter_memberships")) {
          const member = membersById.get(args[4]);
          Object.assign(member, {tier_name: args[0], active_until: args[1]});
        } else if (sql.startsWith("INSERT INTO supporter_transactions")) {
          transactions.set(args[0], args[1]);
        } else if (sql.startsWith("INSERT INTO supporter_tokens")) {
          tokens.set(args[0], {membership_id: args[1], last_seen: args[3]});
        } else if (sql.startsWith("UPDATE supporter_tokens")) {
          const token = tokens.get(args[1]); if (token) token.last_seen = args[0];
        }
        return {meta: {changes: 1}};
      },
      async first() {
        if (sql.startsWith("SELECT membership_id FROM supporter_transactions")) {
          const membership_id = transactions.get(args[0]);
          return membership_id ? {membership_id} : null;
        }
        if (sql.startsWith("SELECT id, active_until FROM supporter_memberships")) {
          return membersByEmail.get(args[0]) || null;
        }
        if (sql.startsWith("SELECT m.id, m.tier_name")) {
          const memberId = transactions.get(args[0]); return membersById.get(memberId) || null;
        }
        if (sql.startsWith("SELECT m.tier_name, m.active_until")) {
          const token = tokens.get(args[0]); return membersById.get(token?.membership_id) || null;
        }
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

test("Ko-fi membership can be claimed without storing email or transaction plaintext", async () => {
  const DB = database();
  const env = {
    DB,
    ADMIN_TOKEN: "a".repeat(32),
    KOFI_VERIFICATION_TOKEN: "verification-token",
    SUPPORTER_HASH_SECRET: "s".repeat(32),
    KOFI_SUPPORTER_TIER: "HCD Supporter",
  };
  const transaction = "KO-FI-TRANSACTION-123";
  const form = new FormData();
  form.set("data", JSON.stringify({
    verification_token: env.KOFI_VERIFICATION_TOKEN,
    type: "Subscription",
    is_subscription_payment: true,
    tier_name: "HCD Supporter",
    email: "supporter@example.com",
    kofi_transaction_id: transaction,
  }));
  const webhook = await worker.fetch(new Request("https://test/v1/kofi/webhook", {
    method: "POST", body: form,
  }), env);
  assert.equal(webhook.status, 200);
  assert.equal(DB.membersByEmail.size, 1);
  assert.ok(!DB.membersByEmail.has("supporter@example.com"));
  assert.ok(!DB.transactions.has(transaction));

  const claim = await worker.fetch(new Request("https://test/v1/supporter/claim", {
    method: "POST", body: JSON.stringify({transaction_id: transaction}),
  }), env);
  assert.equal(claim.status, 200);
  const activation = await claim.json();
  assert.equal(activation.active, true);
  assert.match(activation.token, /^hcds_/);

  const status = await worker.fetch(new Request("https://test/v1/supporter/status", {
    headers: {authorization: `Bearer ${activation.token}`},
  }), env);
  assert.equal(status.status, 200);
  assert.equal((await status.json()).active, true);
});

test("one-time Ko-fi tips do not unlock Supporter", async () => {
  const DB = database();
  const env = {
    DB,
    KOFI_VERIFICATION_TOKEN: "verification-token",
    SUPPORTER_HASH_SECRET: "s".repeat(32),
  };
  const form = new FormData();
  form.set("data", JSON.stringify({
    verification_token: env.KOFI_VERIFICATION_TOKEN,
    type: "Donation",
    email: "tip@example.com",
    kofi_transaction_id: "TIP-12345678",
  }));
  const result = await worker.fetch(new Request("https://test/v1/kofi/webhook", {
    method: "POST", body: form,
  }), env);
  assert.equal(result.status, 200);
  assert.equal((await result.json()).ignored, true);
  assert.equal(DB.membersByEmail.size, 0);
});

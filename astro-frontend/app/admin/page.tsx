"use client";

import { useEffect, useState } from "react";
import { getBrowserApiBase } from "../../lib/api";

/**
 * A private spending view — the thing the provider dashboards can't show:
 * which of your users cost what, on which model, this month.
 *
 * Gated by the same ADMIN_SECRET as the tier controls. The secret is kept in
 * sessionStorage so a refresh doesn't ask again, and never leaves this browser.
 */

type ByModel = {
  model_key: string;
  calls: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
};

type TopUser = {
  user_id: number | null;
  email: string | null;
  tier: string | null;
  calls: number;
  cost_usd: number;
};

type Summary = {
  generated_at: string;
  month_to_date_usd: number;
  all_time_usd: number;
  calls_this_month: number;
  by_model: ByModel[];
  top_users: TopUser[];
};

const money = (n: number) => `$${n.toFixed(n < 1 ? 3 : 2)}`;
const num = (n: number) => n.toLocaleString();

const MODEL_LABEL: Record<string, string> = {
  fast: "Fast",
  smart: "Smart",
  deep: "Deep",
  other: "Other",
};

type ErrorEvent = {
  id: number; path: string; method: string; kind: string;
  message: string; created_at: string; status_code: number | null;
};
type BugReport = {
  id: number; email: string | null; message: string;
  page: string | null; resolved: number; created_at: string;
};
type ErrorReport = {
  summary: { total: number; last_24h: number; last_hour: number;
             most_common_today: { kind: string; path: string; hits: number }[] };
  errors: ErrorEvent[];
};

const ago = (iso: string) => {
  const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`;
};

export default function AdminPage() {
  const [secret, setSecret] = useState("");
  const [data, setData] = useState<Summary | null>(null);
  // What has been failing. The whole point of recording it was so nobody has
  // to hear about a bug from the person it happened to.
  const [faults, setFaults] = useState<ErrorReport | null>(null);
  // What people said was broken, in their words. Separate from the error log:
  // a crash and "this answer made no sense" are different problems.
  const [bugs, setBugs] = useState<{ open: number; reports: BugReport[] } | null>(null);
  // Changing someone's tier used to mean a terminal and a remembered curl.
  // It is needed for test accounts now and for comped friends and early
  // customers until payments exist, so it belongs where the secret already is.
  const [tierEmail, setTierEmail] = useState("");
  const [tierChoice, setTierChoice] = useState("premium");
  const [tierNote, setTierNote] = useState("");
  const [tierBusy, setTierBusy] = useState(false);

  const applyTier = async () => {
    if (!tierEmail.trim()) return setTierNote("Which account?");
    setTierBusy(true);
    setTierNote("");
    try {
      const res = await fetch(`${getBrowserApiBase()}/admin/tier-by-email`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", "x-admin-secret": secret },
        body: JSON.stringify({ email: tierEmail.trim(), tier: tierChoice }),
      });
      const body = await res.json().catch(() => ({}));
      setTierNote(
        res.ok
          ? `${tierEmail.trim()} is now ${tierChoice}.`
          : typeof body.detail === "string" ? body.detail : "That didn't work.",
      );
      if (res.ok) load(secret);
    } catch {
      setTierNote("Could not reach the server.");
    }
    setTierBusy(false);
  };
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const load = async (withSecret: string) => {
    if (!withSecret) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${getBrowserApiBase()}/admin/usage`, {
        headers: { "x-admin-secret": withSecret },
      });
      if (res.status === 401) {
        setError("That admin secret isn't right.");
        setData(null);
      } else if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(typeof body.detail === "string" ? body.detail : "Could not load spending.");
      } else {
        setData(await res.json());
        // Same secret, same trip — no reason to make this a separate action.
        fetch(`${getBrowserApiBase()}/admin/errors?limit=25`, {
          headers: { "x-admin-secret": withSecret },
        })
          .then((r) => (r.ok ? r.json() : null))
          .then(setFaults)
          .catch(() => setFaults(null));
        fetch(`${getBrowserApiBase()}/admin/bug-reports?limit=30`, {
          headers: { "x-admin-secret": withSecret },
        })
          .then((r) => (r.ok ? r.json() : null))
          .then(setBugs)
          .catch(() => setBugs(null));
        try {
          sessionStorage.setItem("zodi-admin-secret", withSecret);
        } catch {
          /* private mode — fine */
        }
      }
    } catch {
      setError("Could not reach the server.");
    }
    setLoading(false);
  };

  useEffect(() => {
    let saved = "";
    try {
      saved = sessionStorage.getItem("zodi-admin-secret") ?? "";
    } catch {
      /* ignore */
    }
    if (saved) {
      setSecret(saved);
      load(saved);
    }
  }, []);

  return (
    <main
      className="min-h-screen"
      style={{ background: "var(--sky)", padding: "clamp(20px, 4vw, 48px)" }}
    >
      <div className="mx-auto flex w-full flex-col" style={{ maxWidth: 780 }}>
        <p className="micro-label" style={{ letterSpacing: "0.26em" }}>Zodi · private</p>
        <h1 className="font-display" style={{ fontSize: "clamp(28px, 5vw, 40px)", marginTop: 4 }}>
          Spending
        </h1>
        <p className="font-reading" style={{ fontSize: 15, color: "var(--ink-3)", marginTop: 6 }}>
          What the app has cost, per model and per user — the view no provider
          dashboard can give you.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-2">
          <input
            type="password"
            value={secret}
            onChange={(e) => setSecret(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") load(secret); }}
            placeholder="Admin secret"
            className="auth-field"
            style={{ maxWidth: 260 }}
          />
          <button
            onClick={() => load(secret)}
            disabled={loading}
            className="uppercase"
            style={{
              borderRadius: 999,
              padding: "11px 22px",
              fontSize: 11,
              letterSpacing: "0.18em",
              background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
              color: "var(--on-gold)",
            }}
          >
            {loading ? "Loading…" : data ? "Refresh" : "Load"}
          </button>
        </div>

        {error && (
          <p className="font-reading" style={{ fontSize: 14, color: "var(--gold-deep)", marginTop: 12 }}>
            {error}
          </p>
        )}

        {data && (
          <>
            <div className="mt-7 grid gap-3" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
              {[
                ["This month", money(data.month_to_date_usd)],
                ["All time", money(data.all_time_usd)],
                ["Messages this month", num(data.calls_this_month)],
              ].map(([label, value]) => (
                <div
                  key={label}
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--line-2)",
                    borderRadius: 18,
                    padding: "18px 20px",
                  }}
                >
                  <p className="micro-label" style={{ color: "var(--ink-3)" }}>{label}</p>
                  <p className="font-display" style={{ fontSize: 30, marginTop: 6 }}>{value}</p>
                </div>
              ))}
            </div>

            <h2 className="micro-label" style={{ letterSpacing: "0.22em", marginTop: 30, marginBottom: 10 }}>
              By model · this month
            </h2>
            <div style={{ border: "1px solid var(--line)", borderRadius: 14, overflow: "hidden" }}>
              {data.by_model.length === 0 && (
                <p className="font-reading" style={{ fontSize: 14, color: "var(--ink-3)", padding: "14px 16px" }}>
                  No messages yet this month.
                </p>
              )}
              {data.by_model.map((m) => (
                <div
                  key={m.model_key}
                  className="flex items-center justify-between"
                  style={{ padding: "13px 16px", borderTop: "1px solid var(--line)", fontSize: 14 }}
                >
                  <span style={{ color: "var(--ink)", fontWeight: 500 }}>
                    {MODEL_LABEL[m.model_key] ?? m.model_key}
                  </span>
                  <span style={{ color: "var(--ink-3)", fontSize: 13 }}>
                    {num(m.calls)} msgs · {num(m.tokens_in)} in / {num(m.tokens_out)} out
                  </span>
                  <span className="font-reading" style={{ color: "var(--ink)", minWidth: 70, textAlign: "right" }}>
                    {money(m.cost_usd)}
                  </span>
                </div>
              ))}
            </div>

            <h2 className="micro-label" style={{ letterSpacing: "0.22em", marginTop: 30, marginBottom: 10 }}>
              Change someone&rsquo;s plan
            </h2>
            <div
              style={{ border: "1px solid var(--line)", borderRadius: 14, padding: "14px 16px" }}
            >
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={tierEmail}
                  onChange={(e) => setTierEmail(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") applyTier(); }}
                  placeholder="their email"
                  className="min-w-0 flex-1"
                  style={{
                    background: "var(--sunk)", border: "1px solid var(--line-2)",
                    borderRadius: 10, padding: "9px 12px", fontSize: 14, color: "var(--ink)",
                  }}
                />
                <select
                  value={tierChoice}
                  onChange={(e) => setTierChoice(e.target.value)}
                  style={{
                    background: "var(--sunk)", border: "1px solid var(--line-2)",
                    borderRadius: 10, padding: "9px 12px", fontSize: 14, color: "var(--ink)",
                  }}
                >
                  <option value="free">Free</option>
                  <option value="standard">Standard</option>
                  <option value="premium">Premium &mdash; unlimited</option>
                </select>
                <button
                  onClick={applyTier}
                  disabled={tierBusy}
                  className="micro-label"
                  style={{
                    letterSpacing: "0.14em", color: "var(--on-gold)",
                    background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
                    borderRadius: 999, padding: "10px 18px", opacity: tierBusy ? 0.6 : 1,
                  }}
                >
                  {tierBusy ? "Saving…" : "Apply"}
                </button>
              </div>
              {tierNote && (
                <p className="font-reading" style={{ fontSize: 13.5, color: "var(--ink-2)", marginTop: 10 }}>
                  {tierNote}
                </p>
              )}
              <p style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 8 }}>
                Premium is unlimited tokens on all three models, and unlimited
                saved people. The account has to exist already.
              </p>
            </div>

            <h2 className="micro-label" style={{ letterSpacing: "0.22em", marginTop: 30, marginBottom: 10 }}>
              Reported by people {bugs && bugs.open > 0 && (
                <span style={{ color: "var(--gold-deep)" }}>· {bugs.open} open</span>
              )}
            </h2>
            <div style={{ border: "1px solid var(--line)", borderRadius: 14, overflow: "hidden" }}>
              {(!bugs || bugs.reports.length === 0) && (
                <p className="font-reading" style={{ fontSize: 14, color: "var(--ink-3)", padding: "14px 16px" }}>
                  {bugs ? "Nobody has reported anything." : "Checking…"}
                </p>
              )}
              {bugs?.reports.map((b) => (
                <div key={b.id} style={{ padding: "13px 16px", borderTop: "1px solid var(--line)", opacity: b.resolved ? 0.45 : 1 }}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate" style={{ fontSize: 13, color: "var(--ink-3)" }}>
                      {b.email ?? "not signed in"} {b.page && <span>· {b.page}</span>}
                    </span>
                    <span className="flex shrink-0 items-baseline gap-3">
                      <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{ago(b.created_at)}</span>
                      {!b.resolved && (
                        <button
                          onClick={async () => {
                            await fetch(`${getBrowserApiBase()}/admin/bug-reports/${b.id}`, {
                              method: "PATCH", headers: { "x-admin-secret": secret },
                            });
                            load(secret);
                          }}
                          className="micro-label"
                          style={{ letterSpacing: "0.12em", color: "var(--gold-deep)" }}
                        >
                          Done
                        </button>
                      )}
                    </span>
                  </div>
                  <p className="font-reading" style={{ fontSize: 15, color: "var(--ink)", marginTop: 4, overflowWrap: "anywhere" }}>
                    {b.message}
                  </p>
                </div>
              ))}
            </div>

            <h2 className="micro-label" style={{ letterSpacing: "0.22em", marginTop: 30, marginBottom: 10 }}>
              Something broken?
            </h2>
            <div style={{ border: "1px solid var(--line)", borderRadius: 14, overflow: "hidden" }}>
              {!faults && (
                <p className="font-reading" style={{ fontSize: 14, color: "var(--ink-3)", padding: "14px 16px" }}>
                  Checking…
                </p>
              )}
              {faults && faults.summary.total === 0 && (
                <p className="font-reading" style={{ fontSize: 14, color: "var(--ink-3)", padding: "14px 16px" }}>
                  Nothing has failed. That is the answer you want here.
                </p>
              )}
              {faults && faults.summary.total > 0 && (
                <>
                  <div
                    className="flex flex-wrap items-baseline gap-x-6 gap-y-1"
                    style={{ padding: "13px 16px", fontSize: 14 }}
                  >
                    <span style={{ color: faults.summary.last_hour ? "var(--gold-deep)" : "var(--ink-3)" }}>
                      <strong>{num(faults.summary.last_hour)}</strong> in the last hour
                    </span>
                    <span style={{ color: "var(--ink-2)" }}>
                      <strong>{num(faults.summary.last_24h)}</strong> today
                    </span>
                    <span style={{ color: "var(--ink-3)" }}>{num(faults.summary.total)} kept in all</span>
                  </div>
                  {faults.errors.slice(0, 8).map((e) => (
                    <div
                      key={e.id}
                      style={{ padding: "12px 16px", borderTop: "1px solid var(--line)", fontSize: 13.5 }}
                    >
                      <div className="flex items-baseline justify-between gap-3">
                        <span className="min-w-0 truncate" style={{ color: "var(--ink)" }}>
                          <strong>{e.kind}</strong>{" "}
                          <span style={{ color: "var(--ink-3)" }}>{e.method} {e.path}</span>
                        </span>
                        <span style={{ color: "var(--ink-3)", whiteSpace: "nowrap" }}>{ago(e.created_at)}</span>
                      </div>
                      {e.message && (
                        <p
                          className="font-reading"
                          style={{ fontSize: 13, color: "var(--ink-2)", marginTop: 3, overflowWrap: "anywhere" }}
                        >
                          {e.message}
                        </p>
                      )}
                    </div>
                  ))}
                </>
              )}
            </div>

            <h2 className="micro-label" style={{ letterSpacing: "0.22em", marginTop: 30, marginBottom: 10 }}>
              Biggest spenders · this month
            </h2>
            <div style={{ border: "1px solid var(--line)", borderRadius: 14, overflow: "hidden" }}>
              {data.top_users.length === 0 && (
                <p className="font-reading" style={{ fontSize: 14, color: "var(--ink-3)", padding: "14px 16px" }}>
                  Nobody yet.
                </p>
              )}
              {data.top_users.map((u) => (
                <div
                  key={u.user_id ?? "unknown"}
                  className="flex items-center justify-between gap-3"
                  style={{ padding: "13px 16px", borderTop: "1px solid var(--line)", fontSize: 14 }}
                >
                  <span className="min-w-0 truncate" style={{ color: "var(--ink)" }}>
                    {u.email ?? `user ${u.user_id ?? "?"}`}
                    {u.tier && u.tier !== "free" && (
                      <span className="micro-label" style={{ marginLeft: 8, color: "var(--gold-deep)" }}>
                        {u.tier}
                      </span>
                    )}
                  </span>
                  <span style={{ color: "var(--ink-3)", fontSize: 13, whiteSpace: "nowrap" }}>
                    {num(u.calls)} msgs
                  </span>
                  <span className="font-reading" style={{ color: "var(--ink)", minWidth: 70, textAlign: "right" }}>
                    {money(u.cost_usd)}
                  </span>
                </div>
              ))}
            </div>

            <p style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 18 }}>
              Costs are computed from published token prices at the moment each
              message was sent. Cache reads are counted at the full input rate,
              so the real bill is a touch lower than shown.
            </p>
          </>
        )}
      </div>
    </main>
  );
}

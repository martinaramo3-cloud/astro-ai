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

export default function AdminPage() {
  const [secret, setSecret] = useState("");
  const [data, setData] = useState<Summary | null>(null);
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

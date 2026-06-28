"use client";

import { useState } from "react";
import { getBrowserApiBase } from "../lib/api";
import PlaceAutocomplete from "../components/PlaceAutocomplete";

const API_BASE = getBrowserApiBase();

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Home() {
  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [form, setForm] = useState({ name: "", email: "", password: "", birth_date: "", birth_time: "", birth_place: "" });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const switchMode = (next: "signup" | "login") => {
    setMode(next);
    setMessage("");
  };

  const validate = () => {
    if (!EMAIL_RE.test(form.email)) {
      setMessage("Please enter a valid email address.");
      return false;
    }
    if (form.password.length < 6) {
      setMessage("Password must be at least 6 characters.");
      return false;
    }
    return true;
  };

  const handleSignup = async () => {
    setMessage("");
    if (!validate()) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || "Signup failed.");
        setLoading(false);
        return;
      }
      localStorage.setItem("user", JSON.stringify(data));
      setMessage("Account created successfully.");
      setTimeout(() => { window.location.href = "/chat"; }, 700);
    } catch {
      setMessage("Taking a moment to wake up — please try again in 30 seconds.");
    }
    setLoading(false);
  };

  const handleLogin = async () => {
    setMessage("");
    if (!EMAIL_RE.test(form.email)) {
      setMessage("Please enter a valid email address.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.email, password: form.password }),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || "Invalid email or password.");
        setLoading(false);
        return;
      }
      localStorage.setItem("user", JSON.stringify(data));
      window.location.href = "/chat";
    } catch {
      setMessage("Taking a moment to wake up — please try again in 30 seconds.");
    }
    setLoading(false);
  };

  return (
    <main className="px-6 pb-20 pt-10 text-white">
      <section className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="flex flex-col justify-center space-y-6 py-10">
          <div className="inline-flex w-fit rounded-full border border-violet-300/20 bg-violet-200/10 px-4 py-2 text-xs uppercase tracking-[0.28em] text-violet-100/80">
            Astraea Studio
          </div>
          <h1 className="max-w-xl text-5xl font-semibold leading-tight md:text-6xl">
            The stars have always known.
          </h1>
          <p className="max-w-md text-lg leading-8 text-white/60">
            Ask your astrologer anything — love, timing, patterns. Every answer comes from your chart.
          </p>
        </div>

        <div className="glass rounded-[2rem] p-6 shadow-2xl shadow-violet-950/30">
          {/* Mode toggle */}
          <div className="mb-6 flex rounded-2xl border border-white/10 bg-white/5 p-1">
            <button
              onClick={() => switchMode("signup")}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition ${mode === "signup" ? "bg-white text-slate-950" : "text-white/60 hover:text-white"}`}
            >
              Create account
            </button>
            <button
              onClick={() => switchMode("login")}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition ${mode === "login" ? "bg-white text-slate-950" : "text-white/60 hover:text-white"}`}
            >
              Log in
            </button>
          </div>

          {mode === "signup" ? (
            <>
              <div className="mb-6">
                <p className="text-sm uppercase tracking-[0.24em] text-white/45">Create your profile</p>
                <h2 className="mt-2 text-3xl font-semibold">Start your chart</h2>
                <p className="mt-3 text-sm leading-6 text-white/65">Your profile saves the basics so the astrologer can answer with your chart context already in place.</p>
              </div>
              <div className="space-y-4">
                <input name="name" placeholder="Full name" value={form.name} onChange={handleChange} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                <input name="password" type="password" placeholder="Password (min. 6 characters)" value={form.password} onChange={handleChange} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                <div className="grid gap-4 sm:grid-cols-2">
                  <input name="birth_date" type="date" value={form.birth_date} onChange={handleChange} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                  <input name="birth_time" type="time" value={form.birth_time} onChange={handleChange} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                </div>
                <PlaceAutocomplete value={form.birth_place} onChange={(v) => setForm({ ...form, birth_place: v })} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                <button onClick={handleSignup} disabled={loading} className="w-full rounded-2xl bg-gradient-to-r from-violet-200 to-white px-5 py-3 font-semibold text-slate-950 transition hover:opacity-90 disabled:opacity-60">
                  {loading ? "Creating account..." : "Create account"}
                </button>
                {message ? <p className="text-sm text-white/72">{message}</p> : null}
              </div>
            </>
          ) : (
            <>
              <div className="mb-6">
                <p className="text-sm uppercase tracking-[0.24em] text-white/45">Welcome back</p>
                <h2 className="mt-2 text-3xl font-semibold">Log in</h2>
                <p className="mt-3 text-sm leading-6 text-white/65">Enter your email and password to continue your readings.</p>
              </div>
              <div className="space-y-4">
                <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                <input name="password" type="password" placeholder="Password" value={form.password} onChange={handleChange} className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none" />
                <button onClick={handleLogin} disabled={loading} className="w-full rounded-2xl bg-gradient-to-r from-violet-200 to-white px-5 py-3 font-semibold text-slate-950 transition hover:opacity-90 disabled:opacity-60">
                  {loading ? "Logging in..." : "Log in"}
                </button>
                {message ? <p className="text-sm text-white/72">{message}</p> : null}
              </div>
            </>
          )}
        </div>
      </section>

    </main>
  );
}

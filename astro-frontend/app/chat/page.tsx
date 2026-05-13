"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { getBrowserApiBase } from "../../lib/api";
import PlaceAutocomplete from "../../components/PlaceAutocomplete";

type User = {
  id: number;
  name: string;
  email: string;
  birth_date: string;
  birth_time: string;
  birth_place: string;
  subscription_tier?: string;
};

type UsageStatus = {
  tier: string;
  tier_label: string;
  model: string;
  daily_token_limit: number | null;
  tokens_used_today: number;
  tokens_remaining_today: number | null;
};

type SavedProfile = {
  id: number;
  owner_user_id: number;
  label: string;
  person_name: string;
  relationship_type?: string;
  birth_date: string;
  birth_time: string;
  birth_place: string;
};

type Message = { role: "user" | "assistant"; content: string };
type ChatSession = {
  id: number;
  owner_user_id: number;
  profile_id: number | null;
  title: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
};

const DEFAULT_MESSAGE: Message = {
  role: "assistant",
  content:
    "Welcome back. Ask about love, timing, emotional patterns, or your life direction.",
};

const API_BASE = getBrowserApiBase();

export default function ChatPage() {
  const [user] = useState<User | null>(() => {
    if (typeof window === "undefined") return null;
    const savedUser = window.localStorage.getItem("user");
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [profiles, setProfiles] = useState<SavedProfile[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<SavedProfile | null>(null);
  const [showAddProfile, setShowAddProfile] = useState(false);
  const [usage, setUsage] = useState<UsageStatus | null>(null);
  const [newProfile, setNewProfile] = useState({
    label: "",
    person_name: "",
    relationship_type: "",
    birth_date: "",
    birth_time: "",
    birth_place: "",
  });

  const [messages, setMessages] = useState<Message[]>([DEFAULT_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (user === null) {
      window.location.href = "/";
    }
  }, [user]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const loadData = async () => {
      if (!user) return;

      try {
        const [profilesRes, sessionsRes, usageRes] = await Promise.all([
          fetch(`${API_BASE}/profiles/${user.id}`),
          fetch(`${API_BASE}/chat-sessions/${user.id}`),
          fetch(`${API_BASE}/subscription/usage/${user.id}`),
        ]);
        const profilesData = await profilesRes.json();
        const sessionsData = await sessionsRes.json();
        const usageData = await usageRes.json();
        if (profilesRes.ok) setProfiles(profilesData);
        if (sessionsRes.ok) setSessions(sessionsData);
        if (usageRes.ok) setUsage(usageData);
      } catch (e) {
        console.error("Failed to load chat data", e);
      }
    };

    loadData();
  }, [user]);

  const profileLine = useMemo(() => {
    if (!user) return "Loading chart profile...";
    return `${user.name} · ${user.birth_date} · ${user.birth_time} · ${user.birth_place}`;
  }, [user]);

  const buildSessionTitle = (history: Message[]) => {
    const firstUserMessage = history.find((message) => message.role === "user")?.content?.trim();
    if (!firstUserMessage) {
      return selectedProfile ? `Chat with ${selectedProfile.label}` : "New chart chat";
    }

    const compact = firstUserMessage.replace(/\s+/g, " ").trim();
    return compact.length > 52 ? `${compact.slice(0, 52)}...` : compact;
  };

  const persistSession = async (history: Message[]) => {
    if (!user) return;

    const title = buildSessionTitle(history);
    const payload = {
      title,
      profile_id: selectedProfile?.id ?? null,
      messages: history,
    };

    try {
      const response = await fetch(
        currentSessionId
          ? `${API_BASE}/chat-sessions/${currentSessionId}`
          : `${API_BASE}/chat-sessions`,
        {
          method: currentSessionId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(
            currentSessionId
              ? payload
              : {
                  owner_user_id: user.id,
                  ...payload,
                },
          ),
        },
      );
      const data = await response.json();
      if (!response.ok) return;

      setCurrentSessionId(data.id);
      setSessions((prev) => {
        const next = [data, ...prev.filter((session) => session.id !== data.id)];
        return next;
      });
    } catch (error) {
      console.error("Failed to persist session", error);
    }
  };

  const startNewChat = (profile: SavedProfile | null = selectedProfile) => {
    setCurrentSessionId(null);
    setSelectedProfile(profile);
    setMessages([DEFAULT_MESSAGE]);
    setInput("");
  };

  const openSession = (session: ChatSession) => {
    setCurrentSessionId(session.id);
    setMessages(session.messages.length ? session.messages : [DEFAULT_MESSAGE]);
    setInput("");
    const matchingProfile = profiles.find((profile) => profile.id === session.profile_id) ?? null;
    setSelectedProfile(matchingProfile);
  };

  const sendMessage = async () => {
    if (!input.trim() || !user || loading) return;

    const userText = input.trim();
    const nextHistory = [...messages, { role: "user" as const, content: userText }];

    setMessages(nextHistory);
    setInput("");
    setLoading(true);

    try {
      const endpoint = selectedProfile
        ? `${API_BASE}/ask-saved-compatibility`
        : `${API_BASE}/ask-astrologer`;

      const body = selectedProfile
        ? {
            owner_user_id: user.id,
            profile_id: selectedProfile.id,
            question: userText,
            history: nextHistory,
          }
        : {
            birth_date: user.birth_date,
            birth_time: user.birth_time,
            birth_place: user.birth_place,
            question: userText,
            history: nextHistory,
            user_id: user.id,
          };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      const finalMessages = [
        ...nextHistory,
        {
          role: "assistant" as const,
          content: response.ok
            ? data.answer || "No answer came back."
            : data.detail || "The astrologer service returned an error.",
        },
      ];
      setMessages(finalMessages);
      await persistSession(finalMessages);
    } catch {
      const fallbackMessages = [
        ...nextHistory,
        {
          role: "assistant" as const,
          content: "Something went wrong connecting to the backend.",
        },
      ];
      setMessages(fallbackMessages);
      await persistSession(fallbackMessages);
    }

    setLoading(false);
  };

  const saveProfile = async () => {
    if (!user) return;
    if (
      !newProfile.label ||
      !newProfile.person_name ||
      !newProfile.birth_date ||
      !newProfile.birth_time ||
      !newProfile.birth_place
    ) {
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          owner_user_id: user.id,
          ...newProfile,
        }),
      });

      const data = await res.json();

      if (res.ok) {
        setProfiles((prev) => [data, ...prev]);
        setSelectedProfile(data);
        setShowAddProfile(false);
        setNewProfile({
          label: "",
          person_name: "",
          relationship_type: "",
          birth_date: "",
          birth_time: "",
          birth_place: "",
        });
      } else {
        console.error(data);
      }
    } catch (e) {
      console.error("Failed to save profile", e);
    }
  };

  const logout = () => {
    localStorage.removeItem("user");
    window.location.href = "/";
  };

  return (
    <main className="px-6 py-10 text-white">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[320px_1fr]">
        <aside className="glass rounded-[2rem] p-6">
          <p className="text-sm uppercase tracking-[0.24em] text-white/45">
            Your chart profile
          </p>
          <h1 className="mt-3 text-3xl font-semibold">Astrologer Chat</h1>
          <p className="mt-4 text-sm leading-7 text-white/68">
            Use this space for relationship questions, emotional patterns, career
            direction, or current themes.
          </p>

          <div className="mt-6 rounded-3xl border border-white/10 bg-white/5 p-4 text-sm leading-7 text-white/75">
            {profileLine}
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between">
              <p className="text-sm uppercase tracking-[0.24em] text-white/45">
                Chats
              </p>
              <button
                onClick={() => startNewChat()}
                className="rounded-full border border-white/15 px-3 py-1 text-xs hover:bg-white/10"
              >
                + New
              </button>
            </div>

            <div className="mt-3 space-y-2">
              {sessions.length === 0 ? (
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white/55">
                  Your saved chat history will appear here.
                </div>
              ) : (
                sessions.map((session) => {
                  const profile = profiles.find((item) => item.id === session.profile_id);
                  const isActive = session.id === currentSessionId;
                  return (
                    <button
                      key={session.id}
                      onClick={() => openSession(session)}
                      className={`w-full rounded-2xl px-4 py-3 text-left text-sm ${
                        isActive
                          ? "bg-white text-slate-950"
                          : "border border-white/10 bg-white/5 text-white"
                      }`}
                    >
                      <div className="font-medium">{session.title}</div>
                      <div className="text-xs opacity-75">
                        {profile ? `You + ${profile.label}` : "Just me"}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          <div className="mt-6">
            <div className="flex items-center justify-between">
              <p className="text-sm uppercase tracking-[0.24em] text-white/45">
                Saved people
              </p>
              <button
                onClick={() => setShowAddProfile((prev) => !prev)}
                className="rounded-full border border-white/15 px-3 py-1 text-xs hover:bg-white/10"
              >
                + Add
              </button>
            </div>

            <div className="mt-3 space-y-2">
              <button
                onClick={() => startNewChat(null)}
                className={`w-full rounded-2xl px-4 py-3 text-left text-sm ${
                  !selectedProfile
                    ? "bg-white text-slate-950"
                    : "border border-white/10 bg-white/5 text-white"
                }`}
              >
                Just me
              </button>

              {profiles.map((profile) => (
                <button
                  key={profile.id}
                  onClick={() => startNewChat(profile)}
                  className={`w-full rounded-2xl px-4 py-3 text-left text-sm ${
                    selectedProfile?.id === profile.id
                      ? "bg-white text-slate-950"
                      : "border border-white/10 bg-white/5 text-white"
                  }`}
                >
                  <div className="font-medium">{profile.label}</div>
                  <div className="text-xs opacity-75">{profile.person_name}</div>
                </button>
              ))}
            </div>

            {showAddProfile && (
              <div className="mt-4 space-y-3 rounded-3xl border border-white/10 bg-white/5 p-4">
                <input
                  placeholder="Label (My boyfriend)"
                  value={newProfile.label}
                  onChange={(e) =>
                    setNewProfile({ ...newProfile, label: e.target.value })
                  }
                  className="w-full rounded-xl bg-slate-950/70 px-3 py-2 text-sm outline-none"
                />
                <input
                  placeholder="Person name"
                  value={newProfile.person_name}
                  onChange={(e) =>
                    setNewProfile({ ...newProfile, person_name: e.target.value })
                  }
                  className="w-full rounded-xl bg-slate-950/70 px-3 py-2 text-sm outline-none"
                />
                <input
                  placeholder="Relationship type"
                  value={newProfile.relationship_type}
                  onChange={(e) =>
                    setNewProfile({
                      ...newProfile,
                      relationship_type: e.target.value,
                    })
                  }
                  className="w-full rounded-xl bg-slate-950/70 px-3 py-2 text-sm outline-none"
                />
                <input
                  type="date"
                  value={newProfile.birth_date}
                  onChange={(e) =>
                    setNewProfile({ ...newProfile, birth_date: e.target.value })
                  }
                  className="w-full rounded-xl bg-slate-950/70 px-3 py-2 text-sm outline-none"
                />
                <input
                  type="time"
                  value={newProfile.birth_time}
                  onChange={(e) =>
                    setNewProfile({ ...newProfile, birth_time: e.target.value })
                  }
                  className="w-full rounded-xl bg-slate-950/70 px-3 py-2 text-sm outline-none"
                />
                <PlaceAutocomplete
                  value={newProfile.birth_place}
                  onChange={(v) => setNewProfile({ ...newProfile, birth_place: v })}
                  placeholder="Birth place"
                  className="w-full rounded-xl bg-slate-950/70 px-3 py-2 text-sm outline-none"
                />
                <button
                  onClick={saveProfile}
                  className="w-full rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-950"
                >
                  Save person
                </button>
              </div>
            )}
          </div>

          <div className="mt-6 space-y-3 text-sm text-white/70">
            <p>Good prompts:</p>
            <p>“Why do I pull away in relationships?”</p>
            <p>“What career pattern stands out most in my chart?”</p>
            <p>“What does this month activate for me emotionally?”</p>
          </div>

          <button
            onClick={logout}
            className="mt-8 rounded-full border border-white/15 px-5 py-3 text-sm font-medium transition hover:bg-white/10"
          >
            Log out
          </button>
        </aside>

        <section className="glass flex min-h-[72vh] flex-col rounded-[2rem] p-5">
          <div className="mb-4 flex items-center justify-between border-b border-white/10 px-2 pb-4">
            <div>
              <p className="text-sm uppercase tracking-[0.24em] text-white/45">
                Private conversation
              </p>
              <p className="mt-1 text-white/70">
                {selectedProfile
                  ? `Compatibility mode: you + ${selectedProfile.label}`
                  : "Clear, premium guidance grounded in your chart."}
              </p>
            </div>
            {usage && (
              <div className="flex flex-col items-end gap-1">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold tracking-wide ${
                    usage.tier === "premium"
                      ? "bg-violet-400/20 text-violet-200"
                      : usage.tier === "standard"
                      ? "bg-sky-400/20 text-sky-200"
                      : "bg-white/10 text-white/60"
                  }`}
                >
                  {usage.tier === "premium" ? "✦ Premium" : usage.tier === "standard" ? "◈ Standard" : "Free"}
                </span>
                <span className="text-xs text-white/35">
                  {usage.daily_token_limit
                    ? `${usage.tokens_used_today.toLocaleString()} / ${usage.daily_token_limit.toLocaleString()} tokens`
                    : "Unlimited tokens"}
                </span>
              </div>
            )}
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-2 pb-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`max-w-[85%] rounded-[1.6rem] px-5 py-4 text-sm leading-7 shadow-lg ${
                  message.role === "user"
                    ? "ml-auto bg-white text-slate-950"
                    : "border border-white/10 bg-slate-950/60 text-white"
                }`}
              >
                {message.content}
              </div>
            ))}
            {loading ? (
              <div className="max-w-[85%] rounded-[1.6rem] border border-white/10 bg-slate-950/60 px-5 py-4 text-sm leading-7 text-white">
                Reading your chart...
              </div>
            ) : null}
            <div ref={endRef} />
          </div>

          <div className="mt-3 flex gap-3 border-t border-white/10 pt-4">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                selectedProfile
                  ? `Ask about you and ${selectedProfile.label}...`
                  : "Ask your astrologer..."
              }
              rows={3}
              className="min-h-[88px] flex-1 resize-none rounded-[1.6rem] border border-white/10 bg-slate-950/70 px-4 py-3 outline-none"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
            />
            <button
              onClick={sendMessage}
              disabled={loading}
              className="self-end rounded-full bg-gradient-to-r from-violet-200 to-white px-6 py-3 font-semibold text-slate-950 transition hover:opacity-90 disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </section>
      </div>
    </main>
  );
}

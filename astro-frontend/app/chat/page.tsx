"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiFetch, clearAuth, errorMessage, saveAuth } from "../../lib/api";
import PlaceAutocomplete from "../../components/PlaceAutocomplete";
import ChartWheel, { type NatalChart } from "../../components/ChartWheel";
import BirthDetailsEditor from "../../components/BirthDetailsEditor";
import AttachedImages from "../../components/AttachedImages";
import CosmicAlert from "../../components/CosmicAlert";
import ZodiMark from "../../components/ZodiMark";
import Wordmark from "../../components/Wordmark";
import { ThemeToggle, useTheme } from "../../components/ThemeProvider";
import { useSpeechInput } from "../../components/useSpeechInput";

const SIGN_GLYPH: Record<string, string> = {
  Aries: "♈︎", Taurus: "♉︎", Gemini: "♊︎", Cancer: "♋︎", Leo: "♌︎", Virgo: "♍︎",
  Libra: "♎︎", Scorpio: "♏︎", Sagittarius: "♐︎", Capricorn: "♑︎", Aquarius: "♒︎", Pisces: "♓︎",
};
const PLANET_GLYPH: Record<string, string> = {
  Sun: "☉︎", Moon: "☽︎", Mercury: "☿︎", Venus: "♀︎", Mars: "♂︎",
  Jupiter: "♃︎", Saturn: "♄︎", Uranus: "♅︎", Neptune: "♆︎", Pluto: "♇︎",
};

const STARTERS = [
  "Why do I pull away in relationships?",
  "What does this month activate for me?",
  "What pattern runs my career?",
];

type User = {
  id: number;
  name: string;
  email: string;
  birth_date: string;
  birth_time: string;
  birth_place: string;
  birth_time_known?: boolean;
  subscription_tier?: string;
};

type ModelOption = { key: string; label: string; blurb: string };

type UsageStatus = {
  tier: string;
  tier_label: string;
  model: string;
  available_models: ModelOption[];
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
  birth_time_known?: boolean;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  // Pictures sent with this message, kept so a reopened chat still shows them.
  attachment_ids?: number[];
};

type PendingImage = {
  id: number;          // server-side attachment id
  previewUrl: string;  // local object URL, so nothing is re-downloaded to show it
  name: string;
};
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
    "Ask me anything — love, timing, the patterns you keep circling. I read from your chart, not a horoscope.",
};

const fieldStyle: React.CSSProperties = {
  border: "1px solid var(--line-2)",
  background: "var(--ground)",
  borderRadius: 14,
  padding: "10px 13px",
  fontSize: 14,
  width: "100%",
  outline: "none",
};

export default function ChatPage() {
  const { theme } = useTheme();
  const night = theme === "night";

  const [user, setUser] = useState<User | null>(() => {
    if (typeof window === "undefined") return null;
    const savedUser = window.localStorage.getItem("user");
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [profiles, setProfiles] = useState<SavedProfile[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null);
  const [selectedProfile, setSelectedProfile] = useState<SavedProfile | null>(null);
  const [showAddProfile, setShowAddProfile] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);
  const [usage, setUsage] = useState<UsageStatus | null>(null);
  const [newProfile, setNewProfile] = useState({
    label: "",
    person_name: "",
    relationship_type: "",
    birth_date: "",
    birth_time: "",
    birth_place: "",
    birth_time_known: true,
  });

  const [messages, setMessages] = useState<Message[]>([DEFAULT_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [chartOpen, setChartOpen] = useState(false);
  const [chart, setChart] = useState<NatalChart | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [accountOpen, setAccountOpen] = useState(false);
  // Which set of birth details is open for editing: your own, or one saved
  // person. Null when the editor is closed.
  const [editing, setEditing] = useState<{ kind: "me" } | { kind: "person"; profile: SavedProfile } | null>(null);
  const [deleteArmed, setDeleteArmed] = useState(false);
  const [accountBusy, setAccountBusy] = useState("");
  // Anything irreversible routes through one confirmation dialog.
  const [confirmAction, setConfirmAction] = useState<{
    title: string;
    body: string;
    confirmLabel: string;
    run: () => Promise<void> | void;
  } | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  // Images picked for the next message. They upload as soon as they're chosen,
  // so by the time the question is sent there is only an id to attach.
  const [pending, setPending] = useState<PendingImage[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  // Dictation appends to whatever is already typed.
  const { supported: micSupported, listening, toggle: toggleMic } = useSpeechInput(
    (text) => setInput((prev) => (prev ? `${prev} ${text}` : text)),
  );

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
          apiFetch(`/profiles/${user.id}`),
          apiFetch(`/chat-sessions/${user.id}`),
          apiFetch(`/subscription/usage/${user.id}`),
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

  // Pick the active model once usage (and its available models) loads.
  useEffect(() => {
    if (!usage) return;
    const keys = usage.available_models?.map((m) => m.key) ?? [];
    if (keys.length === 0) return;
    const saved = typeof window !== "undefined" ? window.localStorage.getItem("model") : null;
    setSelectedModel(saved && keys.includes(saved) ? saved : keys[keys.length - 1]);
  }, [usage]);

  const selectModel = (key: string) => {
    setSelectedModel(key);
    if (typeof window !== "undefined") window.localStorage.setItem("model", key);
  };

  // Fetch and show the user's natal chart wheel (cached after first open).
  const openChart = async () => {
    if (!user) return;
    setSidebarOpen(false);
    setChartOpen(true);
    if (chart || chartLoading) return;
    setChartLoading(true);
    setChartError("");
    try {
      const res = await apiFetch("/natal-chart", {
        method: "POST",
        body: JSON.stringify({
          birth_date: user.birth_date,
          birth_time: user.birth_time,
          birth_place: user.birth_place,
          birth_time_known: user.birth_time_known ?? true,
        }),
      });
      const data = await res.json();
      if (res.ok) setChart(data);
      else setChartError(data.detail || "Could not build your chart.");
    } catch {
      setChartError("Could not reach the chart service. Try again in a moment.");
    }
    setChartLoading(false);
  };

  // Re-fetch token usage so the counter reflects what was just spent.
  const refreshUsage = async () => {
    if (!user) return;
    try {
      const res = await apiFetch(`/subscription/usage/${user.id}`);
      if (res.ok) setUsage(await res.json());
    } catch {
      /* non-critical */
    }
  };

  const birthLine = useMemo(() => {
    if (!user) return "";
    const when = user.birth_time_known === false ? "time unknown" : user.birth_time;
    return `${user.birth_date} · ${when} · ${user.birth_place}`;
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
      const response = await apiFetch(
        currentSessionId ? `/chat-sessions/${currentSessionId}` : "/chat-sessions",
        {
          method: currentSessionId ? "PATCH" : "POST",
          body: JSON.stringify(
            currentSessionId ? payload : { owner_user_id: user.id, ...payload },
          ),
        },
      );
      const data = await response.json();
      if (!response.ok) return;

      setCurrentSessionId(data.id);
      setSessions((prev) => [data, ...prev.filter((session) => session.id !== data.id)]);
    } catch (error) {
      console.error("Failed to persist session", error);
    }
  };

  const startNewChat = (profile: SavedProfile | null = selectedProfile) => {
    setCurrentSessionId(null);
    setSelectedProfile(profile);
    setMessages([DEFAULT_MESSAGE]);
    setInput("");
    setSidebarOpen(false);
  };

  const openSession = (session: ChatSession) => {
    setCurrentSessionId(session.id);
    setMessages(session.messages.length ? session.messages : [DEFAULT_MESSAGE]);
    setInput("");
    const matchingProfile = profiles.find((profile) => profile.id === session.profile_id) ?? null;
    setSelectedProfile(matchingProfile);
    setSidebarOpen(false);
  };

  // `overrideText` lets prompts elsewhere in the UI (starters, the cosmic
  // alert) send a question in one tap.
  const canAttach = usage ? usage.tier !== "free" : false;
  const MAX_IMAGES = 3;

  const pickImages = async (files: FileList | null) => {
    if (!files?.length) return;
    setUploadError("");

    const room = MAX_IMAGES - pending.length;
    if (room <= 0) {
      setUploadError(`You can attach up to ${MAX_IMAGES} images per question.`);
      return;
    }

    setUploading(true);
    for (const file of Array.from(files).slice(0, room)) {
      const form = new FormData();
      form.append("file", file);
      try {
        // No Content-Type header: the browser has to set the multipart boundary.
        const res = await apiFetch("/attachments", { method: "POST", body: form });
        const data = await res.json();
        if (res.ok) {
          setPending((prev) => [
            ...prev,
            { id: data.id, previewUrl: URL.createObjectURL(file), name: file.name },
          ]);
        } else {
          setUploadError(errorMessage(data, "Could not upload that image."));
        }
      } catch {
        setUploadError("Could not reach the server. Try again in a moment.");
      }
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  };

  const removePending = async (image: PendingImage) => {
    setPending((prev) => prev.filter((p) => p.id !== image.id));
    URL.revokeObjectURL(image.previewUrl);
    // Take it off the server too, so an unsent picture doesn't linger there.
    try {
      await apiFetch(`/attachments/${image.id}`, { method: "DELETE" });
    } catch {
      /* the row is harmless if this fails */
    }
  };

  const sendMessage = async (overrideText?: string, baseMessages?: Message[]) => {
    const userText = (overrideText ?? input).trim();
    if (!userText || !user || loading) return;
    const base = baseMessages ?? messages;

    // A retried or edited message doesn't re-send the pictures; they belong to
    // the turn that was originally typed.
    const sending = overrideText === undefined ? pending : [];
    const attachmentIds = sending.map((image) => image.id);

    const nextHistory: Message[] = [
      ...base,
      {
        role: "user" as const,
        content: userText,
        ...(attachmentIds.length ? { attachment_ids: attachmentIds } : {}),
      },
    ];

    setMessages(nextHistory);
    setInput("");
    if (sending.length) setPending([]);
    setUploadError("");
    setLoading(true);

    const endpoint = selectedProfile ? "/ask-saved-compatibility" : "/ask-astrologer";

    const body = selectedProfile
      ? {
          owner_user_id: user.id,
          profile_id: selectedProfile.id,
          question: userText,
          history: nextHistory,
          model: selectedModel ?? undefined,
        }
      : {
          birth_date: user.birth_date,
          birth_time: user.birth_time,
          birth_place: user.birth_place,
          birth_time_known: user.birth_time_known ?? true,
          question: userText,
          history: nextHistory,
          attachment_ids: attachmentIds.length ? attachmentIds : undefined,
          user_id: user.id,
          model: selectedModel ?? undefined,
          // So the open conversation isn't also listed as a past one.
          session_id: currentSessionId ?? undefined,
        };

    const attemptFetch = async (attemptsLeft: number): Promise<void> => {
      try {
        const response = await apiFetch(endpoint, {
          method: "POST",
          body: JSON.stringify(body),
        });

        const data = await response.json();

        const answerText = response.ok
          ? data.answer || "No answer came back."
          : data.detail || "The astrologer service returned an error.";

        const finalMessages = [
          ...nextHistory,
          { role: "assistant" as const, content: answerText },
        ];
        setMessages(finalMessages);
        await persistSession(finalMessages);
        refreshUsage();
      } catch {
        if (attemptsLeft > 1) {
          await new Promise((r) => setTimeout(r, 4000));
          return attemptFetch(attemptsLeft - 1);
        }
        const fallbackMessages = [
          ...nextHistory,
          { role: "assistant" as const, content: "Something went wrong. Please try again." },
        ];
        setMessages(fallbackMessages);
        await persistSession(fallbackMessages);
      }
    };

    await attemptFetch(4);
    setLoading(false);
  };

  const saveProfile = async () => {
    if (!user || savingProfile) return;

    // Say which field is missing — silently doing nothing just looks broken.
    const missing = [
      [newProfile.label, "a label, like “My boyfriend”"],
      [newProfile.person_name, "their name"],
      [newProfile.birth_date, "their birth date"],
      ...(newProfile.birth_time_known
        ? [[newProfile.birth_time, "their birth time, or tick that it's unknown"]]
        : []),
      [newProfile.birth_place, "their birth place"],
    ].find(([value]) => !String(value).trim());

    if (missing) {
      setProfileError(`Please add ${missing[1]}.`);
      return;
    }

    setProfileError("");
    setSavingProfile(true);
    try {
      const res = await apiFetch("/profiles", {
        method: "POST",
        body: JSON.stringify({ owner_user_id: user.id, ...newProfile }),
      });

      const data = await res.json();

      if (res.ok) {
        setProfiles((prev) => [data, ...prev]);
        setSelectedProfile(data);
        setShowAddProfile(false);
        setNewProfile({
          label: "", person_name: "", relationship_type: "",
          birth_date: "", birth_time: "", birth_place: "",
          birth_time_known: true,
        });
      } else {
        setProfileError(data.detail || "Could not save this person.");
      }
    } catch {
      setProfileError("Could not reach the server. Try again in a moment.");
    }
    setSavingProfile(false);
  };

  const deleteSession = (session: ChatSession) =>
    setConfirmAction({
      title: "Delete this conversation?",
      body: `“${session.title}” will be permanently deleted. This cannot be undone.`,
      confirmLabel: "Delete conversation",
      run: async () => {
        try {
          const res = await apiFetch(`/chat-sessions/${session.id}`, { method: "DELETE" });
          if (!res.ok) return;
          setSessions((prev) => prev.filter((s) => s.id !== session.id));
          // If the open conversation was the one removed, start fresh.
          if (currentSessionId === session.id) startNewChat(null);
        } catch {
          /* leaving it on screen is better than a false success */
        }
      },
    });

  /** Your own details changed, so the cached chart is now for the wrong moment. */
  const onMeSaved = (saved: Record<string, unknown>) => {
    // Merged rather than replaced: the update response is a UserResponse,
    // which omits the email, and overwriting would blank it locally.
    const next = { ...(user ?? {}), ...saved } as unknown as User;
    setUser(next);
    saveAuth(next as unknown as Record<string, unknown>);
    setChart(null);
    setEditing(null);
  };

  const onPersonSaved = (saved: Record<string, unknown>) => {
    const next = saved as unknown as SavedProfile;
    setProfiles((prev) => prev.map((p) => (p.id === next.id ? next : p)));
    setSelectedProfile((prev) => (prev?.id === next.id ? next : prev));
    setEditing(null);
  };

  const deleteProfile = (profile: SavedProfile) =>
    setConfirmAction({
      title: `Remove ${profile.label}?`,
      body: `${profile.person_name}'s birth details will be permanently deleted, and you'll no longer be able to read your chart against theirs. This cannot be undone.`,
      confirmLabel: "Remove person",
      run: async () => {
        try {
          const res = await apiFetch(`/profiles/${profile.id}`, { method: "DELETE" });
          if (!res.ok) return;
          setProfiles((prev) => prev.filter((p) => p.id !== profile.id));
          // Drop back to reading just their own chart.
          if (selectedProfile?.id === profile.id) startNewChat(null);
        } catch {
          /* leave it on screen rather than claim success */
        }
      },
    });

  /** Re-ask an earlier question, discarding everything that followed it. */
  const submitEdit = async (conversationIndex: number) => {
    const text = editDraft.trim();
    if (!text) return;
    // `conversation` drops the leading greeting, so shift back to `messages`.
    const offset = messages.length - conversation.length;
    const truncated = messages.slice(0, offset + conversationIndex);
    setEditingIndex(null);
    setMessages(truncated);
    await sendMessage(text, truncated);
  };

  const downloadMyData = async () => {
    setAccountBusy("export");
    try {
      const res = await apiFetch("/me/export");
      if (!res.ok) return;
      const data = await res.json();
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = `zodi-my-data-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      /* nothing downloaded; the button simply re-enables */
    }
    setAccountBusy("");
  };

  const deleteAccount = async () => {
    setAccountBusy("delete");
    try {
      const res = await apiFetch("/me", { method: "DELETE" });
      if (res.ok) {
        clearAuth();
        window.location.href = "/";
        return;
      }
    } catch {
      /* fall through and re-enable */
    }
    setAccountBusy("");
  };

  const logout = async () => {
    // Revoke the token server-side so it can't be reused, then clear locally.
    try {
      await apiFetch("/logout", { method: "POST" });
    } catch {
      /* clearing local state matters more than the round trip */
    }
    clearAuth();
    window.location.href = "/";
  };

  const conversation = messages.filter(
    (m, i) => !(i === 0 && m.role === "assistant" && m.content === DEFAULT_MESSAGE.content),
  );
  const isFresh = conversation.length === 0;

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: "var(--sky)" }}>
      {/* Backdrop for the mobile drawer */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 lg:hidden"
          style={{ background: "rgba(0,0,0,0.4)" }}
          aria-hidden="true"
        />
      )}

      {/* ─── Sidebar ─── */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[86%] max-w-[300px] transform flex-col overflow-y-auto transition-transform duration-300 ease-out lg:static lg:w-[268px] lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        style={{
          background: "var(--ground-2)",
          borderRight: "1px solid var(--line)",
          paddingTop: "calc(18px + env(safe-area-inset-top, 0px))",
          paddingBottom: 18,
          paddingLeft: 16,
          paddingRight: 16,
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ZodiMark size={38} night={night} />
            <Wordmark zSize={34} restSize={20} />
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            aria-label="Close menu"
            className="-mr-2 grid shrink-0 place-items-center lg:hidden"
            style={{ width: 44, height: 44, color: "var(--ink-3)", fontSize: 18 }}
          >
            ✕
          </button>
        </div>

        <button
          onClick={() => startNewChat(null)}
          className="mt-5 w-full text-left"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--line-2)",
            borderRadius: 16,
            padding: "12px 16px",
            fontSize: 14,
            fontWeight: 300,
          }}
        >
          + New conversation
        </button>

        <button
          onClick={openChart}
          className="mt-2 w-full text-left"
          style={{
            background: "transparent",
            border: "1px solid var(--line-2)",
            borderRadius: 16,
            padding: "12px 16px",
            fontSize: 14,
            fontWeight: 300,
            color: "var(--ink-2)",
          }}
        >
          ✦ View my chart
        </button>

        {/* Conversations */}
        {sessions.length > 0 && (
          <div className="mt-6">
            <p className="micro-label">Conversations</p>
            <div className="mt-2 flex flex-col gap-1">
              {sessions.slice(0, 12).map((session) => {
                const active = session.id === currentSessionId;
                return (
                  <div
                    key={session.id}
                    className="group flex items-center gap-1"
                    style={{
                      borderRadius: 14,
                      background: active ? "var(--gold-soft)" : "transparent",
                    }}
                  >
                    <button
                      onClick={() => openSession(session)}
                      className="min-w-0 flex-1 truncate text-left"
                      style={{
                        padding: "11px 14px",
                        fontSize: 14,
                        fontWeight: 300,
                        color: active ? "var(--ink)" : "var(--ink-2)",
                      }}
                    >
                      {session.title}
                    </button>
                    <button
                      onClick={() => deleteSession(session)}
                      aria-label={`Delete "${session.title}"`}
                      title="Delete conversation"
                      className="row-action"
                      style={{ fontSize: 14 }}
                    >
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Saved people */}
        <div className="mt-6">
          <div className="flex items-center justify-between">
            <p className="micro-label">People</p>
            <button
              onClick={() => {
                setProfileError("");
                setShowAddProfile((prev) => !prev);
              }}
              style={{ fontSize: 12, color: "var(--gold-deep)" }}
            >
              + Add
            </button>
          </div>

          <div className="mt-2 flex flex-col gap-1">
            <button
              onClick={() => startNewChat(null)}
              className="w-full text-left"
              style={{
                borderRadius: 14,
                padding: "11px 14px",
                fontSize: 14,
                fontWeight: 300,
                background: !selectedProfile ? "var(--gold-soft)" : "transparent",
                color: !selectedProfile ? "var(--ink)" : "var(--ink-2)",
              }}
            >
              Just me
            </button>
            {profiles.map((profile) => {
              const active = selectedProfile?.id === profile.id;
              return (
                <div
                  key={profile.id}
                  className="group flex items-center gap-1"
                  style={{
                    borderRadius: 14,
                    background: active ? "var(--gold-soft)" : "transparent",
                  }}
                >
                  <button
                    onClick={() => startNewChat(profile)}
                    className="min-w-0 flex-1 text-left"
                    style={{
                      padding: "11px 14px",
                      fontSize: 14,
                      fontWeight: 300,
                      color: active ? "var(--ink)" : "var(--ink-2)",
                    }}
                  >
                    <span className="block truncate">{profile.label}</span>
                    <span
                      className="block truncate"
                      style={{ fontSize: 12, color: "var(--ink-3)" }}
                    >
                      {profile.person_name}
                    </span>
                  </button>
                  <button
                    onClick={() => setEditing({ kind: "person", profile })}
                    aria-label={`Edit ${profile.label}`}
                    title="See and edit their details"
                    className="row-action"
                    style={{ fontSize: 13 }}
                  >
                    {"\u270E\uFE0E"}
                  </button>
                  <button
                    onClick={() => deleteProfile(profile)}
                    aria-label={`Remove ${profile.label}`}
                    title="Remove person"
                    className="row-action"
                    style={{ fontSize: 14 }}
                  >
                    ✕
                  </button>
                </div>
              );
            })}
          </div>

          {showAddProfile && (
            <div
              className="mt-3 flex flex-col gap-2"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--line)",
                borderRadius: 16,
                padding: 14,
              }}
            >
              <input
                placeholder="Label (My boyfriend)"
                value={newProfile.label}
                onChange={(e) => setNewProfile({ ...newProfile, label: e.target.value })}
                style={fieldStyle}
              />
              <input
                placeholder="Their name"
                value={newProfile.person_name}
                onChange={(e) => setNewProfile({ ...newProfile, person_name: e.target.value })}
                style={fieldStyle}
              />
              <input
                placeholder="Relationship (optional)"
                value={newProfile.relationship_type}
                onChange={(e) =>
                  setNewProfile({ ...newProfile, relationship_type: e.target.value })
                }
                style={fieldStyle}
              />
              <label className="block">
                <span className="micro-label mb-1 block">Birth date</span>
                <input
                  type="date"
                  value={newProfile.birth_date}
                  onChange={(e) => setNewProfile({ ...newProfile, birth_date: e.target.value })}
                  style={fieldStyle}
                />
              </label>
              {newProfile.birth_time_known && (
                <label className="block">
                  <span className="micro-label mb-1 block">Birth time</span>
                  <input
                    type="time"
                    value={newProfile.birth_time}
                    onChange={(e) => setNewProfile({ ...newProfile, birth_time: e.target.value })}
                    style={fieldStyle}
                  />
                </label>
              )}

              <label className="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox"
                  checked={!newProfile.birth_time_known}
                  onChange={(e) =>
                    setNewProfile({ ...newProfile, birth_time_known: !e.target.checked })
                  }
                  className="unknown-time-box"
                />
                <span style={{ fontSize: 13, color: "var(--ink-2)" }}>
                  They don&rsquo;t know their birth time
                </span>
              </label>

              {!newProfile.birth_time_known && (
                <div className="time-warning">
                  <p className="micro-label" style={{ letterSpacing: "0.18em" }}>
                    Birth time unknown
                  </p>
                  <p className="font-reading mt-1">
                    Without their exact birth time, we can&rsquo;t calculate their
                    Rising sign, houses, or certain degrees and aspects. Your
                    compatibility reading will still use the planetary placements
                    available from their birth date.
                  </p>
                </div>
              )}
              <PlaceAutocomplete
                value={newProfile.birth_place}
                onChange={(v) => setNewProfile({ ...newProfile, birth_place: v })}
                placeholder="Birth place"
                style={fieldStyle}
              />
              {profileError && (
                <p style={{ fontSize: 12, lineHeight: 1.5, color: "var(--gold-deep)" }}>
                  {profileError}
                </p>
              )}
              <button
                onClick={saveProfile}
                disabled={savingProfile}
                className="uppercase"
                style={{
                  borderRadius: 999,
                  padding: "11px 16px",
                  background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
                  color: "var(--on-gold)",
                  fontSize: 12,
                  letterSpacing: "0.16em",
                  opacity: savingProfile ? 0.7 : 1,
                }}
              >
                {savingProfile ? "Saving…" : "Save person"}
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          className="safe-bottom mt-auto flex items-center gap-3 pt-4"
          style={{ borderTop: "1px solid var(--line)" }}
        >
          <div
            className="grid h-[30px] w-[30px] place-items-center rounded-full"
            style={{ background: "var(--gold-soft)", color: "var(--gold-deep)", fontSize: 13 }}
          >
            {user?.name?.[0]?.toUpperCase() ?? "·"}
          </div>
          <button
            onClick={() => {
              setDeleteArmed(false);
              setAccountOpen(true);
              setSidebarOpen(false);
            }}
            className="min-w-0 flex-1 truncate text-left"
            style={{ fontSize: 14, fontWeight: 300 }}
          >
            {user?.name}
          </button>
          <button
            onClick={logout}
            className="micro-label shrink-0"
            style={{ letterSpacing: "0.16em" }}
          >
            Log out
          </button>
        </div>
      </aside>

      {/* ─── Main column ─── */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header
          className="flex items-center justify-between gap-3"
          style={{
            // The inset has to live in the inline padding: an inline shorthand
            // would otherwise override a padding-top set by a class, and the
            // header would sit under the status bar where it can't be tapped.
            paddingTop: "calc(14px + env(safe-area-inset-top, 0px))",
            paddingBottom: 14,
            paddingLeft: 18,
            paddingRight: 18,
            borderBottom: "1px solid var(--line)",
            background: "var(--ground-2)",
          }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="-ml-2 grid shrink-0 place-items-center lg:hidden"
            // 44px is the smallest comfortable tap target; the glyph alone
            // gave about 16px of hit area.
            style={{ width: 44, height: 44, fontSize: 19, color: "var(--ink-2)" }}
          >
            ☰
          </button>

          <div className="min-w-0 flex-1">
            <p className="micro-label truncate" style={{ letterSpacing: "0.24em" }}>
              {selectedProfile
                ? `You + ${selectedProfile.label}`
                : `Talking with Zodi · ${night ? "Night" : "Day"} sky`}
            </p>
            <p
              className="font-reading truncate"
              style={{ fontSize: 16, color: "var(--ink-2)" }}
            >
              {birthLine}
            </p>
          </div>

          <ThemeToggle />
        </header>

        {/* Transcript */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[800px] px-[18px] py-6 lg:px-[30px]">
            <CosmicAlert onAsk={(question) => sendMessage(question)} />

            {isFresh && (
              <div className="zo-msg flex flex-col items-start gap-3 py-6">
                <div className="flex items-center gap-2">
                  <ZodiMark size={24} night={night} />
                  <span
                    className="micro-label"
                    style={{ color: "var(--gold-deep)", letterSpacing: "0.24em" }}
                  >
                    Zodi
                  </span>
                </div>
                <p
                  className="font-reading body-pretty"
                  style={{ fontSize: 18, lineHeight: 1.85, maxWidth: "62ch" }}
                >
                  {DEFAULT_MESSAGE.content}
                </p>
              </div>
            )}

            <div className="flex flex-col" style={{ gap: 26 }}>
              {conversation.map((message, index) => {
                const isUser = message.role === "user";
                const delay = Math.min(index * 60, 240);
                return (
                  <div
                    key={index}
                    className="zo-msg"
                    style={{
                      animationDelay: `${delay}ms`,
                      paddingTop: index === 0 ? 0 : 22,
                      borderTop: index === 0 ? "none" : "1px solid var(--line)",
                    }}
                  >
                    {isUser ? (
                      <div className="group flex flex-col items-end">
                        <span
                          className="micro-label mb-2"
                          style={{ letterSpacing: "0.24em" }}
                        >
                          You asked
                        </span>

                        {message.attachment_ids?.length ? (
                          <AttachedImages ids={message.attachment_ids} />
                        ) : null}

                        {editingIndex === index ? (
                          <div className="flex w-full flex-col items-end gap-2">
                            <textarea
                              value={editDraft}
                              onChange={(e) => setEditDraft(e.target.value)}
                              autoFocus
                              rows={3}
                              className="font-display w-full resize-none text-right"
                              style={{
                                fontSize: "clamp(20px, 3vw, 26px)",
                                lineHeight: 1.3,
                                background: "var(--surface)",
                                border: "1px solid var(--line-2)",
                                borderRadius: 16,
                                padding: "12px 16px",
                                outline: "none",
                              }}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                  e.preventDefault();
                                  submitEdit(index);
                                }
                                if (e.key === "Escape") setEditingIndex(null);
                              }}
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => setEditingIndex(null)}
                                className="micro-label"
                                style={{ letterSpacing: "0.16em", padding: "6px 12px" }}
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => submitEdit(index)}
                                className="uppercase"
                                style={{
                                  borderRadius: 999,
                                  padding: "7px 16px",
                                  background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
                                  color: "var(--on-gold)",
                                  fontSize: 10,
                                  letterSpacing: "0.16em",
                                }}
                              >
                                Ask again
                              </button>
                            </div>
                            <p style={{ fontSize: 11, color: "var(--ink-3)" }}>
                              Everything after this will be replaced.
                            </p>
                          </div>
                        ) : (
                          <>
                            <p
                              className="font-display text-right"
                              style={{
                                fontSize: "clamp(22px, 3.2vw, 30px)",
                                lineHeight: 1.24,
                                maxWidth: "26ch",
                                borderRight: "1px solid var(--gold)",
                                paddingRight: 18,
                              }}
                            >
                              {message.content}
                            </p>
                            <button
                              onClick={() => {
                                setEditDraft(message.content);
                                setEditingIndex(index);
                              }}
                              className="micro-label mt-1 opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100"
                              style={{ letterSpacing: "0.16em" }}
                            >
                              Edit
                            </button>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-col items-start">
                        <div className="mb-2 flex items-center gap-2">
                          <ZodiMark size={24} night={night} />
                          <span
                            className="micro-label"
                            style={{ color: "var(--gold-deep)", letterSpacing: "0.24em" }}
                          >
                            Zodi
                          </span>
                        </div>
                        <p
                          className="font-reading body-pretty whitespace-pre-wrap"
                          style={{ fontSize: 18, lineHeight: 1.85, maxWidth: "62ch" }}
                        >
                          {message.content}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Loading: the mark spins — there is no separate spinner. */}
              {loading && (
                <div
                  className="zo-msg flex flex-col items-start"
                  style={{
                    paddingTop: conversation.length ? 22 : 0,
                    borderTop: conversation.length ? "1px solid var(--line)" : "none",
                  }}
                >
                  <div className="mb-2 flex items-center gap-2">
                    <ZodiMark size={26} night={night} spin />
                    <span
                      className="micro-label"
                      style={{ color: "var(--gold-deep)", letterSpacing: "0.24em" }}
                    >
                      Zodi
                    </span>
                  </div>
                  <p
                    className="font-reading zo-dots italic"
                    style={{ fontSize: 17, color: "var(--ink-2)" }}
                  >
                    {night ? "Reading the night sky…" : "Reading the sky…"}
                  </p>
                </div>
              )}
            </div>

            <div ref={endRef} />
          </div>
        </div>

        {/* Composer */}
        <div
          className="safe-bottom"
          style={{ borderTop: "1px solid var(--line)", background: "var(--ground-2)" }}
        >
          <div className="mx-auto w-full max-w-[800px] px-[18px] py-4 lg:px-[30px]">
            {isFresh && !loading && (
              <div className="mb-3 flex flex-wrap gap-2">
                {STARTERS.map((starter) => (
                  <button
                    key={starter}
                    onClick={() => sendMessage(starter)}
                    className="font-reading"
                    style={{
                      borderRadius: 999,
                      border: "1px solid var(--line-2)",
                      padding: "9px 16px",
                      fontSize: 15,
                      color: "var(--ink-2)",
                    }}
                  >
                    {starter}
                  </button>
                ))}
              </div>
            )}

            {(pending.length > 0 || uploading || uploadError) && (
              <div className="mb-2 flex flex-wrap items-center gap-2">
                {pending.map((image) => (
                  <div
                    key={image.id}
                    className="relative"
                    style={{
                      borderRadius: 12,
                      overflow: "hidden",
                      border: "1px solid var(--line-2)",
                      background: "var(--surface)",
                    }}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={image.previewUrl}
                      alt={image.name}
                      style={{ width: 62, height: 62, objectFit: "cover", display: "block" }}
                    />
                    <button
                      onClick={() => removePending(image)}
                      aria-label={`Remove ${image.name}`}
                      className="absolute grid place-items-center"
                      style={{
                        top: 3, right: 3, width: 20, height: 20, borderRadius: 999,
                        background: "rgba(0,0,0,0.62)", color: "#fff", fontSize: 11,
                      }}
                    >
                      ✕
                    </button>
                  </div>
                ))}
                {uploading && (
                  <span style={{ fontSize: 13, color: "var(--ink-3)" }}>Uploading…</span>
                )}
                {uploadError && (
                  <span style={{ fontSize: 13, color: "var(--gold-deep)" }}>{uploadError}</span>
                )}
              </div>
            )}

            <div
              className="flex items-center gap-2"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--line-2)",
                borderRadius: 999,
                padding: "7px 8px 7px 20px",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={
                  selectedProfile
                    ? `Ask about you and ${selectedProfile.label}…`
                    : "Ask another question…"
                }
                className="font-reading min-w-0 flex-1 bg-transparent outline-none"
                style={{ fontSize: 17 }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
              />
              <input
                ref={fileRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                multiple
                hidden
                onChange={(e) => pickImages(e.target.files)}
              />
              <button
                onClick={() =>
                  canAttach
                    ? fileRef.current?.click()
                    : setUploadError(
                        "Attaching pictures is part of a paid plan — upgrade to send charts and screenshots.",
                      )
                }
                disabled={uploading}
                aria-label="Attach an image"
                title={
                  canAttach
                    ? "Attach a chart or a screenshot"
                    : "Attaching pictures is part of a paid plan"
                }
                className="grid shrink-0 place-items-center rounded-full"
                style={{
                  width: 40,
                  height: 40,
                  color: canAttach ? "var(--ink-3)" : "var(--line-2)",
                  fontSize: 18,
                }}
              >
                {"\uD83D\uDCCE\uFE0E"}
              </button>
              {micSupported && (
                <button
                  onClick={toggleMic}
                  aria-label={listening ? "Stop dictating" : "Dictate your question"}
                  aria-pressed={listening}
                  title={listening ? "Listening — tap to stop" : "Speak your question"}
                  className="grid shrink-0 place-items-center rounded-full"
                  style={{
                    width: 40,
                    height: 40,
                    background: listening ? "var(--gold-soft)" : "transparent",
                    color: listening ? "var(--gold-deep)" : "var(--ink-3)",
                    fontSize: 16,
                  }}
                >
                  {listening ? "◉" : "🎙"}
                </button>
              )}
              <button
                onClick={() => sendMessage()}
                disabled={loading}
                aria-label="Send"
                className="grid shrink-0 place-items-center rounded-full"
                style={{
                  width: 44,
                  height: 44,
                  background: "linear-gradient(135deg, var(--gold), var(--gold-deep))",
                  color: "var(--on-gold)",
                  fontSize: 17,
                  opacity: loading ? 0.6 : 1,
                }}
              >
                ↑
              </button>
            </div>

            {/* Meter line: model choice on the left, tokens on the right. */}
            <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
              {usage && usage.available_models?.length > 0 && (
                <div
                  className="flex gap-1 p-1"
                  style={{ background: "var(--sunk)", borderRadius: 999 }}
                >
                  {usage.available_models.map((m) => {
                    const active = selectedModel === m.key;
                    return (
                      <button
                        key={m.key}
                        onClick={() => selectModel(m.key)}
                        title={m.blurb}
                        className="uppercase"
                        style={{
                          borderRadius: 999,
                          padding: "5px 12px",
                          fontSize: 10,
                          letterSpacing: "0.16em",
                          background: active ? "var(--surface)" : "transparent",
                          color: active ? "var(--ink)" : "var(--ink-3)",
                          boxShadow: active ? "var(--shadow-sm)" : "none",
                        }}
                      >
                        {m.label}
                      </button>
                    );
                  })}
                </div>
              )}

              {usage && (
                <p className="micro-label" style={{ letterSpacing: "0.16em" }}>
                  {usage.daily_token_limit
                    ? `${(usage.tokens_remaining_today ?? 0).toLocaleString()} tokens left today`
                    : `${usage.tier_label} · unlimited`}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ─── Confirm anything irreversible ─── */}
      {confirmAction && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.55)" }}
          onClick={() => setConfirmAction(null)}
        >
          <div
            className="w-full max-w-sm"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 24,
              boxShadow: "var(--shadow)",
              padding: 24,
            }}
          >
            <h2 className="font-display" style={{ fontSize: 24, lineHeight: 1.2 }}>
              {confirmAction.title}
            </h2>
            <p
              className="font-reading mt-2"
              style={{ fontSize: 16, lineHeight: 1.65, color: "var(--ink-2)" }}
            >
              {confirmAction.body}
            </p>
            <div className="mt-5 flex items-center justify-end gap-2">
              <button
                onClick={() => setConfirmAction(null)}
                className="micro-label"
                style={{ letterSpacing: "0.16em", padding: "10px 14px" }}
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  const action = confirmAction;
                  setConfirmAction(null);
                  await action.run();
                }}
                className="uppercase"
                style={{
                  borderRadius: 999,
                  padding: "11px 18px",
                  fontSize: 10,
                  letterSpacing: "0.16em",
                  background: "#a8503c",
                  color: "#fffdf8",
                }}
              >
                {confirmAction.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Account & data ─── */}
      {accountOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto p-4 sm:items-center"
          style={{ background: "rgba(0,0,0,0.55)" }}
          onClick={() => setAccountOpen(false)}
        >
          <div
            className="my-auto w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 28,
              boxShadow: "var(--shadow)",
              padding: 24,
            }}
          >
            <div className="mb-5 flex items-start justify-between">
              <div>
                <p className="micro-label">Your account</p>
                <h2 className="font-display" style={{ fontSize: 26, marginTop: 4 }}>
                  {user?.name}
                </h2>
                <p style={{ fontSize: 13, color: "var(--ink-3)" }}>{user?.email}</p>
              </div>
              <button
                onClick={() => setAccountOpen(false)}
                aria-label="Close"
                style={{ fontSize: 18, color: "var(--ink-3)" }}
              >
                ✕
              </button>
            </div>

            <button
              onClick={() => {
                setAccountOpen(false);
                setEditing({ kind: "me" });
              }}
              className="mb-3 w-full text-left"
              style={{
                border: "1px solid var(--line-2)",
                borderRadius: 16,
                padding: "14px 16px",
              }}
            >
              <span style={{ fontSize: 15 }}>Edit my birth details</span>
              <span
                className="font-reading mt-1 block"
                style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ink-2)" }}
              >
                {user?.birth_date}
                {user?.birth_time_known === false ? " · time unknown" : ` · ${user?.birth_time}`}
                {user?.birth_place ? ` · ${user.birth_place}` : ""}
              </span>
            </button>

            <button
              onClick={downloadMyData}
              disabled={accountBusy !== ""}
              className="w-full text-left"
              style={{
                border: "1px solid var(--line-2)",
                borderRadius: 16,
                padding: "14px 16px",
                opacity: accountBusy === "export" ? 0.6 : 1,
              }}
            >
              <span style={{ fontSize: 15 }}>
                {accountBusy === "export" ? "Preparing…" : "Download my data"}
              </span>
              <span
                className="font-reading mt-1 block"
                style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ink-2)" }}
              >
                Your account, saved people and every conversation, as a file.
              </span>
            </button>

            <div
              className="mt-3"
              style={{
                border: "1px solid var(--line-2)",
                borderRadius: 16,
                padding: "14px 16px",
              }}
            >
              <span style={{ fontSize: 15 }}>Delete my account</span>
              <span
                className="font-reading mt-1 block"
                style={{ fontSize: 14, lineHeight: 1.6, color: "var(--ink-2)" }}
              >
                Erases your chart, your saved people and every conversation.
                This cannot be undone.
              </span>

              {!deleteArmed ? (
                <button
                  onClick={() => setDeleteArmed(true)}
                  className="mt-3 uppercase"
                  style={{
                    borderRadius: 999,
                    border: "1px solid var(--line-2)",
                    padding: "8px 16px",
                    fontSize: 10,
                    letterSpacing: "0.16em",
                    color: "var(--ink-2)",
                  }}
                >
                  Delete my account
                </button>
              ) : (
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <span className="font-reading" style={{ fontSize: 14 }}>
                    Are you sure?
                  </span>
                  <button
                    onClick={() => setDeleteArmed(false)}
                    className="micro-label"
                    style={{ letterSpacing: "0.16em", padding: "6px 10px" }}
                  >
                    Keep it
                  </button>
                  <button
                    onClick={deleteAccount}
                    disabled={accountBusy !== ""}
                    className="uppercase"
                    style={{
                      borderRadius: 999,
                      padding: "8px 16px",
                      fontSize: 10,
                      letterSpacing: "0.16em",
                      background: "#a8503c",
                      color: "#fffdf8",
                      opacity: accountBusy === "delete" ? 0.6 : 1,
                    }}
                  >
                    {accountBusy === "delete" ? "Deleting…" : "Yes, delete everything"}
                  </button>
                </div>
              )}
            </div>

            <p className="mt-5 text-center" style={{ fontSize: 12, color: "var(--ink-3)" }}>
              <a href="/terms" style={{ color: "var(--gold-deep)" }}>Terms</a>
              {" · "}
              <a href="/privacy" style={{ color: "var(--gold-deep)" }}>Privacy</a>
            </p>
          </div>
        </div>
      )}

      {/* ─── Chart modal ─── */}
      {chartOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto p-4 sm:items-center"
          style={{ background: "rgba(0,0,0,0.55)" }}
          onClick={() => setChartOpen(false)}
        >
          <div
            className="my-auto w-full max-w-lg"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 28,
              boxShadow: "var(--shadow)",
              padding: 24,
            }}
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <p className="micro-label">Your birth chart</p>
                <h2 className="font-display" style={{ fontSize: 26, marginTop: 4 }}>
                  {user?.name}
                </h2>
              </div>
              <button
                onClick={() => setChartOpen(false)}
                aria-label="Close chart"
                style={{ fontSize: 18, color: "var(--ink-3)" }}
              >
                ✕
              </button>
            </div>

            {chartLoading && (
              <div className="flex items-center gap-3 py-10">
                <ZodiMark size={26} night={night} spin />
                <span
                  className="font-reading zo-dots italic"
                  style={{ fontSize: 17, color: "var(--ink-2)" }}
                >
                  Casting your chart…
                </span>
              </div>
            )}

            {chartError && (
              <p className="font-reading" style={{ fontSize: 15, color: "var(--gold-deep)" }}>
                {chartError}
              </p>
            )}

            {chart && !chartLoading && (
              <>
                <ChartWheel chart={chart} night={night} />
                <div className="mt-5 grid grid-cols-2 gap-x-4 gap-y-2">
                  {chart.ascendant ? (
                    <div
                      className="col-span-2 mb-1 flex items-center justify-between"
                      style={{ background: "var(--sunk)", borderRadius: 12, padding: "8px 12px" }}
                    >
                      <span className="micro-label">Ascendant</span>
                      <span className="font-reading" style={{ fontSize: 15 }}>
                        {SIGN_GLYPH[chart.ascendant.sign]} {chart.ascendant.sign}
                      </span>
                    </div>
                  ) : (
                    <div className="time-warning col-span-2 mb-1" style={{ marginTop: 0 }}>
                      <p className="micro-label" style={{ letterSpacing: "0.18em" }}>
                        Birth time unknown
                      </p>
                      <p className="font-reading mt-1">
                        Without your exact birth time, we can&rsquo;t calculate your
                        Rising sign, houses, or certain degrees and aspects. Your
                        reading will still use the planetary placements available
                        from your birth date.
                      </p>
                    </div>
                  )}
                  {chart.planet_positions.map((p) => (
                    <div
                      key={p.planet}
                      className="flex items-center justify-between"
                      style={{ background: "var(--sunk)", borderRadius: 12, padding: "8px 12px" }}
                    >
                      <span style={{ fontSize: 13, color: "var(--ink-2)" }}>
                        {PLANET_GLYPH[p.planet] ?? "•"} {p.planet}
                      </span>
                      <span className="font-reading" style={{ fontSize: 14 }}>
                        {SIGN_GLYPH[p.sign]} {Math.floor(p.degree_in_sign)}°
                        {p.house ? ` · H${p.house}` : ""}
                        {p.retrograde ? " ℞" : ""}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {editing?.kind === "me" && user && (
        <BirthDetailsEditor
          kind="me"
          endpoint="/me"
          initial={{
            name: user.name,
            birth_date: user.birth_date,
            birth_time: user.birth_time,
            birth_place: user.birth_place,
            birth_time_known: user.birth_time_known,
          }}
          onSaved={onMeSaved}
          onClose={() => setEditing(null)}
        />
      )}

      {editing?.kind === "person" && (
        <BirthDetailsEditor
          kind="person"
          endpoint={`/profiles/${editing.profile.id}`}
          initial={{
            label: editing.profile.label,
            person_name: editing.profile.person_name,
            relationship_type: editing.profile.relationship_type,
            birth_date: editing.profile.birth_date,
            birth_time: editing.profile.birth_time,
            birth_place: editing.profile.birth_place,
            birth_time_known: editing.profile.birth_time_known,
          }}
          onSaved={onPersonSaved}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

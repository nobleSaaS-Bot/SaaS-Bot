import { useState, useEffect, useCallback } from "react";
import { api } from "@/services/api";

// ── Types ──────────────────────────────────────────────────────────────────────

type BroadcastStatus = "draft" | "scheduled" | "sending" | "sent" | "failed" | "cancelled";
type BroadcastSegment = "all" | "new" | "regular" | "vip" | "at_risk" | "churned";

interface BroadcastButton {
  text: string;
  url: string;
}

interface Broadcast {
  id: string;
  title: string;
  message: string;
  image_url: string | null;
  buttons: BroadcastButton[];
  segment: BroadcastSegment;
  status: BroadcastStatus;
  scheduled_at: string | null;
  sent_at: string | null;
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  failed_count: number;
  error_message: string | null;
  created_at: string;
}

interface Stats {
  total: number;
  sent: number;
  scheduled: number;
  total_messages_sent: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const STATUS_META: Record<BroadcastStatus, { label: string; color: string; dot: string }> = {
  draft:     { label: "Draft",     color: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",     dot: "bg-gray-400" },
  scheduled: { label: "Scheduled", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",  dot: "bg-blue-500" },
  sending:   { label: "Sending…",  color: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300", dot: "bg-amber-500 animate-pulse" },
  sent:      { label: "Sent",      color: "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300", dot: "bg-green-500" },
  failed:    { label: "Failed",    color: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",       dot: "bg-red-500" },
  cancelled: { label: "Cancelled", color: "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400",     dot: "bg-zinc-400" },
};

const SEGMENT_LABELS: Record<BroadcastSegment, string> = {
  all: "All Customers",
  new: "New",
  regular: "Regular",
  vip: "VIP ✦",
  at_risk: "At Risk",
  churned: "Churned",
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function DeliveryBar({ broadcast }: { broadcast: Broadcast }) {
  if (broadcast.total_recipients === 0) return <span className="text-xs text-muted-foreground">—</span>;
  const pct = Math.round((broadcast.sent_count / broadcast.total_recipients) * 100);
  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground whitespace-nowrap">{pct}%</span>
    </div>
  );
}

// ── Compose Modal ──────────────────────────────────────────────────────────────

interface ComposeForm {
  title: string;
  message: string;
  image_url: string;
  segment: BroadcastSegment;
  scheduled_at: string;
  buttons: BroadcastButton[];
}

const EMPTY_FORM: ComposeForm = {
  title: "",
  message: "",
  image_url: "",
  segment: "all",
  scheduled_at: "",
  buttons: [],
};

function ComposeModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (b: Broadcast) => void;
}) {
  const [form, setForm] = useState<ComposeForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState(false);

  function set<K extends keyof ComposeForm>(k: K, v: ComposeForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  function addButton() {
    set("buttons", [...form.buttons, { text: "", url: "" }]);
  }

  function updateButton(i: number, field: keyof BroadcastButton, val: string) {
    const updated = form.buttons.map((b, idx) => idx === i ? { ...b, [field]: val } : b);
    set("buttons", updated);
  }

  function removeButton(i: number) {
    set("buttons", form.buttons.filter((_, idx) => idx !== i));
  }

  async function handleSave(sendNow = false) {
    if (!form.title.trim() || !form.message.trim()) {
      setError("Title and message are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        title: form.title.trim(),
        message: form.message.trim(),
        segment: form.segment,
        buttons: form.buttons.filter((b) => b.text && b.url),
      };
      if (form.image_url.trim()) payload.image_url = form.image_url.trim();
      if (!sendNow && form.scheduled_at) payload.scheduled_at = new Date(form.scheduled_at).toISOString();

      const r = await api.post("/broadcasts", payload);
      const created: Broadcast = r.data;

      if (sendNow) {
        const sent = await api.post(`/broadcasts/${created.id}/send`);
        onCreated(sent.data);
      } else {
        onCreated(created);
      }
      onClose();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to save broadcast.");
    } finally {
      setSaving(false);
    }
  }

  const charCount = form.message.length;
  const charLimit = 4096;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-card border rounded-2xl shadow-2xl w-full max-w-2xl flex flex-col max-h-[90vh]">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b shrink-0">
            <h2 className="text-lg font-semibold text-foreground">New Broadcast</h2>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPreview(!preview)}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-muted text-muted-foreground hover:bg-muted/80 transition-colors"
              >
                {preview ? "Edit" : "Preview"}
              </button>
              <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-muted transition-colors">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5"><path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" /></svg>
              </button>
            </div>
          </div>

          {preview ? (
            /* ── Preview ── */
            <div className="flex-1 overflow-y-auto p-6 flex items-start justify-center">
              <div className="w-72 bg-[#effdde] rounded-2xl rounded-tl-sm p-3 shadow-sm">
                {form.image_url && (
                  <img src={form.image_url} alt="" className="w-full rounded-xl mb-2 object-cover max-h-40" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                )}
                <p className="text-sm text-gray-900 whitespace-pre-wrap leading-relaxed">{form.message || <span className="italic text-gray-400">Your message…</span>}</p>
                {form.buttons.filter((b) => b.text).map((b, i) => (
                  <div key={i} className="mt-2 py-1.5 px-3 bg-white rounded-lg text-center text-sm text-[#0088cc] border border-[#0088cc]/20 font-medium">
                    {b.text}
                  </div>
                ))}
                <p className="text-[10px] text-gray-400 text-right mt-1">12:00 ✓✓</p>
              </div>
            </div>
          ) : (
            /* ── Form ── */
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {error && (
                <div className="px-4 py-2.5 bg-destructive/10 text-destructive text-sm rounded-lg border border-destructive/20">{error}</div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">Campaign Title</label>
                  <input
                    value={form.title}
                    onChange={(e) => set("title", e.target.value)}
                    placeholder="e.g. Black Friday Sale 🔥"
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">Target Segment</label>
                  <select
                    value={form.segment}
                    onChange={(e) => set("segment", e.target.value as BroadcastSegment)}
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {(Object.entries(SEGMENT_LABELS) as [BroadcastSegment, string][]).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">Schedule (optional)</label>
                  <input
                    type="datetime-local"
                    value={form.scheduled_at}
                    onChange={(e) => set("scheduled_at", e.target.value)}
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-xs font-medium text-muted-foreground mb-1.5">Image URL (optional)</label>
                  <input
                    value={form.image_url}
                    onChange={(e) => set("image_url", e.target.value)}
                    placeholder="https://example.com/promo.jpg"
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                <div className="col-span-2">
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="text-xs font-medium text-muted-foreground">Message</label>
                    <span className={`text-xs ${charCount > charLimit ? "text-destructive" : "text-muted-foreground"}`}>
                      {charCount}/{charLimit}
                    </span>
                  </div>
                  <textarea
                    value={form.message}
                    onChange={(e) => set("message", e.target.value)}
                    rows={5}
                    placeholder="Write your message here. Supports <b>bold</b> and <i>italic</i> HTML tags…"
                    className="w-full px-3 py-2 text-sm border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                {/* Buttons */}
                <div className="col-span-2">
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs font-medium text-muted-foreground">Inline Buttons (optional)</label>
                    <button
                      onClick={addButton}
                      disabled={form.buttons.length >= 3}
                      className="text-xs text-primary hover:underline disabled:opacity-50"
                    >
                      + Add button
                    </button>
                  </div>
                  {form.buttons.map((btn, i) => (
                    <div key={i} className="flex gap-2 mb-2">
                      <input
                        value={btn.text}
                        onChange={(e) => updateButton(i, "text", e.target.value)}
                        placeholder="Button text"
                        className="flex-1 px-3 py-1.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                      <input
                        value={btn.url}
                        onChange={(e) => updateButton(i, "url", e.target.value)}
                        placeholder="https://…"
                        className="flex-1 px-3 py-1.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                      <button
                        onClick={() => removeButton(i)}
                        className="p-1.5 text-muted-foreground hover:text-destructive transition-colors"
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" /></svg>
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t shrink-0 bg-muted/20">
            <button onClick={onClose} className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
              Cancel
            </button>
            <div className="flex gap-2">
              <button
                onClick={() => handleSave(false)}
                disabled={saving}
                className="px-4 py-2 text-sm font-medium rounded-lg border bg-background hover:bg-muted transition-colors disabled:opacity-50"
              >
                {form.scheduled_at ? "Schedule" : "Save Draft"}
              </button>
              <button
                onClick={() => handleSave(true)}
                disabled={saving}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
              >
                {saving ? (
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" /><path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4" className="opacity-75" strokeLinecap="round" /></svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" /></svg>
                )}
                Send Now
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Stat Card ──────────────────────────────────────────────────────────────────

function StatCard({ label, value, icon, accent }: { label: string; value: string | number; icon: string; accent?: string }) {
  const icons: Record<string, string> = {
    megaphone: "M18 8h1a4 4 0 010 8h-1M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8zM6 1v3M10 1v3M14 1v3",
    check: "M22 11.08V12a10 10 0 11-5.93-9.14M22 4L12 14.01l-3-3",
    clock: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
    send: "M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z",
  };
  return (
    <div className="bg-card border rounded-xl p-5 flex items-start gap-4">
      <div className="p-2.5 rounded-lg bg-primary/10 shrink-0">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className={`w-5 h-5 ${accent ?? "text-primary"}`}>
          <path d={icons[icon]} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      <div>
        <p className="text-2xl font-bold text-foreground">{value}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

const DEMO_BROADCASTS: Broadcast[] = [
  { id: "1", title: "Black Friday Sale 🔥", message: "Big discounts today only! Use code FRIDAY30 for 30% off everything.", image_url: null, buttons: [{ text: "Shop Now", url: "https://t.me/yourbot" }], segment: "all", status: "sent", scheduled_at: null, sent_at: new Date(Date.now() - 86400000).toISOString(), total_recipients: 1240, sent_count: 1198, delivered_count: 1190, failed_count: 42, error_message: null, created_at: new Date(Date.now() - 86400000).toISOString() },
  { id: "2", title: "VIP Early Access", message: "As a VIP customer, you get early access to our new collection before anyone else! 🎉", image_url: null, buttons: [], segment: "vip", status: "scheduled", scheduled_at: new Date(Date.now() + 86400000 * 2).toISOString(), sent_at: null, total_recipients: 87, sent_count: 0, delivered_count: 0, failed_count: 0, error_message: null, created_at: new Date(Date.now() - 3600000).toISOString() },
  { id: "3", title: "We miss you 💙", message: "It's been a while! Come back and check what's new. Here's 15% off your next order.", image_url: null, buttons: [{ text: "Claim Discount", url: "https://t.me/yourbot" }], segment: "at_risk", status: "draft", scheduled_at: null, sent_at: null, total_recipients: 203, sent_count: 0, delivered_count: 0, failed_count: 0, error_message: null, created_at: new Date(Date.now() - 7200000).toISOString() },
];

export default function Broadcasts() {
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCompose, setShowCompose] = useState(false);
  const [sending, setSending] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [bRes, sRes] = await Promise.all([
        api.get("/broadcasts"),
        api.get("/broadcasts/stats"),
      ]);
      setBroadcasts(bRes.data);
      setStats(sRes.data);
    } catch {
      setBroadcasts(DEMO_BROADCASTS);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  async function handleSend(id: string) {
    setSending(id);
    try {
      const r = await api.post(`/broadcasts/${id}/send`);
      setBroadcasts((prev) => prev.map((b) => b.id === id ? r.data : b));
    } finally {
      setSending(null);
    }
  }

  async function handleCancel(id: string) {
    await api.delete(`/broadcasts/${id}`);
    setBroadcasts((prev) => prev.map((b) => b.id === id ? { ...b, status: "cancelled" } : b));
  }

  function handleCreated(b: Broadcast) {
    setBroadcasts((prev) => [b, ...prev]);
    fetchData();
  }

  const display = broadcasts.length > 0 ? broadcasts : loading ? [] : DEMO_BROADCASTS;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Broadcasts</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Send bulk messages to your Telegram customers by segment</p>
        </div>
        <button
          onClick={() => setShowCompose(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:opacity-90 transition-opacity"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          New Broadcast
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Campaigns" value={stats?.total ?? display.length} icon="megaphone" />
        <StatCard label="Sent Successfully" value={stats?.sent ?? display.filter(b => b.status === "sent").length} icon="check" accent="text-green-500" />
        <StatCard label="Scheduled" value={stats?.scheduled ?? display.filter(b => b.status === "scheduled").length} icon="clock" accent="text-blue-500" />
        <StatCard label="Messages Delivered" value={stats?.total_messages_sent?.toLocaleString() ?? display.reduce((s, b) => s + b.delivered_count, 0).toLocaleString()} icon="send" accent="text-violet-500" />
      </div>

      {/* Broadcast List */}
      <div className="bg-card border rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <h2 className="font-semibold text-foreground text-sm">Campaign History</h2>
          <span className="text-xs text-muted-foreground">{display.length} campaigns</span>
        </div>

        {loading ? (
          <div className="divide-y">
            {[1, 2, 3].map((i) => (
              <div key={i} className="px-5 py-4 animate-pulse">
                <div className="h-4 bg-muted rounded w-48 mb-2" />
                <div className="h-3 bg-muted rounded w-full mb-1" />
                <div className="h-3 bg-muted rounded w-3/4" />
              </div>
            ))}
          </div>
        ) : display.length === 0 ? (
          <div className="py-20 text-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-12 h-12 mx-auto mb-3 text-muted-foreground/40">
              <path d="M18 8h1a4 4 0 010 8h-1M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8zM6 1v3M10 1v3M14 1v3" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="text-sm text-muted-foreground">No broadcasts yet.</p>
            <p className="text-xs text-muted-foreground mt-1">Create your first campaign to reach your customers.</p>
          </div>
        ) : (
          <div className="divide-y">
            {display.map((b) => {
              const meta = STATUS_META[b.status];
              const deliveryRate = b.total_recipients > 0
                ? Math.round((b.delivered_count / b.total_recipients) * 100)
                : null;

              return (
                <div key={b.id} className="px-5 py-4 hover:bg-muted/20 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium text-foreground text-sm truncate">{b.title}</h3>
                        <span className={`shrink-0 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium ${meta.color}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />
                          {meta.label}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2 leading-relaxed">{b.message}</p>

                      <div className="flex flex-wrap items-center gap-4 mt-3">
                        {/* Segment */}
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3">
                            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8z" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          {SEGMENT_LABELS[b.segment]}
                          {b.total_recipients > 0 && <span className="text-foreground font-medium">· {b.total_recipients.toLocaleString()}</span>}
                        </span>

                        {/* Delivery */}
                        {b.status === "sent" && (
                          <div className="flex items-center gap-3">
                            <span className="text-xs text-green-600 font-medium">{b.sent_count.toLocaleString()} sent</span>
                            {b.failed_count > 0 && <span className="text-xs text-red-500">{b.failed_count} failed</span>}
                            <DeliveryBar broadcast={b} />
                          </div>
                        )}

                        {/* Timing */}
                        <span className="text-xs text-muted-foreground">
                          {b.status === "sent" && b.sent_at ? `Sent ${timeAgo(b.sent_at)}` :
                           b.status === "scheduled" && b.scheduled_at ? `Scheduled ${new Date(b.scheduled_at).toLocaleString()}` :
                           `Created ${timeAgo(b.created_at)}`}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {b.status === "draft" && (
                        <button
                          onClick={() => handleSend(b.id)}
                          disabled={sending === b.id}
                          className="px-3 py-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-1.5"
                        >
                          {sending === b.id ? (
                            <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" /><path d="M4 12a8 8 0 018-8" stroke="currentColor" strokeWidth="4" className="opacity-75" strokeLinecap="round" /></svg>
                          ) : (
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-3 h-3"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z" strokeLinecap="round" strokeLinejoin="round" /></svg>
                          )}
                          Send
                        </button>
                      )}
                      {(b.status === "draft" || b.status === "scheduled") && (
                        <button
                          onClick={() => handleCancel(b.id)}
                          className="px-3 py-1.5 text-xs font-medium border rounded-lg hover:bg-muted text-muted-foreground transition-colors"
                        >
                          Cancel
                        </button>
                      )}
                      {b.status === "sent" && deliveryRate !== null && (
                        <div className="text-right">
                          <p className="text-lg font-bold text-foreground">{deliveryRate}%</p>
                          <p className="text-[10px] text-muted-foreground">delivery</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showCompose && (
        <ComposeModal onClose={() => setShowCompose(false)} onCreated={handleCreated} />
      )}
    </div>
  );
}

import { useState, useEffect, useCallback } from "react";
import { api } from "@/services/api";

// ── Types ──────────────────────────────────────────────────────────────────────

type Segment = "new" | "regular" | "vip" | "at_risk" | "churned";

interface OrderSummary {
  id: string;
  status: string;
  total: number;
  currency: string;
  created_at: string;
}

interface Customer {
  id: string;
  telegram_id: string;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  phone: string | null;
  email: string | null;
  photo_url: string | null;
  segment: Segment;
  tags: string[];
  notes: string | null;
  total_orders: number;
  total_spent: number;
  currency: string;
  last_order_at: string | null;
  is_blocked: boolean;
  created_at: string;
  recent_orders?: OrderSummary[];
}

interface Stats {
  total: number;
  new_this_month: number;
  vip: number;
  at_risk: number;
  total_revenue: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

const SEGMENT_META: Record<Segment, { label: string; color: string }> = {
  new: { label: "New", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
  regular: { label: "Regular", color: "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300" },
  vip: { label: "VIP", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300" },
  at_risk: { label: "At Risk", color: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300" },
  churned: { label: "Churned", color: "bg-zinc-100 text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400" },
};

const ORDER_STATUS_COLOR: Record<string, string> = {
  paid: "bg-green-100 text-green-700",
  delivered: "bg-emerald-100 text-emerald-700",
  pending: "bg-yellow-100 text-yellow-700",
  cancelled: "bg-red-100 text-red-700",
  refunded: "bg-purple-100 text-purple-700",
  processing: "bg-blue-100 text-blue-700",
  shipped: "bg-cyan-100 text-cyan-700",
  confirmed: "bg-teal-100 text-teal-700",
};

function initials(c: Customer) {
  const parts = [c.first_name, c.last_name].filter(Boolean);
  return parts.length ? parts.map((p) => p![0]).join("").toUpperCase() : c.telegram_id.slice(0, 2).toUpperCase();
}

function displayName(c: Customer) {
  const parts = [c.first_name, c.last_name].filter(Boolean);
  return parts.length ? parts.join(" ") : c.username ? `@${c.username}` : `User ${c.telegram_id}`;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function fmt(amount: number, currency = "USD") {
  return new Intl.NumberFormat("en-US", { style: "currency", currency, minimumFractionDigits: 2 }).format(amount);
}

// ── Avatar ─────────────────────────────────────────────────────────────────────

function Avatar({ customer, size = "md" }: { customer: Customer; size?: "sm" | "md" | "lg" }) {
  const sizes = { sm: "w-8 h-8 text-xs", md: "w-10 h-10 text-sm", lg: "w-14 h-14 text-base" };
  if (customer.photo_url) {
    return <img src={customer.photo_url} alt="" className={`${sizes[size]} rounded-full object-cover`} />;
  }
  const colors = ["bg-blue-500", "bg-violet-500", "bg-emerald-500", "bg-amber-500", "bg-rose-500"];
  const color = colors[parseInt(customer.telegram_id, 10) % colors.length] ?? "bg-primary";
  return (
    <div className={`${sizes[size]} ${color} rounded-full flex items-center justify-center font-semibold text-white shrink-0`}>
      {initials(customer)}
    </div>
  );
}

// ── Stat Card ──────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div className="bg-card border rounded-xl p-5">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent ?? "text-foreground"}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>}
    </div>
  );
}

// ── Profile Drawer ─────────────────────────────────────────────────────────────

function ProfileDrawer({
  customer,
  onClose,
  onUpdated,
}: {
  customer: Customer;
  onClose: () => void;
  onUpdated: (c: Customer) => void;
}) {
  const [detail, setDetail] = useState<Customer>(customer);
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState(customer.notes ?? "");
  const [newTag, setNewTag] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get(`/customers/${customer.id}`).then((r) => {
      setDetail(r.data);
      setNotes(r.data.notes ?? "");
      setLoading(false);
    });
  }, [customer.id]);

  async function patch(payload: object) {
    setSaving(true);
    try {
      const r = await api.patch(`/customers/${customer.id}`, payload);
      setDetail(r.data);
      onUpdated(r.data);
    } finally {
      setSaving(false);
    }
  }

  function addTag() {
    const tag = newTag.trim();
    if (!tag || detail.tags.includes(tag)) return;
    patch({ tags: [...detail.tags, tag] });
    setNewTag("");
  }

  function removeTag(tag: string) {
    patch({ tags: detail.tags.filter((t) => t !== tag) });
  }

  return (
    <>
      {/* Overlay */}
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-card border-l shadow-2xl z-50 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b shrink-0">
          <div className="flex items-center gap-3">
            <Avatar customer={detail} size="lg" />
            <div>
              <h2 className="font-semibold text-foreground">{displayName(detail)}</h2>
              {detail.username && (
                <p className="text-xs text-muted-foreground">@{detail.username}</p>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-muted transition-colors">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-5 h-5"><path d="M18 6L6 18M6 6l12 12" strokeLinecap="round" /></svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* Spend Stats */}
          <div className="grid grid-cols-3 gap-3 p-5 border-b">
            <div className="text-center">
              <p className="text-lg font-bold text-foreground">{detail.total_orders}</p>
              <p className="text-[11px] text-muted-foreground">Orders</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-foreground">{fmt(detail.total_spent, detail.currency)}</p>
              <p className="text-[11px] text-muted-foreground">Total Spent</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-foreground">
                {detail.total_orders > 0 ? fmt(detail.total_spent / detail.total_orders, detail.currency) : "—"}
              </p>
              <p className="text-[11px] text-muted-foreground">Avg Order</p>
            </div>
          </div>

          {/* Contact Info */}
          <div className="px-5 py-4 border-b space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Contact</h3>
            {[
              { icon: "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z", label: "Telegram ID", value: detail.telegram_id },
              { icon: "M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z", label: "Phone", value: detail.phone },
              { icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z", label: "Email", value: detail.email },
            ].map(({ icon, label, value }) =>
              value ? (
                <div key={label} className="flex items-center gap-2 text-sm">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-muted-foreground shrink-0">
                    <path d={icon} strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  <span className="text-muted-foreground">{label}:</span>
                  <span className="text-foreground">{value}</span>
                </div>
              ) : null
            )}
            {detail.last_order_at && (
              <div className="flex items-center gap-2 text-sm">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-muted-foreground shrink-0">
                  <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="text-muted-foreground">Last order:</span>
                <span className="text-foreground">{timeAgo(detail.last_order_at)}</span>
              </div>
            )}
            <div className="flex items-center gap-2 text-sm">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-muted-foreground shrink-0">
                <path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="text-muted-foreground">Joined:</span>
              <span className="text-foreground">{new Date(detail.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          {/* Segment */}
          <div className="px-5 py-4 border-b">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Segment</h3>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(SEGMENT_META) as Segment[]).map((seg) => (
                <button
                  key={seg}
                  onClick={() => patch({ segment: seg })}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-all border-2 ${
                    detail.segment === seg
                      ? `${SEGMENT_META[seg].color} border-current`
                      : "border-transparent bg-muted text-muted-foreground hover:bg-muted/80"
                  }`}
                >
                  {SEGMENT_META[seg].label}
                </button>
              ))}
            </div>
          </div>

          {/* Tags */}
          <div className="px-5 py-4 border-b">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Tags</h3>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {detail.tags.map((tag) => (
                <span key={tag} className="flex items-center gap-1 px-2 py-0.5 bg-secondary text-secondary-foreground rounded-full text-xs">
                  {tag}
                  <button onClick={() => removeTag(tag)} className="hover:text-destructive">×</button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addTag()}
                placeholder="Add tag…"
                className="flex-1 px-3 py-1.5 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <button onClick={addTag} className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:opacity-90 transition-opacity">
                Add
              </button>
            </div>
          </div>

          {/* Notes */}
          <div className="px-5 py-4 border-b">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Notes</h3>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Add internal notes about this customer…"
              className="w-full px-3 py-2 text-sm border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <button
              onClick={() => patch({ notes })}
              disabled={saving || notes === (detail.notes ?? "")}
              className="mt-2 px-4 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg disabled:opacity-50 hover:opacity-90 transition-opacity"
            >
              {saving ? "Saving…" : "Save Notes"}
            </button>
          </div>

          {/* Order History */}
          <div className="px-5 py-4 border-b">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">Order History</h3>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-12 bg-muted rounded-lg animate-pulse" />
                ))}
              </div>
            ) : detail.recent_orders && detail.recent_orders.length > 0 ? (
              <div className="space-y-2">
                {detail.recent_orders.map((order) => (
                  <div key={order.id} className="flex items-center justify-between py-2.5 px-3 bg-muted/40 rounded-lg">
                    <div>
                      <p className="text-xs font-mono text-foreground">#{order.id.slice(-8).toUpperCase()}</p>
                      <p className="text-xs text-muted-foreground">{timeAgo(order.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize ${ORDER_STATUS_COLOR[order.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {order.status}
                      </span>
                      <span className="text-sm font-semibold text-foreground">{fmt(order.total, order.currency)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No orders yet.</p>
            )}
          </div>

          {/* Block */}
          <div className="px-5 py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-foreground">Block Customer</p>
                <p className="text-xs text-muted-foreground">Blocked customers cannot interact with your bot.</p>
              </div>
              <button
                onClick={() => patch({ is_blocked: !detail.is_blocked })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                  detail.is_blocked ? "bg-destructive" : "bg-muted"
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${detail.is_blocked ? "translate-x-6" : "translate-x-1"}`} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

const SEGMENTS: { value: Segment | "all"; label: string }[] = [
  { value: "all", label: "All" },
  { value: "new", label: "New" },
  { value: "regular", label: "Regular" },
  { value: "vip", label: "VIP ✦" },
  { value: "at_risk", label: "At Risk" },
  { value: "churned", label: "Churned" },
];

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [search, setSearch] = useState("");
  const [segment, setSegment] = useState<Segment | "all">("all");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Customer | null>(null);
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const fetchStats = useCallback(async () => {
    try {
      const r = await api.get("/customers/stats");
      setStats(r.data);
    } catch {}
  }, []);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (segment !== "all") params.segment = segment;
      if (debouncedSearch) params.search = debouncedSearch;
      const r = await api.get("/customers", { params });
      setCustomers(r.data);
    } finally {
      setLoading(false);
    }
  }, [segment, debouncedSearch]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  function handleUpdated(updated: Customer) {
    setCustomers((prev) => prev.map((c) => (c.id === updated.id ? { ...c, ...updated } : c)));
    if (selected?.id === updated.id) setSelected((prev) => prev ? { ...prev, ...updated } : prev);
    fetchStats();
  }

  // Demo seed when API is unavailable
  const display: Customer[] = customers.length > 0 ? customers : loading ? [] : DEMO;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Customers</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Manage and segment your Telegram customers</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Customers" value={stats?.total ?? "—"} />
        <StatCard label="New This Month" value={stats?.new_this_month ?? "—"} accent="text-primary" />
        <StatCard label="VIP Customers" value={stats?.vip ?? "—"} accent="text-amber-500" />
        <StatCard
          label="Total Revenue"
          value={stats ? fmt(stats.total_revenue) : "—"}
          sub={`${stats?.at_risk ?? 0} at risk`}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-sm">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground">
            <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" strokeLinecap="round" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, @username, phone…"
            className="w-full pl-9 pr-4 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex gap-1.5 flex-wrap">
          {SEGMENTS.map((s) => (
            <button
              key={s.value}
              onClick={() => setSegment(s.value as Segment | "all")}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                segment === s.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/30">
                <th className="text-left px-4 py-3 font-medium text-muted-foreground">Customer</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden md:table-cell">Segment</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground hidden sm:table-cell">Orders</th>
                <th className="text-right px-4 py-3 font-medium text-muted-foreground">Total Spent</th>
                <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden lg:table-cell">Last Active</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {loading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}>
                      {[1, 2, 3, 4, 5, 6].map((j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-muted rounded animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))
                : display.map((c) => (
                    <tr
                      key={c.id}
                      onClick={() => setSelected(c)}
                      className="hover:bg-muted/30 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <Avatar customer={c} size="sm" />
                          <div>
                            <p className="font-medium text-foreground flex items-center gap-1.5">
                              {displayName(c)}
                              {c.is_blocked && (
                                <span className="text-[10px] bg-destructive/10 text-destructive rounded px-1">Blocked</span>
                              )}
                            </p>
                            {c.username && (
                              <p className="text-xs text-muted-foreground">@{c.username}</p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 hidden md:table-cell">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SEGMENT_META[c.segment].color}`}>
                          {SEGMENT_META[c.segment].label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right text-muted-foreground hidden sm:table-cell">
                        {c.total_orders}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-foreground">
                        {fmt(c.total_spent, c.currency)}
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-sm hidden lg:table-cell">
                        {c.last_order_at ? timeAgo(c.last_order_at) : timeAgo(c.created_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground transition-colors">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
                            <path d="M9 18l6-6-6-6" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>

          {!loading && display.length === 0 && (
            <div className="py-16 text-center text-muted-foreground">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-10 h-10 mx-auto mb-3 opacity-40">
                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="text-sm">No customers found.</p>
              <p className="text-xs mt-1">Customers appear here when they start chatting with your bot.</p>
            </div>
          )}
        </div>
      </div>

      {/* Profile Drawer */}
      {selected && (
        <ProfileDrawer
          customer={selected}
          onClose={() => setSelected(null)}
          onUpdated={handleUpdated}
        />
      )}
    </div>
  );
}

// ── Demo data (shown when API not connected) ────────────────────────────────────

const DEMO: Customer[] = [
  { id: "1", telegram_id: "123456789", first_name: "Aisha", last_name: "Mohammed", username: "aisha_m", phone: "+251911234567", email: null, photo_url: null, segment: "vip", tags: ["loyal", "top-buyer"], notes: "Loves new arrivals.", total_orders: 14, total_spent: 520.0, currency: "USD", last_order_at: new Date(Date.now() - 86400000).toISOString(), is_blocked: false, created_at: new Date(Date.now() - 86400000 * 60).toISOString() },
  { id: "2", telegram_id: "987654321", first_name: "Dawit", last_name: "Bekele", username: "dawit_b", phone: null, email: "dawit@example.com", photo_url: null, segment: "regular", tags: ["wholesale"], notes: null, total_orders: 5, total_spent: 210.5, currency: "USD", last_order_at: new Date(Date.now() - 86400000 * 7).toISOString(), is_blocked: false, created_at: new Date(Date.now() - 86400000 * 90).toISOString() },
  { id: "3", telegram_id: "456123789", first_name: "Sara", last_name: null, username: "sara_t", phone: "+254712345678", email: null, photo_url: null, segment: "new", tags: [], notes: null, total_orders: 1, total_spent: 35.0, currency: "USD", last_order_at: new Date(Date.now() - 86400000 * 2).toISOString(), is_blocked: false, created_at: new Date(Date.now() - 86400000 * 3).toISOString() },
  { id: "4", telegram_id: "741852963", first_name: "Kebede", last_name: "Haile", username: null, phone: "+251922345678", email: null, photo_url: null, segment: "at_risk", tags: ["inactive"], notes: "No purchase in 45 days.", total_orders: 3, total_spent: 89.0, currency: "USD", last_order_at: new Date(Date.now() - 86400000 * 45).toISOString(), is_blocked: false, created_at: new Date(Date.now() - 86400000 * 120).toISOString() },
  { id: "5", telegram_id: "369258147", first_name: "Meron", last_name: "Tesfaye", username: "meron_t", phone: null, email: null, photo_url: null, segment: "churned", tags: [], notes: null, total_orders: 2, total_spent: 55.0, currency: "USD", last_order_at: new Date(Date.now() - 86400000 * 90).toISOString(), is_blocked: false, created_at: new Date(Date.now() - 86400000 * 180).toISOString() },
];

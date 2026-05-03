import { useState, useEffect, useCallback } from "react";
import { api } from "@/services/api";

// ── Types ──────────────────────────────────────────────────────────────────
interface CustomerSummary {
  id: string;
  display_name: string;
  telegram_username: string | null;
  telegram_user_id: number;
  total_orders: number;
  total_spent: number;
  average_order_value: number;
  last_order_at: string | null;
  first_order_at: string | null;
  segments: string[];
  tags: string[];
  is_blocked: boolean;
  last_seen_at: string | null;
  message_count: number;
  created_at: string;
}

interface CustomerDetail extends CustomerSummary {
  notes: string | null;
  language_code: string | null;
  first_name: string | null;
  last_name: string | null;
}

interface OrderSummary {
  id: string;
  total: number;
  status: string;
  created_at: string;
  item_count: number | null;
}

interface CRMStats {
  total_customers: number;
  new_this_month: number;
  repeat_buyers: number;
  vip_count: number;
  at_risk_count: number;
  total_revenue: number;
  avg_customer_value: number;
  top_spender_amount: number;
}

// ── Mock data ──────────────────────────────────────────────────────────────
const MOCK_STATS: CRMStats = {
  total_customers: 1284, new_this_month: 143, repeat_buyers: 389,
  vip_count: 67, at_risk_count: 94, total_revenue: 48320.5,
  avg_customer_value: 37.63, top_spender_amount: 1840.0,
};

const SEGMENTS = ["vip", "repeat_buyer", "new", "at_risk"] as const;
const SEG_META: Record<string, { label: string; color: string; bg: string }> = {
  vip:          { label: "VIP",     color: "#f59e0b", bg: "rgba(245,158,11,0.12)" },
  repeat_buyer: { label: "Repeat",  color: "#34d399", bg: "rgba(52,211,153,0.12)" },
  new:          { label: "New",     color: "#60a5fa", bg: "rgba(96,165,250,0.12)" },
  at_risk:      { label: "At Risk", color: "#f87171", bg: "rgba(248,113,113,0.12)" },
  blocked:      { label: "Blocked", color: "#94a3b8", bg: "rgba(148,163,184,0.12)" },
};

const NAMES = ["Mekdes Alemu","Yonas Tesfaye","Tigist Bekele","Dawit Haile","Sara Girma",
  "Abel Tadesse","Hana Wolde","Biniyam Asefa","Liya Mengistu","Natan Fekadu",
  "Amina Hassan","Ibrahim Jama","Grace Wanjiku","Brian Ochieng","Amara Diallo",
  "Kofi Mensah","Zara Osei","David Kimani","Aisha Musa","James Nkosi"];

function makeMockCustomers(n = 60): CustomerSummary[] {
  return Array.from({ length: n }, (_, i) => {
    const name = NAMES[i % NAMES.length] + (i >= NAMES.length ? ` ${Math.floor(i / NAMES.length) + 1}` : "");
    const orders = Math.floor(Math.random() * 18) + 1;
    const spent = +((Math.random() * 600) + 5).toFixed(2);
    const segs: string[] = [];
    if (spent > 400) segs.push("vip");
    if (orders > 4) segs.push("repeat_buyer");
    if (orders === 1) segs.push("new");
    if (Math.random() < 0.1) segs.push("at_risk");
    const rndDate = (d = 400) => { const dt = new Date(); dt.setDate(dt.getDate() - Math.floor(Math.random() * d)); return dt.toISOString(); };
    return {
      id: `cust-${i}`, display_name: name,
      telegram_username: Math.random() > 0.4 ? name.toLowerCase().replace(" ", "_") : null,
      telegram_user_id: 100000000 + i, total_orders: orders, total_spent: spent,
      average_order_value: +(spent / orders).toFixed(2),
      last_order_at: rndDate(90), first_order_at: rndDate(400),
      segments: segs, tags: [], is_blocked: false, last_seen_at: rndDate(7),
      message_count: Math.floor(Math.random() * 80) + 1, created_at: rndDate(400),
    };
  });
}

const MOCK_CUSTOMERS = makeMockCustomers(60);

// ── Helpers ────────────────────────────────────────────────────────────────
function fmtDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
function fmtMoney(n: number) {
  return "$" + (+n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function timeSince(iso: string | null) {
  if (!iso) return "—";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// ── Segment pill ───────────────────────────────────────────────────────────
function Pill({ seg }: { seg: string }) {
  const m = SEG_META[seg] ?? { label: seg, color: "#94a3b8", bg: "rgba(148,163,184,0.12)" };
  return (
    <span style={{
      fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase",
      padding: "2px 7px", borderRadius: "20px", color: m.color, background: m.bg,
      border: `1px solid ${m.color}30`,
    }}>{m.label}</span>
  );
}

// ── Status badge ───────────────────────────────────────────────────────────
function StatusBadge({ s }: { s: string }) {
  const map: Record<string, { c: string; b: string }> = {
    completed: { c: "#34d399", b: "rgba(52,211,153,0.1)" },
    paid:      { c: "#34d399", b: "rgba(52,211,153,0.1)" },
    pending:   { c: "#fbbf24", b: "rgba(251,191,36,0.1)" },
    cancelled: { c: "#f87171", b: "rgba(248,113,113,0.1)" },
  };
  const m = map[s] ?? map.pending;
  return <span style={{ fontSize: "0.62rem", fontWeight: 600, padding: "2px 8px", borderRadius: "4px", color: m.c, background: m.b }}>{s}</span>;
}

// ── Stat card ──────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, accent }: { label: string; value: string | number; sub?: string; accent?: string }) {
  return (
    <div style={{ background: "#0e0e18", border: "1px solid #1e2235", borderRadius: "10px", padding: "1.1rem 1.25rem", position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: "2px", background: accent ?? "#3b82f6" }} />
      <div style={{ fontSize: "0.6rem", letterSpacing: "0.15em", textTransform: "uppercase", color: "#475569", marginBottom: "0.5rem" }}>{label}</div>
      <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "1.6rem", fontWeight: 700, color: "#f1f5f9", lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: "0.65rem", color: "#475569", marginTop: "0.35rem" }}>{sub}</div>}
    </div>
  );
}

// ── Customer drawer ────────────────────────────────────────────────────────
function CustomerDrawer({ customer, onClose, onUpdate }: {
  customer: CustomerSummary | null;
  onClose: () => void;
  onUpdate: (c: CustomerSummary) => void;
}) {
  const [notes, setNotes] = useState(customer?.display_name ?? "");
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!customer) return;
    setNotes("");
    setOrders([]);
    api.get(`/customers/${customer.id}`).then((r) => {
      setNotes(r.data.customer.notes ?? "");
      setOrders(r.data.recent_orders ?? []);
    }).catch(() => {
      setOrders(Array.from({ length: 5 }, (_, i) => ({
        id: `ord-${i}`, total: +(Math.random() * 200 + 10).toFixed(2),
        status: ["paid", "pending", "cancelled"][i % 3],
        created_at: new Date(Date.now() - i * 86400000 * 10).toISOString(),
        item_count: Math.floor(Math.random() * 5) + 1,
      })));
    });
  }, [customer?.id]);

  if (!customer) return null;

  const handleSaveNotes = async () => {
    setSaving(true);
    try {
      await api.patch(`/customers/${customer.id}`, { notes });
      onUpdate({ ...customer });
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", backdropFilter: "blur(2px)", zIndex: 40, cursor: "pointer" }} />
      <div style={{
        position: "fixed", top: 0, right: 0, bottom: 0, width: "420px",
        background: "#0a0a14", borderLeft: "1px solid #1e2235",
        zIndex: 50, overflowY: "auto", display: "flex", flexDirection: "column",
        animation: "slideIn .2s ease",
      }}>
        <style>{`@keyframes slideIn{from{transform:translateX(100%)}to{transform:translateX(0)}}`}</style>

        <div style={{ padding: "1.5rem", borderBottom: "1px solid #1e2235", flexShrink: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div style={{ display: "flex", gap: "0.85rem", alignItems: "center" }}>
              <div style={{
                width: "46px", height: "46px", borderRadius: "12px", flexShrink: 0,
                background: `hsl(${customer.telegram_user_id % 360},40%,25%)`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "1.1rem", fontWeight: 700, color: `hsl(${customer.telegram_user_id % 360},70%,75%)`,
                fontFamily: "'JetBrains Mono',monospace",
              }}>
                {customer.display_name.charAt(0)}
              </div>
              <div>
                <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#f1f5f9" }}>{customer.display_name}</div>
                {customer.telegram_username && <div style={{ fontSize: "0.7rem", color: "#475569", marginTop: "2px" }}>@{customer.telegram_username}</div>}
              </div>
            </div>
            <button onClick={onClose} style={{ background: "none", border: "1px solid #1e2235", color: "#475569", borderRadius: "6px", width: "28px", height: "28px", cursor: "pointer", fontSize: "1rem" }}>×</button>
          </div>
          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "0.85rem" }}>
            {customer.segments.map(s => <Pill key={s} seg={s} />)}
            {customer.is_blocked && <Pill seg="blocked" />}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", borderBottom: "1px solid #1e2235" }}>
          {[
            { label: "Orders", val: customer.total_orders },
            { label: "Spent", val: fmtMoney(customer.total_spent) },
            { label: "Avg Order", val: fmtMoney(customer.average_order_value) },
          ].map((s, i) => (
            <div key={i} style={{ padding: "0.9rem", textAlign: "center", borderRight: i < 2 ? "1px solid #1e2235" : "none" }}>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "1rem", fontWeight: 700, color: "#f1f5f9" }}>{s.val}</div>
              <div style={{ fontSize: "0.58rem", letterSpacing: "0.1em", textTransform: "uppercase", color: "#475569", marginTop: "2px" }}>{s.label}</div>
            </div>
          ))}
        </div>

        <div style={{ padding: "1.25rem", flex: 1, display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <div>
            <div style={{ fontSize: "0.58rem", letterSpacing: "0.15em", textTransform: "uppercase", color: "#334155", marginBottom: "0.6rem" }}>Details</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
              {[
                ["Customer since", fmtDate(customer.created_at)],
                ["Last order", fmtDate(customer.last_order_at)],
                ["Last seen", timeSince(customer.last_seen_at)],
                ["Messages sent", customer.message_count],
                ["Language", (customer as CustomerDetail).language_code?.toUpperCase() ?? "—"],
                ["Telegram ID", customer.telegram_user_id],
              ].map(([k, v]) => (
                <div key={String(k)} style={{ background: "#0e0e18", border: "1px solid #1e2235", borderRadius: "6px", padding: "0.5rem 0.7rem" }}>
                  <div style={{ fontSize: "0.58rem", color: "#334155", textTransform: "uppercase", letterSpacing: "0.1em" }}>{k}</div>
                  <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "2px", fontFamily: "'JetBrains Mono',monospace" }}>{v}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div style={{ fontSize: "0.58rem", letterSpacing: "0.15em", textTransform: "uppercase", color: "#334155", marginBottom: "0.6rem" }}>Merchant Notes</div>
            <textarea value={notes} onChange={e => setNotes(e.target.value)} placeholder="Add a private note…" rows={3} style={{ width: "100%", background: "#0e0e18", border: "1px solid #1e2235", borderRadius: "6px", color: "#94a3b8", fontSize: "0.75rem", padding: "0.65rem 0.75rem", resize: "vertical", fontFamily: "inherit", lineHeight: 1.6, outline: "none", boxSizing: "border-box" }} />
            <button onClick={handleSaveNotes} disabled={saving} style={{ marginTop: "0.4rem", fontSize: "0.7rem", padding: "5px 14px", borderRadius: "5px", background: saving ? "#1e2235" : "#3b82f6", border: "none", color: "white", cursor: "pointer", opacity: saving ? 0.6 : 1 }}>
              {saving ? "Saving…" : "Save note"}
            </button>
          </div>

          <div>
            <div style={{ fontSize: "0.58rem", letterSpacing: "0.15em", textTransform: "uppercase", color: "#334155", marginBottom: "0.6rem" }}>Recent Orders</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {orders.slice(0, 6).map(o => (
                <div key={o.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "#0e0e18", border: "1px solid #1e2235", borderRadius: "6px", padding: "0.55rem 0.75rem" }}>
                  <div>
                    <div style={{ fontSize: "0.72rem", fontFamily: "'JetBrains Mono',monospace", color: "#f1f5f9", fontWeight: 600 }}>{fmtMoney(o.total)}</div>
                    <div style={{ fontSize: "0.6rem", color: "#334155", marginTop: "1px" }}>{fmtDate(o.created_at)}{o.item_count ? ` · ${o.item_count} item${o.item_count !== 1 ? "s" : ""}` : ""}</div>
                  </div>
                  <StatusBadge s={o.status} />
                </div>
              ))}
              {orders.length === 0 && <p style={{ fontSize: "0.72rem", color: "#334155" }}>No orders yet.</p>}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────
const SORT_OPTIONS = [
  { value: "last_order_at", label: "Recent order" },
  { value: "total_spent", label: "Highest spend" },
  { value: "total_orders", label: "Most orders" },
  { value: "created_at", label: "Newest customer" },
];

export default function Customers() {
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [stats, setStats] = useState<CRMStats>(MOCK_STATS);
  const [search, setSearch] = useState("");
  const [filterSeg, setFilterSeg] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState("last_order_at");
  const [selected, setSelected] = useState<CustomerSummary | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const PAGE_SIZE = 15;

  const fetchStats = useCallback(async () => {
    try { const r = await api.get("/customers/stats"); setStats(r.data); } catch {}
  }, []);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = { page, page_size: PAGE_SIZE, sort_by: sortBy };
      if (search) params.search = search;
      if (filterSeg) params.segment = filterSeg;
      const r = await api.get("/customers", { params });
      setCustomers(r.data.items);
      setTotal(r.data.total);
    } catch {
      setCustomers(MOCK_CUSTOMERS);
      setTotal(MOCK_CUSTOMERS.length);
    } finally {
      setLoading(false);
    }
  }, [page, search, filterSeg, sortBy]);

  useEffect(() => { fetchStats(); }, [fetchStats]);
  useEffect(() => { const t = setTimeout(fetchCustomers, 300); return () => clearTimeout(t); }, [fetchCustomers]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const handleUpdate = useCallback((updated: CustomerSummary) => {
    setCustomers(cs => cs.map(c => c.id === updated.id ? updated : c));
    setSelected(updated);
  }, []);

  const handleExport = () => window.open("/api/customers/export", "_blank");

  return (
    <div style={{ fontFamily: "'DM Sans','Helvetica Neue',sans-serif", background: "#07070f", minHeight: "100vh", color: "#e2e8f0" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap');
        *{box-sizing:border-box}
        ::-webkit-scrollbar{width:5px;height:5px}
        ::-webkit-scrollbar-track{background:#0a0a14}
        ::-webkit-scrollbar-thumb{background:#1e2235;border-radius:3px}
        .row-hover:hover{background:#0d0d1a!important;cursor:pointer}
        .seg-btn:hover{opacity:.8}
        input:focus,textarea:focus,select:focus{outline:none!important;border-color:#3b82f6!important}
      `}</style>

      <div style={{ maxWidth: "1400px", margin: "0 auto", padding: "2rem 1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "2rem", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.6rem", letterSpacing: "0.3em", textTransform: "uppercase", color: "#334155", marginBottom: "0.4rem" }}>CRM</div>
            <h1 style={{ fontSize: "1.8rem", fontWeight: 600, color: "#f8fafc", letterSpacing: "-0.03em" }}>Customers</h1>
            <p style={{ fontSize: "0.75rem", color: "#334155", marginTop: "0.3rem" }}>
              {stats.total_customers.toLocaleString()} total · {stats.new_this_month} new this month
            </p>
          </div>
          <button onClick={handleExport} style={{ display: "flex", alignItems: "center", gap: "0.5rem", background: "#0e0e18", border: "1px solid #1e2235", borderRadius: "7px", color: "#94a3b8", fontSize: "0.72rem", padding: "0.5rem 1rem", cursor: "pointer" }}>
            ↓ Export CSV
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "0.75rem", marginBottom: "1.75rem" }}>
          <StatCard label="Total Revenue" value={fmtMoney(stats.total_revenue)} sub={`avg ${fmtMoney(stats.avg_customer_value)} / customer`} accent="#3b82f6" />
          <StatCard label="VIP Customers" value={stats.vip_count} sub="spent $500+" accent="#f59e0b" />
          <StatCard label="Repeat Buyers" value={stats.repeat_buyers} sub={`${Math.round(stats.repeat_buyers / Math.max(stats.total_customers, 1) * 100)}% of total`} accent="#34d399" />
          <StatCard label="At Risk" value={stats.at_risk_count} sub="no order in 60+ days" accent="#f87171" />
        </div>

        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", background: "#0a0a14", border: "1px solid #1e2235", borderRadius: "10px", padding: "0.75rem 1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search name or @username…" style={{ flex: 1, minWidth: "180px", background: "#0e0e18", border: "1px solid #1e2235", borderRadius: "6px", color: "#e2e8f0", fontSize: "0.78rem", padding: "0.45rem 0.75rem" }} />
          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
            {SEGMENTS.map(s => {
              const m = SEG_META[s]; const active = filterSeg === s;
              return (
                <button key={s} className="seg-btn" onClick={() => { setFilterSeg(active ? null : s); setPage(1); }} style={{ fontSize: "0.62rem", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", padding: "3px 10px", borderRadius: "20px", cursor: "pointer", transition: "all .15s", color: active ? m.color : "#475569", background: active ? m.bg : "transparent", border: `1px solid ${active ? m.color + "40" : "#1e2235"}` }}>{m.label}</button>
              );
            })}
            {filterSeg && <button onClick={() => setFilterSeg(null)} style={{ fontSize: "0.62rem", padding: "3px 8px", borderRadius: "20px", background: "transparent", border: "1px solid #1e2235", color: "#475569", cursor: "pointer" }}>✕ clear</button>}
          </div>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ background: "#0e0e18", border: "1px solid #1e2235", borderRadius: "6px", color: "#94a3b8", fontSize: "0.72rem", padding: "0.45rem 0.65rem", cursor: "pointer" }}>
            {SORT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div style={{ background: "#0a0a14", border: "1px solid #1e2235", borderRadius: "10px", overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 1fr", padding: "0.6rem 1.25rem", borderBottom: "1px solid #1e2235" }}>
            {["Customer", "Segments", "Orders", "Spent", "Last Order", "Last Seen"].map(h => (
              <div key={h} style={{ fontSize: "0.58rem", letterSpacing: "0.12em", textTransform: "uppercase", color: "#334155", fontWeight: 600 }}>{h}</div>
            ))}
          </div>

          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 1fr", padding: "0.75rem 1.25rem", borderBottom: "1px solid #111121" }}>
                {Array.from({ length: 6 }).map((_, j) => (
                  <div key={j} style={{ height: "16px", background: "#1e2235", borderRadius: "4px", marginRight: "1rem", animation: "pulse 1.5s infinite" }} />
                ))}
              </div>
            ))
          ) : customers.length === 0 ? (
            <div style={{ padding: "3rem", textAlign: "center", color: "#334155", fontSize: "0.8rem" }}>No customers match your filters</div>
          ) : customers.map(c => (
            <div key={c.id} className="row-hover" onClick={() => setSelected(c)} style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr 1fr 1fr", padding: "0.75rem 1.25rem", borderBottom: "1px solid #111121", alignItems: "center", transition: "background .1s" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.65rem" }}>
                <div style={{ width: "32px", height: "32px", borderRadius: "8px", flexShrink: 0, background: `hsl(${c.telegram_user_id % 360},35%,20%)`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700, color: `hsl(${c.telegram_user_id % 360},65%,70%)`, fontFamily: "'JetBrains Mono',monospace" }}>
                  {c.display_name.charAt(0)}
                </div>
                <div>
                  <div style={{ fontSize: "0.8rem", fontWeight: 500, color: "#e2e8f0" }}>{c.display_name}</div>
                  {c.telegram_username && <div style={{ fontSize: "0.62rem", color: "#334155" }}>@{c.telegram_username}</div>}
                </div>
              </div>
              <div style={{ display: "flex", gap: "0.3rem", flexWrap: "wrap" }}>
                {c.segments.slice(0, 2).map(s => <Pill key={s} seg={s} />)}
                {c.segments.length > 2 && <span style={{ fontSize: "0.58rem", color: "#334155" }}>+{c.segments.length - 2}</span>}
              </div>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "0.8rem", color: "#94a3b8", fontWeight: 600 }}>{c.total_orders}</div>
              <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "0.8rem", color: "#f1f5f9", fontWeight: 600 }}>{fmtMoney(c.total_spent)}</div>
              <div style={{ fontSize: "0.72rem", color: "#475569" }}>{fmtDate(c.last_order_at)}</div>
              <div style={{ fontSize: "0.72rem", color: "#334155" }}>{timeSince(c.last_seen_at)}</div>
            </div>
          ))}
        </div>

        {totalPages > 1 && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem", padding: "0 0.25rem" }}>
            <span style={{ fontSize: "0.68rem", color: "#334155" }}>
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
            </span>
            <div style={{ display: "flex", gap: "0.35rem" }}>
              {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map(p => (
                <button key={p} onClick={() => setPage(p)} style={{ width: "28px", height: "28px", borderRadius: "5px", fontSize: "0.7rem", background: page === p ? "#3b82f6" : "transparent", border: `1px solid ${page === p ? "#3b82f6" : "#1e2235"}`, color: page === p ? "white" : "#475569", cursor: "pointer" }}>{p}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      <CustomerDrawer customer={selected} onClose={() => setSelected(null)} onUpdate={handleUpdate} />
    </div>
  );
}

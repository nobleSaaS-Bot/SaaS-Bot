import { Link, useLocation } from "wouter";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "grid" },
  { href: "/ai-builder", label: "AI Builder", icon: "sparkles" },
  { href: "/products", label: "Products", icon: "box" },
  { href: "/orders", label: "Orders", icon: "shopping-cart" },
  { href: "/customers", label: "Customers", icon: "users" },
  { href: "/broadcasts", label: "Broadcasts", icon: "megaphone" },
  { href: "/analytics", label: "Analytics", icon: "bar-chart-2" },
  { href: "/store-preview", label: "Store Preview", icon: "eye" },
  { href: "/pricing", label: "Pricing", icon: "credit-card" },
];

const ICONS: Record<string, string> = {
  grid: "M3 3h7v7H3zm11 0h7v7h-7zM3 14h7v7H3zm11 0h7v7h-7z",
  sparkles: "M12 2l2.4 7.4H22l-6.2 4.5 2.4 7.4L12 17l-6.2 3.3 2.4-7.4L2 9.4h7.6z",
  box: "M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z",
  "shopping-cart": "M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0",
  users: "M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75",
  megaphone: "M18 8h1a4 4 0 010 8h-1M2 8h16v9a4 4 0 01-4 4H6a4 4 0 01-4-4V8zM6 1v3M10 1v3M14 1v3",
  "bar-chart-2": "M18 20V10M12 20V4M6 20v-6",
  eye: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 9a3 3 0 100 6 3 3 0 000-6z",
  "credit-card": "M1 4h22v16H1zM1 10h22",
};

export default function Sidebar() {
  const [location] = useLocation();

  return (
    <aside className="hidden md:flex flex-col w-60 border-r bg-sidebar text-sidebar-foreground shrink-0">
      <div className="flex items-center gap-2 px-5 py-4 border-b">
        <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 text-primary-foreground">
            <path d={ICONS["box"]} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <span className="font-bold text-sm">SaaSBot</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive = location === item.href;
          return (
            <Link key={item.href} href={item.href}>
              <a className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "hover:bg-sidebar-accent text-sidebar-foreground/70 hover:text-sidebar-accent-foreground"
              }`}>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4 shrink-0">
                  <path d={ICONS[item.icon] ?? ""} strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {item.label}
              </a>
            </Link>
          );
        })}
      </nav>

      <div className="px-3 pb-4">
        <button
          onClick={() => { localStorage.removeItem("auth_token"); window.location.href = "/login"; }}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-sidebar-foreground/60 hover:text-sidebar-foreground w-full hover:bg-sidebar-accent transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Logout
        </button>
      </div>
    </aside>
  );
}

import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { formatCurrency } from "@/utils/formatCurrency";

interface SummaryStats {
  total_revenue: number;
  monthly_revenue: number;
  total_orders: number;
  pending_orders: number;
}

export default function Dashboard() {
  const [stats, setStats] = useState<SummaryStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storeId = localStorage.getItem("active_store_id");
    if (!storeId) {
      setLoading(false);
      return;
    }
    api
      .get(`/analytics/summary?store_id=${storeId}`)
      .then((res) => setStats(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-muted-foreground">Loading dashboard...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Revenue" value={formatCurrency(stats?.total_revenue ?? 0)} />
        <StatCard label="Monthly Revenue" value={formatCurrency(stats?.monthly_revenue ?? 0)} />
        <StatCard label="Total Orders" value={String(stats?.total_orders ?? 0)} />
        <StatCard label="Pending Orders" value={String(stats?.pending_orders ?? 0)} />
      </div>

      <div className="rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <a href="/products" className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90">
            Manage Products
          </a>
          <a href="/orders" className="px-4 py-2 rounded-lg bg-secondary text-secondary-foreground text-sm font-medium hover:opacity-90">
            View Orders
          </a>
          <a href="/ai-builder" className="px-4 py-2 rounded-lg border text-sm font-medium hover:bg-accent">
            AI Store Builder
          </a>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border p-5 space-y-1">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}

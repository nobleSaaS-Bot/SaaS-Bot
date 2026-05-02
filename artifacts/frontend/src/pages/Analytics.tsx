import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { formatCurrency } from "@/utils/formatCurrency";
import Loader from "@/components/Loader";

interface DataPoint {
  date: string;
  orders: number;
  revenue: number;
}

export default function Analytics() {
  const [data, setData] = useState<DataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);

  useEffect(() => {
    const storeId = localStorage.getItem("active_store_id");
    if (!storeId) {
      setLoading(false);
      return;
    }
    api
      .get(`/analytics/orders-over-time?store_id=${storeId}&days=${days}`)
      .then((res) => setData(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [days]);

  const totalRevenue = data.reduce((sum, d) => sum + d.revenue, 0);
  const totalOrders = data.reduce((sum, d) => sum + d.orders, 0);

  if (loading) return <Loader />;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Analytics</h1>
        <select
          className="rounded-lg border px-3 py-1.5 text-sm bg-background"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border p-5">
          <p className="text-sm text-muted-foreground">Revenue (period)</p>
          <p className="text-2xl font-bold mt-1">{formatCurrency(totalRevenue)}</p>
        </div>
        <div className="rounded-xl border p-5">
          <p className="text-sm text-muted-foreground">Orders (period)</p>
          <p className="text-2xl font-bold mt-1">{totalOrders}</p>
        </div>
      </div>

      {data.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground rounded-xl border">
          <p>No data for this period.</p>
        </div>
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Date</th>
                <th className="text-right px-4 py-3 font-medium">Orders</th>
                <th className="text-right px-4 py-3 font-medium">Revenue</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {data.map((row) => (
                <tr key={row.date} className="hover:bg-muted/30">
                  <td className="px-4 py-2">{row.date}</td>
                  <td className="px-4 py-2 text-right">{row.orders}</td>
                  <td className="px-4 py-2 text-right font-medium">{formatCurrency(row.revenue)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

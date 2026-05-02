import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { formatCurrency } from "@/utils/formatCurrency";
import Loader from "@/components/Loader";

interface Order {
  id: string;
  customer_name: string | null;
  customer_telegram_id: string;
  total: number;
  currency: string;
  status: string;
  created_at: string;
  items: { name: string; quantity: number; price: number }[];
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  paid: "bg-green-100 text-green-800",
  processing: "bg-purple-100 text-purple-800",
  shipped: "bg-indigo-100 text-indigo-800",
  delivered: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-red-100 text-red-800",
  refunded: "bg-gray-100 text-gray-800",
};

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storeId = localStorage.getItem("active_store_id");
    if (!storeId) {
      setLoading(false);
      return;
    }
    api
      .get(`/orders/?store_id=${storeId}`)
      .then((res) => setOrders(res.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <div className="p-6 space-y-5">
      <h1 className="text-2xl font-bold">Orders</h1>

      {orders.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg">No orders yet.</p>
          <p className="text-sm mt-1">Orders placed via your Telegram bot will appear here.</p>
        </div>
      ) : (
        <div className="rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left px-4 py-3 font-medium">Order</th>
                <th className="text-left px-4 py-3 font-medium">Customer</th>
                <th className="text-left px-4 py-3 font-medium">Items</th>
                <th className="text-left px-4 py-3 font-medium">Total</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {orders.map((order) => (
                <tr key={order.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs">{order.id.slice(0, 8).toUpperCase()}</td>
                  <td className="px-4 py-3">{order.customer_name || order.customer_telegram_id}</td>
                  <td className="px-4 py-3 text-muted-foreground">{order.items?.length ?? 0} item(s)</td>
                  <td className="px-4 py-3 font-medium">{formatCurrency(order.total, order.currency)}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[order.status] ?? "bg-muted text-muted-foreground"}`}>
                      {order.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(order.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

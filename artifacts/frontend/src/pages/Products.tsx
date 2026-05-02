import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { formatCurrency } from "@/utils/formatCurrency";
import ProductCard from "@/components/ProductCard";
import Loader from "@/components/Loader";

interface Product {
  id: string;
  name: string;
  description: string | null;
  price: number;
  stock_quantity: number;
  is_active: boolean;
  images: string[] | null;
}

export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storeId = localStorage.getItem("active_store_id");
    if (!storeId) {
      setLoading(false);
      return;
    }
    api
      .get(`/products/?store_id=${storeId}`)
      .then((res) => setProducts(res.data))
      .catch(() => setError("Failed to load products."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Products</h1>
        <button className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90">
          + Add Product
        </button>
      </div>

      {error && <p className="text-destructive text-sm">{error}</p>}

      {products.length === 0 && !error ? (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg">No products yet.</p>
          <p className="text-sm mt-1">Add your first product or use the AI Builder.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {products.map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { api } from "@/services/api";
import { getSubdomain } from "@/utils/getSubdomain";
import Loader from "@/components/Loader";

interface Store {
  id: string;
  name: string;
  description: string | null;
  subdomain: string | null;
  custom_domain: string | null;
  currency: string;
  logo_url: string | null;
  theme: Record<string, string> | null;
}

interface Product {
  id: string;
  name: string;
  price: number;
  description: string | null;
  images: string[] | null;
}

export default function StorePreview() {
  const [store, setStore] = useState<Store | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storeId = localStorage.getItem("active_store_id");
    if (!storeId) {
      setLoading(false);
      return;
    }

    Promise.all([
      api.get(`/stores/${storeId}`),
      api.get(`/products/?store_id=${storeId}&is_active=true`),
    ])
      .then(([storeRes, productsRes]) => {
        setStore(storeRes.data);
        setProducts(productsRes.data);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loader />;

  if (!store) {
    return (
      <div className="p-6 text-center text-muted-foreground">
        <p>No store selected. Create a store to preview it here.</p>
      </div>
    );
  }

  const storeUrl = store.custom_domain
    ? `https://${store.custom_domain}`
    : store.subdomain
    ? `https://${store.subdomain}.yoursaasplatform.com`
    : null;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">{store.name}</h1>
          {store.description && <p className="text-muted-foreground mt-1">{store.description}</p>}
          {storeUrl && (
            <a href={storeUrl} target="_blank" rel="noopener noreferrer" className="text-primary text-sm hover:underline mt-1 block">
              {storeUrl}
            </a>
          )}
        </div>
        <div className="flex gap-2">
          <button className="px-4 py-2 rounded-lg border text-sm font-medium hover:bg-accent">
            Edit Store
          </button>
          <button className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90">
            Configure Bot
          </button>
        </div>
      </div>

      {store.theme && (
        <div className="rounded-xl border p-4 space-y-2">
          <h2 className="text-sm font-semibold">Branding</h2>
          <div className="flex gap-3 flex-wrap">
            {["primary_color", "secondary_color", "accent_color"].map((key) =>
              store.theme?.[key] ? (
                <div key={key} className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full border" style={{ backgroundColor: store.theme![key] }} />
                  <span className="text-xs text-muted-foreground">{key.replace("_color", "")}</span>
                </div>
              ) : null
            )}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold mb-3">Products ({products.length})</h2>
        {products.length === 0 ? (
          <p className="text-muted-foreground text-sm">No products yet.</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {products.map((product) => (
              <div key={product.id} className="rounded-xl border overflow-hidden">
                <div className="aspect-square bg-muted flex items-center justify-center">
                  {product.images?.[0] ? (
                    <img src={product.images[0]} alt={product.name} className="object-cover w-full h-full" />
                  ) : (
                    <span className="text-muted-foreground text-xs">No image</span>
                  )}
                </div>
                <div className="p-3">
                  <p className="text-sm font-medium truncate">{product.name}</p>
                  <p className="text-sm text-primary font-semibold">{store.currency} {Number(product.price).toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

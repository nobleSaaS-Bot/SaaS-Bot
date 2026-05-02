import { useEffect, useState } from "react";
import { api } from "@/services/api";

interface Store {
  id: string;
  name: string;
}

export default function Navbar() {
  const [stores, setStores] = useState<Store[]>([]);
  const [activeStoreId, setActiveStoreId] = useState<string>(
    () => localStorage.getItem("active_store_id") ?? ""
  );

  useEffect(() => {
    api
      .get("/stores/")
      .then((res) => {
        setStores(res.data);
        if (!activeStoreId && res.data.length > 0) {
          setActiveStoreId(res.data[0].id);
          localStorage.setItem("active_store_id", res.data[0].id);
        }
      })
      .catch(console.error);
  }, []);

  const handleStoreChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setActiveStoreId(e.target.value);
    localStorage.setItem("active_store_id", e.target.value);
    window.location.reload();
  };

  return (
    <header className="border-b px-5 py-3 flex items-center justify-between bg-background shrink-0">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground hidden sm:block">Store:</span>
        {stores.length > 0 ? (
          <select
            value={activeStoreId}
            onChange={handleStoreChange}
            className="text-sm rounded-lg border px-3 py-1.5 bg-background"
          >
            {stores.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        ) : (
          <a href="/store-preview" className="text-sm text-primary hover:underline">Create your first store</a>
        )}
      </div>

      <div className="flex items-center gap-3">
        <a
          href="/ai-builder"
          className="px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-medium hover:bg-primary/20 transition-colors"
        >
          AI Builder
        </a>
        <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-sm font-medium">
          M
        </div>
      </div>
    </header>
  );
}

import { useState } from "react";
import { api } from "@/services/api";

interface BuildForm {
  business_name: string;
  business_type: string;
  description: string;
  target_audience: string;
  style_preferences: string;
  num_products: number;
}

export default function AIBuilder() {
  const [form, setForm] = useState<BuildForm>({
    business_name: "",
    business_type: "",
    description: "",
    target_audience: "",
    style_preferences: "",
    num_products: 5,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const storeId = localStorage.getItem("active_store_id");
    if (!storeId) {
      setError("Please select or create a store first.");
      setLoading(false);
      return;
    }

    try {
      await api.post("/ai/build-store", { ...form, store_id: storeId });
      setResult("Your store is being built with AI. Check back in a moment to see your products, categories, and branding.");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">AI Store Builder</h1>
        <p className="text-muted-foreground mt-1">
          Describe your business and let AI generate your store, products, categories, and branding.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Business Name" required>
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm bg-background"
            value={form.business_name}
            onChange={(e) => setForm({ ...form, business_name: e.target.value })}
            required
          />
        </Field>

        <Field label="Business Type" hint="e.g. Fashion, Electronics, Food, Beauty">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm bg-background"
            value={form.business_type}
            onChange={(e) => setForm({ ...form, business_type: e.target.value })}
            required
          />
        </Field>

        <Field label="Description">
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm bg-background resize-none"
            rows={3}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
        </Field>

        <Field label="Target Audience" hint="Who are your customers?">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm bg-background"
            value={form.target_audience}
            onChange={(e) => setForm({ ...form, target_audience: e.target.value })}
          />
        </Field>

        <Field label="Style Preferences" hint="e.g. modern, luxury, playful, minimal">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm bg-background"
            value={form.style_preferences}
            onChange={(e) => setForm({ ...form, style_preferences: e.target.value })}
          />
        </Field>

        <Field label={`Number of Products: ${form.num_products}`}>
          <input
            type="range"
            min={1}
            max={20}
            value={form.num_products}
            onChange={(e) => setForm({ ...form, num_products: Number(e.target.value) })}
            className="w-full"
          />
        </Field>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {result && <p className="text-sm text-green-600">{result}</p>}

        <button
          type="submit"
          disabled={loading}
          className="px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Building..." : "Build Store with AI"}
        </button>
      </form>
    </div>
  );
}

function Field({ label, hint, required, children }: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="text-destructive ml-1">*</span>}
      </label>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      {children}
    </div>
  );
}

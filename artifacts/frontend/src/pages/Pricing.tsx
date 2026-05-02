import { useEffect, useState } from "react";
import { api } from "@/services/api";

interface Plan {
  name: string;
  price_monthly: number;
  price_yearly: number;
  limits: Record<string, any>;
}

const FEATURE_LABELS: Record<string, string> = {
  products: "Products",
  orders_per_month: "Orders / month",
  stores: "Stores",
  flows: "Conversation flows",
  ai_store_builder: "AI Store Builder",
  analytics: "Analytics",
  custom_domain: "Custom domain",
  payment_providers: "Payment providers",
  team_members: "Team members",
};

function formatLimit(value: any): string {
  if (value === true) return "Yes";
  if (value === false) return "No";
  if (value === -1) return "Unlimited";
  return String(value);
}

export default function Pricing() {
  const [plans, setPlans] = useState<Record<string, Plan>>({});
  const [billing, setBilling] = useState<"monthly" | "yearly">("monthly");

  useEffect(() => {
    api.get("/billing/plans").then((res) => setPlans(res.data)).catch(console.error);
  }, []);

  const planKeys = Object.keys(plans);

  return (
    <div className="p-6 space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Pricing Plans</h1>
        <p className="text-muted-foreground">Choose the right plan for your business.</p>
        <div className="inline-flex rounded-lg border p-1 gap-1 mt-2">
          <button
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${billing === "monthly" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
            onClick={() => setBilling("monthly")}
          >
            Monthly
          </button>
          <button
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${billing === "yearly" ? "bg-primary text-primary-foreground" : "hover:bg-muted"}`}
            onClick={() => setBilling("yearly")}
          >
            Yearly <span className="text-xs opacity-75">-17%</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {planKeys.map((key) => {
          const plan = plans[key];
          const price = billing === "monthly" ? plan.price_monthly : plan.price_yearly;
          return (
            <div key={key} className={`rounded-xl border p-5 space-y-4 ${key === "pro" ? "border-primary ring-1 ring-primary" : ""}`}>
              {key === "pro" && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-primary text-primary-foreground">Popular</span>
              )}
              <div>
                <h2 className="text-lg font-bold">{plan.name}</h2>
                <p className="text-3xl font-bold mt-1">
                  ${price}
                  <span className="text-sm font-normal text-muted-foreground">/{billing === "monthly" ? "mo" : "yr"}</span>
                </p>
              </div>
              <ul className="space-y-2 text-sm">
                {Object.entries(plan.limits).map(([feat, val]) => (
                  <li key={feat} className="flex justify-between gap-2">
                    <span className="text-muted-foreground">{FEATURE_LABELS[feat] ?? feat}</span>
                    <span className={`font-medium ${val === false ? "text-muted-foreground line-through" : ""}`}>
                      {formatLimit(val)}
                    </span>
                  </li>
                ))}
              </ul>
              <button className="w-full py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90">
                {price === 0 ? "Get Started Free" : "Subscribe"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

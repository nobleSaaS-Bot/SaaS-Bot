import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import AIBuilder from "@/pages/AIBuilder";
import Products from "@/pages/Products";
import Orders from "@/pages/Orders";
import Analytics from "@/pages/Analytics";
import Pricing from "@/pages/Pricing";
import StorePreview from "@/pages/StorePreview";
import Customers from "@/pages/Customers";
import Broadcasts from "@/pages/Broadcasts";
import Login from "@/pages/Login";
import { isAuthenticated } from "@/services/auth";

const queryClient = new QueryClient();

function ProtectedRoute({ component: Component }: { component: React.ComponentType }) {
  if (!isAuthenticated()) {
    window.location.replace(import.meta.env.BASE_URL + "login");
    return null;
  }
  return (
    <Layout>
      <Component />
    </Layout>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/login" component={Login} />
      <Route path="/" component={() => <ProtectedRoute component={Dashboard} />} />
      <Route path="/ai-builder" component={() => <ProtectedRoute component={AIBuilder} />} />
      <Route path="/products" component={() => <ProtectedRoute component={Products} />} />
      <Route path="/orders" component={() => <ProtectedRoute component={Orders} />} />
      <Route path="/analytics" component={() => <ProtectedRoute component={Analytics} />} />
      <Route path="/pricing" component={() => <ProtectedRoute component={Pricing} />} />
      <Route path="/customers" component={() => <ProtectedRoute component={Customers} />} />
      <Route path="/broadcasts" component={() => <ProtectedRoute component={Broadcasts} />} />
      <Route path="/store-preview" component={() => <ProtectedRoute component={StorePreview} />} />
      <Route>
        <div className="flex items-center justify-center min-h-screen text-muted-foreground">
          Page not found.
        </div>
      </Route>
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

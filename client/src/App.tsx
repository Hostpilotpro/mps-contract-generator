import { Switch, Route, Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { queryClient, apiRequest } from "./lib/queryClient";
import { QueryClientProvider, useQuery, useMutation } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import WizardPage from "@/pages/wizard";
import Login from "@/pages/login";
import NotFound from "@/pages/not-found";
import { LogOut } from "lucide-react";

function AuthWrapper() {
  // Check if user is logged in
  const { data, isLoading } = useQuery({
    queryKey: ["/api/me"],
    queryFn: () => apiRequest("GET", "/api/me").then(r => r.json()).catch(() => null),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const logoutMutation = useMutation({
    mutationFn: () => apiRequest("POST", "/api/logout", {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/me"] });
    },
  });

  const handleLogin = () => {
    queryClient.invalidateQueries({ queryKey: ["/api/me"] });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "#1C2340" }}>
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: "#9B7E52", borderTopColor: "transparent" }} />
      </div>
    );
  }

  const user = data?.user;

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <>
      {/* Logout bar */}
      <div
        className="fixed top-0 right-0 z-50 flex items-center gap-3 px-4 py-2"
        style={{ background: "rgba(28,35,64,0.95)", borderBottom: "1px solid rgba(155,126,82,0.2)", backdropFilter: "blur(8px)" }}
      >
        <span className="text-xs font-semibold" style={{ color: "#9B7E52", letterSpacing: "0.1em" }}>
          {user.username}
          <span className="ml-2 px-1.5 py-0.5 rounded text-xs" style={{ background: "rgba(155,126,82,0.2)", color: "#C4A97A" }}>
            {user.role.toUpperCase()}
          </span>
        </span>
        <button
          onClick={() => logoutMutation.mutate()}
          className="flex items-center gap-1 text-xs opacity-60 hover:opacity-100 transition-opacity"
          style={{ color: "#F5F0E8" }}
          data-testid="button-logout"
        >
          <LogOut className="w-3.5 h-3.5" />
          Sign out
        </button>
      </div>
      {/* Main app with top padding for the bar */}
      <div className="pt-9">
        <Router hook={useHashLocation}>
          <Switch>
            <Route path="/" component={WizardPage} />
            <Route path="/wizard" component={WizardPage} />
            <Route component={NotFound} />
          </Switch>
        </Router>
      </div>
    </>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <AuthWrapper />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;

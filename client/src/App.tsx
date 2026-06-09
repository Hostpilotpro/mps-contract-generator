import { useState } from "react";
import { Switch, Route, Router } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { queryClient, apiRequest } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import WizardPage from "@/pages/wizard";
import Login from "@/pages/login";
import NotFound from "@/pages/not-found";
import { authStore } from "@/lib/authStore";
import { LogOut } from "lucide-react";

function AuthWrapper() {
  const [user, setUser] = useState<{ username: string; role: string } | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogin = (token: string, u: { username: string; role: string }) => {
    authStore.login(token, u);
    setUser(u);
    // Re-fetch any protected queries now that we have a token
    queryClient.invalidateQueries();
  };

  const handleLogout = async () => {
    setLoggingOut(true);
    try { await apiRequest("POST", "/api/logout", {}); } catch {}
    authStore.logout();
    queryClient.clear();
    setUser(null);
    setLoggingOut(false);
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <>
      {/* Top auth bar */}
      <div
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-end gap-3 px-4 py-2"
        style={{
          background: "rgba(28,35,64,0.97)",
          borderBottom: "1px solid rgba(155,126,82,0.25)",
          backdropFilter: "blur(8px)",
          height: "36px",
        }}
      >
        <span className="text-xs font-semibold" style={{ color: "#9B7E52", letterSpacing: "0.1em" }}>
          {user.username}
          <span
            className="ml-2 px-1.5 py-0.5 rounded text-xs"
            style={{ background: "rgba(155,126,82,0.2)", color: "#C4A97A" }}
          >
            {user.role.toUpperCase()}
          </span>
        </span>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="flex items-center gap-1 text-xs opacity-60 hover:opacity-100 transition-opacity"
          style={{ color: "#F5F0E8" }}
          data-testid="button-logout"
        >
          <LogOut className="w-3.5 h-3.5" />
          {loggingOut ? "..." : "Sign out"}
        </button>
      </div>

      {/* Main content — pushed below the bar */}
      <div style={{ paddingTop: "36px" }}>
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

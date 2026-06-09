import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface LoginProps {
  onLogin: (token: string, user: { username: string; role: string }) => void;
}

export default function Login({ onLogin }: LoginProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");

  const loginMutation = useMutation({
    mutationFn: () =>
      apiRequest("POST", "/api/login", { username, password }),
    onSuccess: async (res) => {
      const data = await res.json();
      if (data.success && data.token) {
        onLogin(data.token, { username: data.username, role: data.role });
      } else {
        setError(data.error || "Invalid credentials");
      }
    },
    onError: () => setError("Invalid username or password"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!username || !password) { setError("Please enter username and password"); return; }
    loginMutation.mutate();
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: "linear-gradient(135deg, #1C2340 0%, #2A3558 60%, #1C2340 100%)" }}
    >
      <div className="w-full max-w-sm mx-4">
        {/* Logo + title */}
        <div className="text-center mb-8">
          <img
            src="/logo.jpg"
            alt="Mr Property Siam"
            className="w-24 h-24 mx-auto rounded-2xl shadow-2xl object-contain mb-4"
            style={{ background: "white", padding: "4px" }}
          />
          <h1
            className="text-2xl font-bold tracking-wide"
            style={{ color: "#F5F0E8", fontFamily: "'Playfair Display', Georgia, serif" }}
          >
            MR PROPERTY SIAM
          </h1>
          <p className="text-sm mt-1" style={{ color: "#9B7E52", letterSpacing: "0.15em" }}>
            HR PORTAL
          </p>
        </div>

        {/* Card */}
        <div
          className="rounded-2xl p-7 shadow-2xl"
          style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(155,126,82,0.3)", backdropFilter: "blur(10px)" }}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold mb-1.5 tracking-wider" style={{ color: "#9B7E52" }}>
                USERNAME
              </label>
              <Input
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter username"
                autoComplete="username"
                data-testid="input-username"
                className="border-0 text-white placeholder:text-gray-500"
                style={{ background: "rgba(255,255,255,0.08)", outline: "1px solid rgba(155,126,82,0.4)" }}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold mb-1.5 tracking-wider" style={{ color: "#9B7E52" }}>
                PASSWORD
              </label>
              <Input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter password"
                autoComplete="current-password"
                data-testid="input-password"
                className="border-0 text-white placeholder:text-gray-500"
                style={{ background: "rgba(255,255,255,0.08)", outline: "1px solid rgba(155,126,82,0.4)" }}
              />
            </div>

            {error && (
              <p className="text-xs text-red-400 text-center">{error}</p>
            )}

            <Button
              type="submit"
              className="w-full py-2.5 font-semibold tracking-wider text-sm mt-2"
              style={{ background: "#9B7E52", color: "white", border: "none" }}
              disabled={loginMutation.isPending}
              data-testid="button-login"
            >
              {loginMutation.isPending ? "Signing in..." : "SIGN IN"}
            </Button>
          </form>

          <p className="text-center mt-5 text-xs" style={{ color: "rgba(245,240,232,0.3)" }}>
            Mister Property Siam Co.,LTD · Internal Use Only
          </p>
        </div>
      </div>
    </div>
  );
}

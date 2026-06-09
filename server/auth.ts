import type { Request, Response, NextFunction } from "express";

// ── User accounts ─────────────────────────────────────────────────────────────
export const USERS: Record<string, { password: string; role: "hr" | "admin" }> = {
  "HRSIAM": { password: process.env.HR_PASSWORD   || "mps2026hr",    role: "hr"    },
  "ADMIN":  { password: process.env.ADMIN_PASSWORD || "mps2026admin", role: "admin" },
};

// ── Auth middleware ───────────────────────────────────────────────────────────
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const session = (req as any).session;
  if (session?.user) return next();
  res.status(401).json({ error: "Authentication required" });
}

// ── Register auth routes ──────────────────────────────────────────────────────
export function registerAuthRoutes(app: any) {
  app.post("/api/login", (req: Request, res: Response) => {
    const { username, password } = req.body || {};
    const user = USERS[String(username || "").toUpperCase()];
    if (user && user.password === password) {
      (req as any).session.user = { username: String(username).toUpperCase(), role: user.role };
      res.json({ success: true, role: user.role });
    } else {
      res.status(401).json({ success: false, error: "Invalid username or password" });
    }
  });

  app.post("/api/logout", (req: Request, res: Response) => {
    (req as any).session.destroy(() => res.json({ success: true }));
  });

  app.get("/api/me", (req: Request, res: Response) => {
    const session = (req as any).session;
    if (session?.user) res.json({ user: session.user });
    else res.status(401).json({ error: "Not authenticated" });
  });
}

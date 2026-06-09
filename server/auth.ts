import type { Request, Response, NextFunction } from "express";
import { createHmac } from "crypto";

// ── Credentials ───────────────────────────────────────────────────────────────
const SECRET = process.env.SESSION_SECRET || "mps-hr-koh-samui-2026";
const USERS: Record<string, { password: string; role: "hr" | "admin" }> = {
  "HRSIAM": { password: process.env.HR_PASSWORD    || "mps2026hr",    role: "hr"    },
  "ADMIN":  { password: process.env.ADMIN_PASSWORD  || "mps2026admin", role: "admin" },
};

// ── Token helpers ─────────────────────────────────────────────────────────────
function makeToken(username: string, role: string): string {
  const payload = `${username}:${role}`;
  const sig     = createHmac("sha256", SECRET).update(payload).digest("hex");
  return Buffer.from(`${payload}:${sig}`).toString("base64");
}

function verifyToken(token: string): { username: string; role: string } | null {
  try {
    const decoded  = Buffer.from(token, "base64").toString("utf8");
    const parts    = decoded.split(":");
    if (parts.length !== 3) return null;
    const [username, role, sig] = parts;
    const expected = createHmac("sha256", SECRET).update(`${username}:${role}`).digest("hex");
    if (sig !== expected) return null;
    return { username, role };
  } catch {
    return null;
  }
}

// ── Middleware ────────────────────────────────────────────────────────────────
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  const auth = req.headers.authorization || "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  const user  = verifyToken(token);
  if (user) { (req as any).currentUser = user; return next(); }
  res.status(401).json({ error: "Authentication required" });
}

// ── Routes ────────────────────────────────────────────────────────────────────
export function registerAuthRoutes(app: any) {
  app.post("/api/login", (req: Request, res: Response) => {
    const { username, password } = req.body || {};
    const user = USERS[String(username || "").toUpperCase()];
    if (user && user.password === String(password || "")) {
      const u = String(username).toUpperCase();
      res.json({ success: true, token: makeToken(u, user.role), role: user.role, username: u });
    } else {
      res.status(401).json({ success: false, error: "Invalid username or password" });
    }
  });

  app.get("/api/me", (req: Request, res: Response) => {
    const auth  = req.headers.authorization || "";
    const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
    const user  = verifyToken(token);
    if (user) res.json({ user });
    else res.status(401).json({ error: "Not authenticated" });
  });
}

import type { Express } from "express";
import { createServer, type Server } from "http";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";
import https from "https";
import { requireAuth } from "./auth";

// ── Airtable sync ────────────────────────────────────────────────────────────
const AT_PAT      = process.env.AIRTABLE_PAT || "";
const AT_BASE     = "appSM9dyGsBlR1Ifq";
const AT_TABLE    = "tblLXPO5Ukr0r763N";

function syncToAirtable(data: any): void {
  if (!AT_PAT) return; // skip if no token configured

  const p       = data.contractType === "b2b" ? null : data.employee;
  const col     = data.contractType === "b2b" ? data.collaborator : null;
  const person  = p || col || {};
  const dept    = data.department || "B2B";

  const deptLabel: Record<string,string> = {
    housekeeping: "Housekeeping",
    office:       "Office / Management",
    pool:         "Pool, Garden & Handyman",
  };

  const managedVillas = (person.managedProperties || person.properties || [])
    .map((v: any) => `${v.propertyName} (Pack ${v.managementPackRate ?? "-"}% / Cut ${v.commissionRate}%)`)
    .join("\n");

  const roles = col?.roles?.join(", ") || person.additionalRoles?.join(", ") || "";

  const fields: Record<string, any> = {
    "Full Name":          person.fullName         || "",
    "Nickname":           person.nickname         || "",
    "Date of Birth":      person.dateOfBirth      || undefined,
    "Nationality":        person.nationality      || "",
    "ID / Passport":      person.idPassport       || "",
    "Phone":              person.phone            || "",
    "Email":              person.email            || "",
    "Address":            person.address          || "",
    "Contract Type":      data.contractType === "b2b" ? "B2B Collaboration" : "Employment",
    "Department":         deptLabel[dept] || dept,
    "Position / Roles":   p?.position || (col?.roles || []).join(", ") || "",
    "Additional Scope":   roles,
    "Start Date":         p?.startDate            || undefined,
    "Salary THB":         p?.salary               || undefined,
    "Contract Languages": (data.languages || []).join(", "),
    "Is Company (B2B)":   col?.isCompany          || false,
    "Company Name":       col?.companyName        || "",
    "Company Registration": col?.companyRegistration || "",
    "Managed Villas":     managedVillas,
    "Contract Generated": new Date().toISOString(),
  };

  // Remove undefined / empty values
  Object.keys(fields).forEach(k => {
    if (fields[k] === undefined || fields[k] === "") delete fields[k];
  });

  const body = JSON.stringify({ records: [{ fields }] });
  const req  = https.request({
    hostname: "api.airtable.com",
    path:     `/v0/${AT_BASE}/${AT_TABLE}`,
    method:   "POST",
    headers:  {
      "Authorization": `Bearer ${AT_PAT}`,
      "Content-Type":  "application/json",
      "Content-Length": Buffer.byteLength(body),
    },
  }, (res) => {
    let out = "";
    res.on("data", (c) => out += c);
    res.on("end", () => {
      if (res.statusCode !== 200) console.error("Airtable sync error:", res.statusCode, out.slice(0, 200));
      else console.log("Airtable: staff record saved for", person.fullName);
    });
  });
  req.on("error", (e) => console.error("Airtable sync failed:", e.message));
  req.write(body);
  req.end();
}

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.post("/api/generate", requireAuth, (req, res) => {
    const data = req.body;

    if (!data || !data.contractType) {
      return res.status(400).json({ error: "Missing contract data" });
    }

    // Resolve the generate_contract.py path — it lives at the project root
    const scriptPath = path.resolve(process.cwd(), "generate_contract.py");

    if (!fs.existsSync(scriptPath)) {
      console.error("generate_contract.py not found at:", scriptPath);
      return res.status(500).json({ error: "Generator script not found" });
    }

    const python = spawn("python3", [scriptPath], {
      cwd: process.cwd(),
      stdio: ["pipe", "pipe", "pipe"],
    });

    let outputPath = "";
    let errorOutput = "";

    // Send JSON via stdin
    try {
      python.stdin.write(JSON.stringify(data));
      python.stdin.end();
    } catch (e) {
      console.error("Failed to write to python stdin:", e);
      return res.status(500).json({ error: "Failed to start generation" });
    }

    python.stdout.on("data", (chunk: Buffer) => {
      outputPath += chunk.toString();
    });

    python.stderr.on("data", (chunk: Buffer) => {
      errorOutput += chunk.toString();
      process.stderr.write(chunk); // forward to our stderr for debugging
    });

    python.on("error", (err) => {
      console.error("Failed to spawn python3:", err);
      if (!res.headersSent) {
        res.status(500).json({ error: "Failed to start generation process" });
      }
    });

    python.on("close", (code) => {
      outputPath = outputPath.trim();

      if (code !== 0) {
        console.error(`Python exited with code ${code}. stderr:\n${errorOutput}`);
        if (!res.headersSent) {
          res.status(500).json({
            error: "Contract generation failed",
            details: errorOutput.slice(0, 500),
          });
        }
        return;
      }

      if (!outputPath || !fs.existsSync(outputPath)) {
        console.error("No output file produced. stdout:", outputPath, "stderr:", errorOutput);
        if (!res.headersSent) {
          res.status(500).json({ error: "Generation produced no output" });
        }
        return;
      }

      const filename = `MPS-Contracts-${Date.now()}.zip`;
      res.setHeader("Content-Type", "application/zip");
      res.setHeader("Content-Disposition", `attachment; filename="${filename}"`);
      res.setHeader("Content-Length", fs.statSync(outputPath).size);

      const fileStream = fs.createReadStream(outputPath);
      fileStream.pipe(res);

      fileStream.on("end", () => {
        try { fs.unlinkSync(outputPath); } catch (_) {/* ignore */}
        // Fire-and-forget Airtable sync (never blocks the download)
        try { syncToAirtable(data); } catch (_) {/* ignore */}
      });

      fileStream.on("error", (err) => {
        console.error("File stream error:", err);
      });
    });
  });

  return httpServer;
}

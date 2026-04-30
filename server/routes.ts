import type { Express } from "express";
import { createServer, type Server } from "http";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.post("/api/generate", (req, res) => {
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
        try {
          fs.unlinkSync(outputPath);
        } catch (_) {/* ignore cleanup errors */}
      });

      fileStream.on("error", (err) => {
        console.error("File stream error:", err);
      });
    });
  });

  return httpServer;
}

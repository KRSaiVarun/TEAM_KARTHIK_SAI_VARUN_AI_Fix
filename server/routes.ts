import { api } from "@shared/routes";
import { spawn } from "child_process";
import type { Express } from "express";
import { type Server } from "http";
import path from "path";
import { z } from "zod";
import { storage } from "./storage";

/**
 * Generate branch name using format: TEAM_NAME_LEADER_NAME_AI_Fix
 */
function generateBranchName(teamName: string, leaderName: string): string {
  const cleanTeam = teamName
    .toUpperCase()
    .replace(/\s+/g, "_")
    .replace(/[^A-Z0-9_]/g, "");

  const cleanLeader = leaderName
    .toUpperCase()
    .replace(/\s+/g, "_")
    .replace(/[^A-Z0-9_]/g, "");

  return `${cleanTeam}_${cleanLeader}_AI_Fix`;
}

export async function registerRoutes(
  httpServer: Server,
  app: Express,
): Promise<Server> {
  app.post(api.projects.create.path, async (req, res) => {
    try {
      const input = api.projects.create.input.parse(req.body);

      // Generate branch name with EXACT format
      const branchName = generateBranchName(input.teamName, input.leaderName);

      const project = await storage.createProject({
        ...input,
        branchName,
      });

      // Initialize timeline with first entry
      await storage.addTimelineEntry(project.id, {
        id: `run-${Date.now()}`,
        timestamp: new Date().toISOString(),
        attempt: 1,
        status: "pending",
      });

      // Trigger Python agent in background with environment variables
      const pythonProcess = spawn(
        "python",
        [
          path.join(process.cwd(), "backend", "agent.py"),
          project.id.toString(),
          project.repoUrl,
          project.teamName,
          project.leaderName,
          branchName,
        ],
        {
          env: {
            ...process.env,
            DATABASE_URL:
              process.env.DATABASE_URL ||
              "postgresql://devuser:devpassword@127.0.0.1:15432/devdb",
            MAX_RETRIES: "5",
          },
        },
      );

      pythonProcess.stdout.on("data", (data) => {
        console.log(`Agent stdout: ${data}`);
      });

      pythonProcess.stderr.on("data", (data) => {
        console.error(`Agent stderr: ${data}`);
      });

      pythonProcess.on("close", (code) => {
        console.log(`Agent process exited with code ${code}`);
      });

      res.status(201).json(project);
    } catch (err) {
      console.error("POST /api/projects error:", err);
      if (err instanceof z.ZodError) {
        res.status(400).json({
          message: err.errors[0].message,
          field: err.errors[0].path.join("."),
        });
      } else {
        res
          .status(500)
          .json({ message: "Internal Server Error", error: String(err) });
      }
    }
  });

  app.get(api.projects.list.path, async (req, res) => {
    const projects = await storage.listProjects();
    res.json(projects);
  });

  app.get(api.projects.get.path, async (req, res) => {
    const project = await storage.getProject(Number(req.params.id));
    if (!project) {
      return res.status(404).json({ message: "Project not found" });
    }
    res.json(project);
  });

  app.get(api.projects.getBugs.path, async (req, res) => {
    const bugs = await storage.getBugsByProject(Number(req.params.id));
    res.json(bugs);
  });

  return httpServer;
}

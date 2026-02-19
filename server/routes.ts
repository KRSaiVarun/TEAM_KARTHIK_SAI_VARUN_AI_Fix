import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { api } from "@shared/routes";
import { z } from "zod";
import { spawn } from "child_process";
import path from "path";

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  app.post(api.projects.create.path, async (req, res) => {
    try {
      const input = api.projects.create.input.parse(req.body);
      const project = await storage.createProject(input);

      // Trigger Python agent in background
      const pythonProcess = spawn("python3", [
        path.join(process.cwd(), "backend", "agent.py"),
        project.id.toString(),
        project.repoUrl,
        project.teamName,
        project.leaderName
      ]);

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
      if (err instanceof z.ZodError) {
        res.status(400).json({
          message: err.errors[0].message,
          field: err.errors[0].path.join('.'),
        });
      } else {
        res.status(500).json({ message: "Internal Server Error" });
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

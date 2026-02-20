import { ExternalLink, Loader } from "lucide-react";
import React, { useCallback, useEffect, useState } from "react";
import { useLocation } from "wouter";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";

interface Project {
  id: number;
  repoUrl: string;
  teamName: string;
  leaderName: string;
  branchName: string | null;
  createdAt: string;
  status: "pending" | "running" | "completed" | "failed";
  summary: {
    totalFiles?: number;
    totalErrors?: number;
    fixedErrors?: number;
    tests?: {
      status: string;
      rounds: number;
      stdout: string;
      stderr: string;
    };
  } | null;
}

export function AnalysisDashboard() {
  const [, setLocation] = useLocation();
  const [projects, setProjects] = useState<Project[]>([]);
  const [repoUrl, setRepoUrl] = useState("");
  const [teamName, setTeamName] = useState("");
  const [leaderName, setLeaderName] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Fetch projects list
  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/projects");
      if (response.ok) {
        const data = await response.json();
        setProjects(data);
      }
    } catch (error) {
      console.error("Failed to fetch projects:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load and polling
  useEffect(() => {
    fetchProjects();
    const interval = setInterval(fetchProjects, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [fetchProjects]);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl || !teamName || !leaderName) {
      alert("Please fill in all fields");
      return;
    }

    try {
      setSubmitting(true);
      const response = await fetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repoUrl, teamName, leaderName }),
      });

      if (response.ok) {
        const newProject = await response.json();
        setRepoUrl("");
        setTeamName("");
        setLeaderName("");
        await fetchProjects();
        // Navigate to project details page
        setLocation(`/project/${newProject.id}`);
      } else {
        const error = await response.json();
        alert(`Failed to create project: ${error.message}`);
      }
    } catch (error) {
      console.error("Failed to create project:", error);
      alert("Failed to create project");
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "success";
      case "running":
        return "warning";
      case "failed":
        return "destructive";
      default:
        return "secondary";
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">AI Code Analysis Agent</h1>
        <p className="text-muted-foreground">
          Automatically analyze GitHub repositories, run tests, and apply fixes
        </p>
      </div>

      {/* Input Form */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">New Analysis</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                GitHub Repository URL
              </label>
              <Input
                type="url"
                placeholder="https://github.com/user/repo.git"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Team Name</label>
              <Input
                type="text"
                placeholder="Team A"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Leader Name</label>
              <Input
                type="text"
                placeholder="Alice"
                value={leaderName}
                onChange={(e) => setLeaderName(e.target.value)}
                disabled={submitting}
              />
            </div>
          </div>
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? (
              <>
                <Loader className="mr-2 h-4 w-4 animate-spin" />
                Running Analysis...
              </>
            ) : (
              "Run Analysis"
            )}
          </Button>
        </form>
      </Card>

      {/* Projects List */}
      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Analyses</h2>
        {loading && projects.length === 0 ? (
          <div className="flex justify-center py-8">
            <Loader className="h-6 w-6 animate-spin" />
          </div>
        ) : projects.length === 0 ? (
          <p className="text-muted-foreground">
            No analyses yet. Create one above!
          </p>
        ) : (
          <div className="space-y-3">
            {projects.map((project) => (
              <div
                key={project.id}
                className="p-4 border rounded-lg hover:bg-accent transition flex items-start justify-between"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold">{project.repoUrl}</h3>
                    <Badge variant={getStatusColor(project.status) as any}>
                      {project.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Team: {project.teamName} | Leader: {project.leaderName}
                  </p>
                  {project.summary && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Files: {project.summary.totalFiles} | Errors:{" "}
                      {project.summary.totalErrors} | Fixed:{" "}
                      {project.summary.fixedErrors}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {project.status === "running" && (
                    <Loader className="h-5 w-5 animate-spin text-blue-500" />
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setLocation(`/project/${project.id}`)}
                    className="gap-2"
                  >
                    <ExternalLink className="h-4 w-4" />
                    View Analysis
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

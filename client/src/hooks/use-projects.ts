import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, buildUrl } from "@shared/routes";
import { useToast } from "@/hooks/use-toast";
import { z } from "zod";

// Helper types derived from Zod schemas
type Project = z.infer<typeof api.projects.list.responses[200]>[number];
type CreateProjectInput = z.infer<typeof api.projects.create.input>;
type Bug = z.infer<typeof api.projects.getBugs.responses[200]>[number];

export function useProjects() {
  return useQuery({
    queryKey: [api.projects.list.path],
    queryFn: async () => {
      const res = await fetch(api.projects.list.path);
      if (!res.ok) throw new Error("Failed to fetch projects");
      return api.projects.list.responses[200].parse(await res.json());
    },
  });
}

export function useProject(id: number) {
  return useQuery({
    queryKey: [api.projects.get.path, id],
    queryFn: async () => {
      const url = buildUrl(api.projects.get.path, { id });
      const res = await fetch(url);
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch project");
      return api.projects.get.responses[200].parse(await res.json());
    },
    // Poll every 3 seconds if status is running or pending
    refetchInterval: (data) => 
      data?.status === 'running' || data?.status === 'pending' ? 3000 : false,
  });
}

export function useProjectBugs(projectId: number) {
  return useQuery({
    queryKey: [api.projects.getBugs.path, projectId],
    queryFn: async () => {
      const url = buildUrl(api.projects.getBugs.path, { id: projectId });
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch bugs");
      return api.projects.getBugs.responses[200].parse(await res.json());
    },
    // Poll frequently if parent project is running
    refetchInterval: 3000, 
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: async (data: CreateProjectInput) => {
      const res = await fetch(api.projects.create.path, {
        method: api.projects.create.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      
      if (!res.ok) {
        if (res.status === 400) {
          const error = await res.json();
          throw new Error(error.message || "Validation failed");
        }
        throw new Error("Failed to create project analysis");
      }
      
      return api.projects.create.responses[201].parse(await res.json());
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: [api.projects.list.path] });
      toast({
        title: "Analysis Started",
        description: `Started analyzing ${data.repoUrl}`,
      });
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    },
  });
}

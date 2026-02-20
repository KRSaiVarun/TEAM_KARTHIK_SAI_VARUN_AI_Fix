import {
    bugs,
    projects,
    users,
    type Bug,
    type InsertProject,
    type InsertUser,
    type Project,
    type User,
} from "@shared/schema";
import { eq } from "drizzle-orm";
import { db } from "./db";

export interface TimelineEntry {
  id: string;
  timestamp: string;
  attempt: number;
  status: "pending" | "running" | "success" | "failed";
  duration?: number;
  error?: string;
}

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  createProject(
    project: InsertProject & { branchName?: string },
  ): Promise<Project>;
  getProject(id: number): Promise<Project | undefined>;
  listProjects(): Promise<Project[]>;
  updateProjectStatus(
    id: number,
    status: string,
    summary?: any,
  ): Promise<Project>;
  addTimelineEntry(projectId: number, entry: TimelineEntry): Promise<void>;
  updateTimelineEntry(
    projectId: number,
    entryId: string,
    updates: Partial<TimelineEntry>,
  ): Promise<void>;
  createBug(bug: any): Promise<Bug>;
  getBugsByProject(projectId: number): Promise<Bug[]>;
}

export class DatabaseStorage implements IStorage {
  async getUser(id: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db
      .select()
      .from(users)
      .where(eq(users.username, username));
    return user || undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db.insert(users).values(insertUser).returning();
    return user;
  }

  async createProject(
    insertProject: InsertProject & { branchName?: string },
  ): Promise<Project> {
    const [project] = await db
      .insert(projects)
      .values(insertProject)
      .returning();
    return project;
  }

  async getProject(id: number): Promise<Project | undefined> {
    const [project] = await db
      .select()
      .from(projects)
      .where(eq(projects.id, id));
    return project || undefined;
  }

  async listProjects(): Promise<Project[]> {
    return await db.select().from(projects).orderBy(projects.createdAt);
  }

  async updateProjectStatus(
    id: number,
    status: string,
    summary?: any,
  ): Promise<Project> {
    const [project] = await db
      .update(projects)
      .set({ status, summary })
      .where(eq(projects.id, id))
      .returning();
    return project;
  }

  async addTimelineEntry(
    projectId: number,
    entry: TimelineEntry,
  ): Promise<void> {
    const project = await this.getProject(projectId);
    if (!project) throw new Error(`Project ${projectId} not found`);

    const timeline = (project.timeline as TimelineEntry[]) || [];
    timeline.push(entry);

    await db
      .update(projects)
      .set({ timeline })
      .where(eq(projects.id, projectId));
  }

  async updateTimelineEntry(
    projectId: number,
    entryId: string,
    updates: Partial<TimelineEntry>,
  ): Promise<void> {
    const project = await this.getProject(projectId);
    if (!project) throw new Error(`Project ${projectId} not found`);

    const timeline = (project.timeline as TimelineEntry[]) || [];
    const entryIndex = timeline.findIndex((e) => e.id === entryId);
    if (entryIndex === -1)
      throw new Error(`Timeline entry ${entryId} not found`);

    timeline[entryIndex] = { ...timeline[entryIndex], ...updates };

    await db
      .update(projects)
      .set({ timeline })
      .where(eq(projects.id, projectId));
  }

  async createBug(bug: any): Promise<Bug> {
    const [newBug] = await db.insert(bugs).values(bug).returning();
    return newBug;
  }

  async getBugsByProject(projectId: number): Promise<Bug[]> {
    return await db.select().from(bugs).where(eq(bugs.projectId, projectId));
  }
}

export const storage = new DatabaseStorage();

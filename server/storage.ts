import { users, projects, bugs, type User, type InsertUser, type Project, type InsertProject, type Bug } from "@shared/schema";
import { db } from "./db";
import { eq } from "drizzle-orm";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;

  createProject(project: InsertProject): Promise<Project>;
  getProject(id: number): Promise<Project | undefined>;
  listProjects(): Promise<Project[]>;
  updateProjectStatus(id: number, status: string, summary?: any): Promise<Project>;
  createBug(bug: any): Promise<Bug>;
  getBugsByProject(projectId: number): Promise<Bug[]>;
}

export class DatabaseStorage implements IStorage {
  async getUser(id: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.id, id));
    return user || undefined;
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    const [user] = await db.select().from(users).where(eq(users.username, username));
    return user || undefined;
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const [user] = await db.insert(users).values(insertUser).returning();
    return user;
  }

  async createProject(insertProject: InsertProject): Promise<Project> {
    const [project] = await db.insert(projects).values(insertProject).returning();
    return project;
  }

  async getProject(id: number): Promise<Project | undefined> {
    const [project] = await db.select().from(projects).where(eq(projects.id, id));
    return project || undefined;
  }

  async listProjects(): Promise<Project[]> {
    return await db.select().from(projects).orderBy(projects.createdAt);
  }

  async updateProjectStatus(id: number, status: string, summary?: any): Promise<Project> {
    const [project] = await db
      .update(projects)
      .set({ status, summary })
      .where(eq(projects.id, id))
      .returning();
    return project;
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

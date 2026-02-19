import { pgTable, text, serial, integer, boolean, timestamp, jsonb, varchar } from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;

export const projects = pgTable("projects", {
  id: serial("id").primaryKey(),
  repoUrl: text("repo_url").notNull(),
  teamName: text("team_name").notNull(),
  leaderName: text("leader_name").notNull(),
  branchName: text("branch_name"),
  createdAt: timestamp("created_at").defaultNow(),
  status: text("status").default("pending"), // pending, running, completed, failed
  summary: jsonb("summary").$type<{
    totalFiles: number;
    totalErrors: number;
    fixedErrors: number;
  }>(),
});

export const bugs = pgTable("bugs", {
  id: serial("id").primaryKey(),
  projectId: integer("project_id").notNull(),
  filePath: text("file_path").notNull(),
  bugType: text("bug_type").notNull(), // LINTING, SYNTAX, IMPORT, INDENTATION, LOGIC
  lineNumber: integer("line_number"),
  errorMessage: text("error_message"),
  fixApplied: text("fix_applied"),
  status: text("status").default("pending"), // pending, fixed, failed
  createdAt: timestamp("created_at").defaultNow(),
});

export const insertProjectSchema = createInsertSchema(projects).omit({ 
  id: true, 
  createdAt: true, 
  branchName: true,
  status: true,
  summary: true 
});

export type Project = typeof projects.$inferSelect;
export type InsertProject = z.infer<typeof insertProjectSchema>;
export type Bug = typeof bugs.$inferSelect;

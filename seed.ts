/**
 * SEED DATA SCRIPT - FOR TESTING/DEMO PURPOSES ONLY
 *
 * ⚠️ This script creates test data for development/demo.
 *
 * 📋 REAL WORKFLOW (How users interact with the app):
 * 1. User visits http://localhost:5000 (Dashboard)
 * 2. User fills out the form:
 *    - Repository URL: https://github.com/user/repo
 *    - Team Name: My Team
 *    - Leader Name: Alice Johnson
 * 3. User clicks "Run Analysis" button
 * 4. Project is created in database with user's actual data
 * 5. User is redirected to Project Details page
 * 6. Page displays: "My Team / Alice Johnson" + repo URL
 * 7. Analysis runs in background, bugs are detected and fixed
 * 8. Score Breakdown Panel & Fixes Table are populated with real results
 *
 * 🧪 THIS SEED SCRIPT:
 * Creates a sample completed project with demo bugs for testing
 * the Score Breakdown Panel and Fixes Applied Table components.
 *
 * Usage: npm run seed (requires DATABASE_URL environment variable)
 */

import "dotenv/config";
import { db } from "./server/db";
import { bugs, projects } from "./shared/schema";

async function seedData() {
  try {
    // Create a completed project
    const project = await db
      .insert(projects)
      .values({
        repoUrl: "https://github.com/example/sample-repo",
        teamName: "Demo Team",
        leaderName: "John Doe",
        branchName: "fix/auto-fixes-001",
        status: "completed",
        commitCount: 25,
        createdAt: new Date(Date.now() - 5 * 60 * 1000), // 5 minutes ago
        completedAt: new Date(Date.now() - 2 * 60 * 1000), // 2 minutes ago
        summary: {
          totalFiles: 15,
          totalErrors: 8,
          fixedErrors: 6,
        },
      })
      .returning();

    console.log("✅ Created project:", project);

    // Create sample bugs
    const sampleBugs = [
      {
        projectId: project[0].id,
        filePath: "src/components/Button.tsx",
        bugType: "LINTING",
        lineNumber: 42,
        errorMessage: "Missing semicolon at end of statement",
        fixApplied: "Add missing semicolon",
        status: "fixed",
      },
      {
        projectId: project[0].id,
        filePath: "src/utils/helpers.ts",
        bugType: "SYNTAX",
        lineNumber: 18,
        errorMessage: "Unexpected token 'const'",
        fixApplied: "Fix syntax error in variable declaration",
        status: "fixed",
      },
      {
        projectId: project[0].id,
        filePath: "src/api/users.ts",
        bugType: "TYPE_ERROR",
        lineNumber: 56,
        errorMessage: "Parameter type mismatch: expected string, got number",
        fixApplied: "Add type conversion",
        status: "fixed",
      },
      {
        projectId: project[0].id,
        filePath: "src/pages/Dashboard.tsx",
        bugType: "IMPORT",
        lineNumber: 3,
        errorMessage: "Cannot find module '@/utils/unknown'",
        fixApplied: "Fix import path to correct module",
        status: "fixed",
      },
      {
        projectId: project[0].id,
        filePath: "src/styles/global.css",
        bugType: "INDENTATION",
        lineNumber: 24,
        errorMessage: "Inconsistent indentation",
        fixApplied: "Normalize indentation to 2 spaces",
        status: "fixed",
      },
      {
        projectId: project[0].id,
        filePath: "src/logic/calculator.ts",
        bugType: "LOGIC",
        lineNumber: 78,
        errorMessage: "Logic error: condition always evaluates to true",
        fixApplied: "Fix logic condition",
        status: "fixed",
      },
      {
        projectId: project[0].id,
        filePath: "src/components/Modal.tsx",
        bugType: "LINTING",
        lineNumber: 91,
        errorMessage: "Variable declared but never used",
        fixApplied: "Remove unused variable",
        status: "failed",
      },
      {
        projectId: project[0].id,
        filePath: "src/hooks/useData.ts",
        bugType: "SYNTAX",
        lineNumber: 12,
        errorMessage: "Missing closing brace",
        fixApplied: "Add missing closing brace",
        status: "pending",
      },
    ];

    const insertedBugs = await db.insert(bugs).values(sampleBugs).returning();

    console.log("\n" + "=".repeat(60));
    console.log("✅ Demo project created successfully!");
    console.log("=".repeat(60));
    console.log(`\nProject ID: ${project[0].id}`);
    console.log(`Team: ${project[0].teamName} / ${project[0].leaderName}`);
    console.log(`Repo: ${project[0].repoUrl}`);
    console.log(`Bugs Created: ${insertedBugs.length}`);
    console.log(
      `\n📍 View Demo: http://localhost:5000/project/${project[0].id}`,
    );
    console.log("\n" + "=".repeat(60));
    console.log("💡 FOR REAL WORLD USAGE:");
    console.log("=".repeat(60));
    console.log("1. Go to http://localhost:5000");
    console.log("2. Enter your GitHub repo URL");
    console.log("3. Enter your Team Name");
    console.log("4. Enter Leader Name");
    console.log("5. Click 'Run Analysis'");
    console.log("6. Project Details will show YOUR data, not demo data!");
    console.log("=".repeat(60) + "\n");
  } catch (error) {
    console.error("❌ Error seeding data:", error);
    process.exit(1);
  }
}

seedData();

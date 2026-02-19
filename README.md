# Code Fix Agent

A full-stack application that analyzes GitHub repositories, detects bugs (Linting, Syntax, Logic), and applies automated fixes using a Python-based agent.

## Features

- **Project Dashboard**: Submit repos and view analysis status.
- **Automated Analysis**: Clones repo, scans files, detects issues.
- **Rule-Based Fixes**: Automatically applies fixes for common issues.
- **Bug Reporting**: Detailed view of found bugs and applied fixes.
- **CI Integration**: (Simulated) Tracks "CI status" and commits fixes to a new branch.

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Shadcn UI
- **Backend**: Node.js (Express) + Python (Agent)
- **Database**: PostgreSQL
- **ORM**: Drizzle

## Setup Instructions

1.  **Install Dependencies**:

    ```bash
    npm install
    ```

    Python dependencies are installed via `nix` or `pip`:

    ```bash
    pip install fastapi uvicorn pydantic gitpython pytest psycopg2-binary
    ```

2.  **Database Setup**:
    Ensure PostgreSQL is running and `DATABASE_URL` is set.

    ```bash
    npm run db:push
    ```

3.  **Run Application**:

    ```bash
    npm run dev
    ```

    This starts the Node.js server (port 5000) and the React frontend.

4.  **(Optional) Seed Demo Data**:
    ```bash
    npm run seed
    ```
    Creates a demo project for testing the Score Breakdown Panel and Fixes Table.

## Quick Start - Using the Dashboard

1. **Open Dashboard**: http://localhost:5000
2. **Fill Out Form**:
   - GitHub Repository URL: `https://github.com/user/repo`
   - Team Name: `My Team`
   - Leader Name: `Alice Johnson`
3. **Click "Run Analysis"** - Analysis starts in background
4. **View Results**: Click on project to see Project Details page
5. **Check Status**:
   - Shows: `PENDING` → `RUNNING` → `COMPLETED`
   - Displays your team name and leader name
   - Real-time logs of what the agent is doing

## Important Notes

✅ **Your Data is Displayed**: Whatever you enter in the form (Team Name, Leader Name) will show on the Project Details page, not demo data!

✅ **Demo Project**: ID 3 is a demo project created by `npm run seed` for testing

✅ **Real Projects**: Any project you create via the dashboard form will show YOUR submitted data

## API Endpoints

- `POST /api/projects`: Submit a new project for analysis.
- `GET /api/projects`: List all projects.
- `GET /api/projects/:id`: Get project details.
- `GET /api/projects/:id/bugs`: Get bugs for a project.

## Project Structure

- `client/`: React frontend code.
- `server/`: Node.js API server.
- `backend/`: Python agent script (`agent.py`).
- `shared/`: Shared TypeScript types and schemas.

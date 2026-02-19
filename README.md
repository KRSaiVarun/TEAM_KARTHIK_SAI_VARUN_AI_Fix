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

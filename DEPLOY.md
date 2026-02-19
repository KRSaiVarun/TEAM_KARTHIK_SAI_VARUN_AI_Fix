# Deployment Instructions

## Rapid Deployment on Replit

1.  **Database**: Ensure a PostgreSQL database is provisioned in the Replit environment.
2.  **Environment Variables**: Check that `DATABASE_URL` is set in the Secrets/Environment variables.
3.  **Build**: The application uses Vite for the frontend.
    ```bash
    npm run build
    ```
4.  **Start**:
    ```bash
    npm start
    ```
    This runs `node dist/index.cjs` which serves the API and the static frontend files.

## Python Environment

The Python environment is managed by `nix` (replit.nix) or `pip`. Ensure `backend/agent.py` has access to the installed Python packages (`psycopg2-binary`, `gitpython`, etc.).
On Replit, this is handled automatically if the packages are added to the configuration.

## Docker (Optional)

If deploying elsewhere, use a multi-stage Dockerfile:
1.  Build frontend with Node.js.
2.  Setup Python environment.
3.  Copy built frontend and server code.
4.  Run the Node.js server.

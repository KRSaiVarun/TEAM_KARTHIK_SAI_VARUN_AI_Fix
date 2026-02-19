import os
import sys
import subprocess
import psycopg2
import shutil
import time
import json
import re
from urllib.parse import urlparse

# Get DB connection
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def run_command(command, cwd=None):
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            shell=True
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def clone_repo(repo_url, target_dir):
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)
    
    print(f"Cloning {repo_url} to {target_dir}...")
    # Using git command line for simplicity
    stdout, stderr, code = run_command(f"git clone {repo_url} .", cwd=target_dir)
    if code != 0:
        raise Exception(f"Failed to clone repo: {stderr}")
    return True

def analyze_file(file_path):
    issues = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Simple rule-based analysis
    for i, line in enumerate(lines):
        # 1. Check for missing semicolons in JS (very naive)
        if file_path.endswith('.js') or file_path.endswith('.ts'):
            if not line.strip().endswith(';') and not line.strip().endswith('{') and not line.strip().endswith('}') and len(line.strip()) > 0:
                issues.append({
                    "type": "LINTING",
                    "line": i + 1,
                    "message": "Missing semicolon",
                    "fix": line.rstrip() + ";"
                })
        
        # 2. Check for TODOs
        if "TODO" in line:
            issues.append({
                "type": "LOGIC",
                "line": i + 1,
                "message": "Found TODO comment",
                "fix": None
            })
            
        # 3. Check for print statements in production code (Python)
        if file_path.endswith('.py') and "print(" in line:
            issues.append({
                "type": "LINTING",
                "line": i + 1,
                "message": "Avoid print() in production, use logging",
                "fix": line.replace("print(", "logger.info(")
            })

    return issues

def apply_fix(file_path, line_number, fix_content):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # Line number is 1-based
    if 0 <= line_number - 1 < len(lines):
        lines[line_number - 1] = fix_content + "\n"
        
    with open(file_path, 'w') as f:
        f.writelines(lines)
    return True

def main():
    if len(sys.argv) < 5:
        print("Usage: python agent.py <project_id> <repo_url> <team_name> <leader_name>")
        sys.exit(1)

    project_id = sys.argv[1]
    repo_url = sys.argv[2]
    team_name = sys.argv[3]
    leader_name = sys.argv[4]

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Update status to running
        cur.execute("UPDATE projects SET status = 'running' WHERE id = %s", (project_id,))
        conn.commit()

        # Create workspace
        workspace_dir = os.path.join(os.getcwd(), "workspace", f"project_{project_id}")
        clone_repo(repo_url, workspace_dir)

        # Analyze files
        total_files = 0
        total_errors = 0
        fixed_errors = 0

        for root, dirs, files in os.walk(workspace_dir):
            if ".git" in dirs:
                dirs.remove(".git")
            
            for file in files:
                if file.endswith(('.js', '.ts', '.py', '.jsx', '.tsx')):
                    total_files += 1
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, workspace_dir)
                    
                    issues = analyze_file(file_path)
                    
                    for issue in issues:
                        total_errors += 1
                        fix_applied = None
                        
                        if issue["fix"]:
                            # Apply fix
                            apply_fix(file_path, issue["line"], issue["fix"])
                            fix_applied = issue["fix"]
                            fixed_errors += 1
                        
                        # Record bug in DB
                        cur.execute(
                            """
                            INSERT INTO bugs (project_id, file_path, bug_type, line_number, error_message, fix_applied, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (project_id, rel_path, issue["type"], issue["line"], issue["message"], fix_applied, "fixed" if fix_applied else "pending")
                        )
        
        conn.commit()

        # Commit changes if any fixes were applied
        if fixed_errors > 0:
            branch_name = f"fix/{team_name}_{leader_name}_AI_Fix"
            run_command(f"git checkout -b {branch_name}", cwd=workspace_dir)
            run_command("git config user.name 'AI Agent'", cwd=workspace_dir)
            run_command("git config user.email 'agent@replit.com'", cwd=workspace_dir)
            run_command("git add .", cwd=workspace_dir)
            run_command("git commit -m '[AI-AGENT] Applied automated fixes'", cwd=workspace_dir)
            # In a real scenario, we would push: run_command(f"git push origin {branch_name}", cwd=workspace_dir)
            
            # Update project with branch name
            cur.execute("UPDATE projects SET branch_name = %s WHERE id = %s", (branch_name, project_id))

        # Update summary
        summary = json.dumps({
            "totalFiles": total_files,
            "totalErrors": total_errors,
            "fixedErrors": fixed_errors
        })
        
        cur.execute("UPDATE projects SET status = 'completed', summary = %s WHERE id = %s", (summary, project_id))
        conn.commit()
        print(f"Analysis completed for project {project_id}")

    except Exception as e:
        print(f"Error: {e}")
        cur.execute("UPDATE projects SET status = 'failed' WHERE id = %s", (project_id,))
        conn.commit()
    finally:
        cur.close()
        conn.close()
        # Cleanup
        # shutil.rmtree(workspace_dir) # Keep it for debugging in this demo

if __name__ == "__main__":
    main()

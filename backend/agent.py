import os
import sys
import subprocess
import psycopg2
import psycopg2.extras as extras
import shutil
import time
import json
import re
import tempfile
import traceback
from urllib.parse import urlparse
from urllib.request import urlopen
import zipfile

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


def run_tests(cwd, timeout=30):
    """Detect and run tests in the repository. Returns (stdout, stderr, returncode).

    Args:
        cwd: Working directory for tests
        timeout: Max seconds to wait for test execution (default 30s)
    """
    import threading

    result_container = {"stdout": "", "stderr": "", "returncode": 1}
    error_container = {"error": None}

    def run_with_timeout():
        try:
            # Prefer npm/yarn/pnpm if package.json contains a test script
            pkg = os.path.join(cwd, "package.json")
            if os.path.exists(pkg):
                try:
                    # Use npm test with timeout
                    result = subprocess.run(
                        "npm test --silent --timeout=10000",
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    result_container["stdout"] = result.stdout
                    result_container["stderr"] = result.stderr
                    result_container["returncode"] = result.returncode
                    return
                except subprocess.TimeoutExpired:
                    result_container["stdout"] = ""
                    result_container["stderr"] = f"npm test timed out after {timeout} seconds"
                    result_container["returncode"] = 124  # timeout exit code
                    return
                except Exception as e:
                    error_container["error"] = str(e)
                    pass

            # Fallback to pytest if available
            try:
                if any(f.endswith(".py") for f in os.listdir(cwd)):
                    result = subprocess.run(
                        "pytest -q",
                        cwd=cwd,
                        capture_output=True,
                        text=True,
                        timeout=timeout
                    )
                    result_container["stdout"] = result.stdout
                    result_container["stderr"] = result.stderr
                    result_container["returncode"] = result.returncode
                    return
            except subprocess.TimeoutExpired:
                result_container["stdout"] = ""
                result_container["stderr"] = f"pytest timed out after {timeout} seconds"
                result_container["returncode"] = 124
                return
            except Exception as e:
                error_container["error"] = str(e)
                pass

            # No test runner detected
            result_container["stdout"] = ""
            result_container["stderr"] = "No test runner detected"
            result_container["returncode"] = 0
        except Exception as e:
            error_container["error"] = str(e)
            result_container["stderr"] = str(e)
            result_container["returncode"] = 1

    # Run in thread with timeout
    thread = threading.Thread(target=run_with_timeout)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout + 5)  # Give 5 extra seconds for cleanup

    if error_container["error"]:
        print(f"Test execution error: {error_container['error']}")

    return result_container["stdout"], result_container["stderr"], result_container["returncode"]

def clone_repo(repo_url, target_dir):
    """
    Download and extract a GitHub repository as ZIP.
    Supports URLs like:
    - https://github.com/octocat/Hello-World.git
    - https://github.com/octocat/Hello-World
    - https://github.com/pradhu3008-max/8-errors?tab=readme-ov-file#8-errors
    """
    # Ensure target parent exists
    parent = os.path.dirname(target_dir)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)

    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)

    try:
        # Parse the GitHub URL to extract owner and repo
        # Handle various URL formats
        url_clean = repo_url.split('?')[0].split('#')[0]  # Remove query params and fragments
        url_clean = url_clean.rstrip('/')

        if url_clean.endswith('.git'):
            url_clean = url_clean[:-4]

        # Extract owner and repo from URL: https://github.com/owner/repo
        parts = url_clean.split('/')
        if len(parts) < 2:
            raise Exception(f"Invalid GitHub URL format: {repo_url}")

        owner = parts[-2]
        repo = parts[-1]

        # Build download URL for main branch ZIP
        download_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip"
        print(f"Downloading {download_url}...")

        # Download ZIP
        zip_path = os.path.join(parent, f"{repo}.zip")
        try:
            with urlopen(download_url) as response:
                with open(zip_path, 'wb') as out_file:
                    out_file.write(response.read())
        except Exception:
            # Try master branch if main doesn't exist
            download_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
            print(f"Main branch not found, trying {download_url}...")
            with urlopen(download_url) as response:
                with open(zip_path, 'wb') as out_file:
                    out_file.write(response.read())

        # Extract ZIP
        print(f"Extracting to {target_dir}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(parent)

        # The extracted folder has a name like 'repo-main' or 'repo-master'
        # Find it and move to target_dir
        extracted_dirs = [d for d in os.listdir(parent)
                         if os.path.isdir(os.path.join(parent, d)) and d.startswith(repo)]

        if extracted_dirs:
            extracted_path = os.path.join(parent, extracted_dirs[0])
            shutil.move(extracted_path, target_dir)

        # Clean up ZIP
        os.remove(zip_path)

        print(f"Successfully cloned {repo_url}")
        return True

    except Exception as e:
        raise Exception(f"Failed to clone repo: {str(e)}")

def analyze_file(file_path):
    issues = []
    # Read files as UTF-8 to avoid platform-specific decoding errors
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
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
    # Read/write using UTF-8 to avoid charmap decoding issues
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    # Line number is 1-based
    if 0 <= line_number - 1 < len(lines):
        lines[line_number - 1] = fix_content + "\n"

    with open(file_path, 'w', encoding='utf-8') as f:
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
    print("Connected to database via DATABASE_URL")

    try:
        # Update status to running
        cur.execute("UPDATE projects SET status = 'running' WHERE id = %s", (project_id,))
        conn.commit()

        # Create workspace — use system temp directory to avoid OneDrive permission issues
        workspace_base = os.path.join(tempfile.gettempdir(), "code_fix_agent_workspace")
        os.makedirs(workspace_base, exist_ok=True)
        workspace_dir = os.path.join(workspace_base, f"project_{project_id}")
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

                        # Record bug in DB (commit after insert for durability)
                        try:
                            cur.execute(
                                """
                                INSERT INTO bugs (project_id, file_path, bug_type, line_number, error_message, fix_applied, status)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                RETURNING id
                                """,
                                (project_id, rel_path, issue["type"], issue["line"], issue["message"], fix_applied, "fixed" if fix_applied else "pending")
                            )
                            bug_id = cur.fetchone()[0]
                            conn.commit()
                            print(f"Inserted bug id={bug_id} project={project_id} file={rel_path} fix_applied={bool(fix_applied)}")
                        except Exception as e:
                            print(f"Failed to insert bug for project {project_id} file {rel_path}: {e}")
                            traceback.print_exc()
                            try:
                                conn.rollback()
                            except Exception:
                                pass

        conn.commit()
        # Now run tests and attempt iterative fixes
        test_stdout = ""
        test_stderr = ""
        test_code = 0

        # Respect MAX_RETRIES environment variable (default 5)
        try:
            max_rounds = int(os.environ.get("MAX_RETRIES", "5"))
        except Exception:
            max_rounds = 5
        round_no = 0
        pushed_branch = None
        def add_timeline_entry(pid, entry):
            try:
                cur.execute("SELECT timeline FROM projects WHERE id = %s", (pid,))
                row = cur.fetchone()
                current = row[0] if row and row[0] else []
                if not isinstance(current, list):
                    current = []
                current.append(entry)
                cur.execute("UPDATE projects SET timeline = %s WHERE id = %s", (extras.Json(current), pid))
                conn.commit()
            except Exception as e:
                print(f"Failed to append timeline entry for project {pid}: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass

        def update_last_timeline_entry(pid, attempt, updates):
            try:
                cur.execute("SELECT timeline FROM projects WHERE id = %s", (pid,))
                row = cur.fetchone()
                current = row[0] if row and row[0] else []
                if not isinstance(current, list):
                    current = []
                # find last entry with matching attempt
                for i in range(len(current)-1, -1, -1):
                    if current[i].get('attempt') == attempt:
                        current[i].update(updates)
                        break
                cur.execute("UPDATE projects SET timeline = %s WHERE id = %s", (extras.Json(current), pid))
                conn.commit()
            except Exception as e:
                print(f"Failed to update timeline entry for project {pid}: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass

        while round_no < max_rounds:
            round_no += 1
            print(f"Running tests (round {round_no})...")
            # Record timeline entry for this attempt
            started_at = int(time.time() * 1000)
            timeline_entry = {
                "attempt": round_no,
                "status": "running",
                "started_at": started_at,
                "message": "Tests running"
            }
            add_timeline_entry(project_id, timeline_entry)
            # Update retryCount in projects
            try:
                cur.execute("UPDATE projects SET retryCount = %s WHERE id = %s", (round_no, project_id))
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
            test_stdout, test_stderr, test_code = run_tests(workspace_dir)
            print("Test return code:", test_code)

            completed_at = int(time.time() * 1000)
            duration_ms = max(0, completed_at - started_at)

            if test_code == 0:
                # Tests passed: use Json wrapper for safe JSONB insertion
                summary_obj = {
                    "totalFiles": total_files,
                    "totalErrors": total_errors,
                    "fixedErrors": fixed_errors,
                    "tests": {
                        "status": "passed",
                        "rounds": round_no,
                        "stdout": test_stdout,
                        "stderr": test_stderr,
                    }
                }
                try:
                    cur.execute(
                        "UPDATE projects SET status = 'completed', summary = %s WHERE id = %s",
                        (extras.Json(summary_obj), project_id),
                    )
                    conn.commit()
                    print(f"Updated project {project_id} status=completed with summary (passed) rounds={round_no}")
                    # update timeline entry to passed
                    update_last_timeline_entry(project_id, round_no, {
                        "status": "passed",
                        "completed_at": completed_at,
                        "duration_ms": duration_ms
                    })
                except Exception as e:
                    print(f"Failed to update project summary for project {project_id}: {e}")
                    traceback.print_exc()
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                break

            # Tests failed: attempt another analysis pass and apply simple fixes
            print("Tests failed — attempting another analysis pass to auto-fix common issues...")
            # Re-scan files and apply any available simple fixes
            additional_fixes = 0
            for root, dirs, files in os.walk(workspace_dir):
                if ".git" in dirs:
                    dirs.remove(".git")
                for file in files:
                    if file.endswith(('.js', '.ts', '.py', '.jsx', '.tsx')):
                        file_path = os.path.join(root, file)
                        issues = analyze_file(file_path)
                        for issue in issues:
                            if issue.get("fix"):
                                apply_fix(file_path, issue["line"], issue["fix"])
                                additional_fixes += 1
                                fixed_errors += 1

            if additional_fixes > 0:
                # Commit and push this round
                branch_name = f"fix/{team_name}_{leader_name}_AI_Fix_r{round_no}"
                run_command(f"git checkout -b {branch_name}", cwd=workspace_dir)
                run_command("git config user.name \"AI Agent\"", cwd=workspace_dir)
                run_command("git config user.email \"agent@replit.com\"", cwd=workspace_dir)
                run_command("git add .", cwd=workspace_dir)
                run_command("git commit -m '[AI-AGENT] Applied automated fixes (round {0})'".format(round_no), cwd=workspace_dir)
                stdout_push, stderr_push, code_push = run_command(f"git push origin {branch_name}", cwd=workspace_dir)
                if code_push == 0:
                    pushed_branch = branch_name
                else:
                    print("Git push failed (likely auth); continuing without remote push")

                # Update branch name in DB (latest attempted)
                try:
                    cur.execute("UPDATE projects SET branch_name = %s WHERE id = %s", (branch_name, project_id))
                    conn.commit()
                    print(f"Updated project {project_id} branch_name={branch_name}")
                except Exception as e:
                    print(f"Failed to update branch_name for project {project_id}: {e}")
                    traceback.print_exc()
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                # update timeline entry for this attempt as failed (we'll continue loop)
                update_last_timeline_entry(project_id, round_no, {
                    "status": "failed",
                    "completed_at": int(time.time() * 1000),
                    "duration_ms": int(time.time() * 1000) - started_at,
                    "message": "Attempted fixes applied"
                })
            else:
                # No automatic fixes detected — stop trying
                print("No additional automatic fixes found; stopping iterations")
                update_last_timeline_entry(project_id, round_no, {
                    "status": "no_fixes",
                    "completed_at": int(time.time() * 1000),
                    "duration_ms": int(time.time() * 1000) - started_at,
                    "message": "No automatic fixes found"
                })
                break

        else:
            # Reached max rounds without passing tests
            summary_obj = {
                "totalFiles": total_files,
                "totalErrors": total_errors,
                "fixedErrors": fixed_errors,
                "tests": {
                    "status": "failed",
                    "rounds": round_no,
                    "stdout": test_stdout,
                    "stderr": test_stderr,
                }
            }
            try:
                cur.execute("UPDATE projects SET status = 'failed', summary = %s WHERE id = %s", (extras.Json(summary_obj), project_id))
                conn.commit()
                print(f"Tests did not pass after {max_rounds} rounds for project {project_id}")
            except Exception as e:
                print(f"Failed to update failed summary for project {project_id}: {e}")
                traceback.print_exc()
                try:
                    conn.rollback()
                except Exception:
                    pass

        # If tests passed in loop, we've already updated status. If not, ensure summary set.
        if test_code != 0 and round_no <= max_rounds:
            # Update summary for non-passing state if not already set
            try:
                if 'summary_obj' not in locals():
                    summary_obj = {
                        "totalFiles": total_files,
                        "totalErrors": total_errors,
                        "fixedErrors": fixed_errors,
                        "tests": {
                            "status": "failed",
                            "rounds": round_no,
                            "stdout": test_stdout,
                            "stderr": test_stderr,
                        }
                    }
                cur.execute("UPDATE projects SET summary = %s WHERE id = %s", (extras.Json(summary_obj), project_id))
                conn.commit()
                print(f"Updated project {project_id} summary after final round (not passing)")
                # mark last timeline entry as failed
                update_last_timeline_entry(project_id, round_no, {
                    "status": "failed",
                    "completed_at": int(time.time() * 1000),
                    "duration_ms": int(time.time() * 1000) - started_at,
                    "message": "Final state — tests did not pass"
                })
            except Exception as e:
                print(f"Failed to update summary after final round for project {project_id}: {e}")
                traceback.print_exc()
                try:
                    conn.rollback()
                except Exception:
                    pass

    except Exception as e:
        print(f"Error in main analysis: {e}")
        traceback.print_exc()
        # Always try to save summary with available data
        try:
            # Compile summary with whatever data we have
            summary_obj = {
                "totalFiles": total_files if 'total_files' in locals() else 0,
                "totalErrors": total_errors if 'total_errors' in locals() else 0,
                "fixedErrors": fixed_errors if 'fixed_errors' in locals() else 0,
                "error": str(e),
                "tests": {
                    "status": "error",
                    "rounds": round_no if 'round_no' in locals() else 0,
                    "stdout": test_stdout if 'test_stdout' in locals() else "",
                    "stderr": test_stderr if 'test_stderr' in locals() else str(e),
                }
            }
            cur.execute(
                "UPDATE projects SET status = 'failed', summary = %s WHERE id = %s",
                (extras.Json(summary_obj), project_id)
            )
            conn.commit()
            print(f"Updated project {project_id} with error summary")
        except Exception as inner_e:
            print(f"Failed to save error summary for project {project_id}: {inner_e}")
            # Last resort: just update status
            try:
                cur.execute("UPDATE projects SET status = 'failed' WHERE id = %s", (project_id,))
                conn.commit()
            except Exception:
                pass
    finally:
        cur.close()
        conn.close()
        # Cleanup: Remove temp directory after analysis completes
        try:
            if 'workspace_dir' in locals() and os.path.exists(workspace_dir):
                shutil.rmtree(workspace_dir)
                print(f"Cleaned up temp workspace: {workspace_dir}")
        except Exception as e:
            print(f"Warning: Failed to cleanup workspace: {e}")

if __name__ == "__main__":
    main()

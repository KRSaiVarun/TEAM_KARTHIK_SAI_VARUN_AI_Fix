import sys
import os
import re
import json
import shutil
import subprocess
import logging
import tempfile
import sqlite3
import hashlib
import time
import asyncio
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime, timezone
from weakref import WeakSet
import urllib.parse
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, validator, Field
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import redis
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Configuration Management
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Application settings with environment variable override."""
    # Database
    db_path: str = "agent_results.db"

    # Repository limits
    max_repo_size_mb: int = 500
    clone_timeout_sec: int = 120
    analysis_timeout_sec: int = 300
    max_files: int = 500

    # Rate limiting
    rate_limit_rpm: int = 10

    # Authentication
    api_key: Optional[str] = None

    # CORS
    cors_origins: str = "*"

    # Redis (optional)
    redis_url: Optional[str] = None

    # Server
    host: str = "127.0.0.1"
    port: int = 5001
    reload: bool = False

    # Worker pool
    max_workers: int = 4

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Initialize settings
settings = Settings()

# Convert MB to bytes
MAX_REPO_SIZE = settings.max_repo_size_mb * 1024 * 1024

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

structlog.configure(processors=[
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.JSONRenderer()
])
logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

try:
    analysis_duration = Histogram('analysis_duration_seconds',
                                  'Time spent on analysis',
                                  ['language', 'status'])

    analysis_counter = Counter('analysis_total', 'Total analyses performed',
                               ['status', 'has_issues'])

    active_analyses = Gauge('active_analyses', 'Number of active analyses')
except ValueError:
    # Metrics already registered (e.g., during module reload)
    analysis_duration = None
    analysis_counter = None
    active_analyses = None

# ---------------------------------------------------------------------------
# Redis Cache (optional)
# ---------------------------------------------------------------------------

redis_client = None
if settings.redis_url:
    try:
        redis_client = redis.from_url(settings.redis_url,
                                      decode_responses=True)
        logger.info("redis.connected", url=settings.redis_url)
    except Exception as e:
        logger.warning("redis.connection_failed", error=str(e))

# ---------------------------------------------------------------------------
# Database Manager (Singleton)
# ---------------------------------------------------------------------------


class DatabaseManager:
    """Manages database connections and operations."""
    _instance = None
    # FIX: Do NOT create asyncio.Lock() at class level — event loop may not exist yet.
    _lock: Optional[asyncio.Lock] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str):
        if not hasattr(self, 'initialized'):
            self.db_path = db_path
            self._init_db()
            self.initialized = True

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self.get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS results (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_url    TEXT NOT NULL,
                    team_name   TEXT NOT NULL,
                    leader_name TEXT NOT NULL,
                    branch_name TEXT,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    summary     TEXT,
                    issues      TEXT,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    webhook_url TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_status ON results(status);
                CREATE INDEX IF NOT EXISTS idx_created ON results(created_at);
                CREATE INDEX IF NOT EXISTS idx_team ON results(team_name);
            """)
            logger.info("database.initialized", path=self.db_path)

    @contextmanager
    def get_connection(self):
        """Get a database connection as a context manager."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path,
                                   check_same_thread=False,
                                   timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query and return cursor."""
        with self.get_connection() as conn:
            return conn.execute(query, params)

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one row as dict."""
        with self.get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return dict(row) if row else None

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows as dicts."""
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]


# Initialize database manager
db_manager = DatabaseManager(settings.db_path)


def get_db() -> DatabaseManager:
    """Dependency for FastAPI to get database manager."""
    return db_manager


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class WebhookConfig(BaseModel):
    """Webhook configuration for analysis notifications."""
    url: str
    secret: Optional[str] = None
    events: List[str] = ["completed", "failed"]


class AnalysisRequest(BaseModel):
    """Request model for repository analysis."""
    repoUrl: str
    teamName: str
    leaderName: str
    webhook: Optional[WebhookConfig] = None
    branch: Optional[str] = None

    @validator("repoUrl")
    def validate_repo_url(cls, v: str) -> str:
        v = v.strip()
        parsed = urllib.parse.urlparse(v)
        if parsed.scheme not in ("http", "https", "git", "ssh"):
            raise ValueError("Only http/https/git/ssh URLs are allowed.")
        if not parsed.netloc:
            raise ValueError("Invalid repository URL.")
        if re.search(r'[;&|`$()<>"\'\\\s]', v):
            raise ValueError("URL contains disallowed characters.")
        if len(v) > 512:
            raise ValueError("URL is too long.")
        return v

    @validator("teamName", "leaderName")
    def validate_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty.")
        if len(v) > 100:
            raise ValueError("Name too long (max 100 characters).")
        if not re.match(r'^[\w\s\-\.@]+$', v):
            raise ValueError("Name contains invalid characters.")
        return v


class Issue(BaseModel):
    """Code issue model."""
    file: str
    line: int
    column: int = 0
    type: str  # LINTING | SYNTAX | IMPORT | INDENTATION | LOGIC | SECURITY
    code: str = ""
    message: str
    severity: str = "warning"  # error | warning | info
    language: str = "unknown"


class AnalysisResult(BaseModel):
    """Analysis result model."""
    id: int
    repoUrl: str
    teamName: str
    leaderName: str
    branchName: Optional[str] = None
    status: str = "pending"
    summary: Optional[Dict[str, Any]] = None
    issues: Optional[List[Issue]] = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BatchAnalysisRequest(BaseModel):
    """Batch analysis request model."""
    requests: List[AnalysisRequest]
    parallel: bool = True


# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------

_rate_limit_store: Dict[str, List[float]] = {}


def check_rate_limit(ip: str) -> None:
    """Check if IP has exceeded rate limit."""
    now = time.monotonic()
    window = 60.0
    timestamps = [t for t in _rate_limit_store.get(ip, []) if now - t < window]

    if len(timestamps) >= settings.rate_limit_rpm:
        logger.warning("rate_limit.exceeded", ip=ip)
        raise HTTPException(status_code=429,
                            detail="Rate limit exceeded. Try again later.")

    timestamps.append(now)
    _rate_limit_store[ip] = timestamps


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------


def check_auth(request: Request) -> None:
    """Check Bearer token authentication if API key is set."""
    if not settings.api_key:
        return

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != settings.api_key:
        logger.warning("auth.failed", path=request.url.path)
        raise HTTPException(status_code=401,
                            detail="Invalid or missing API key.")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Get current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def db_create_result(request: AnalysisRequest) -> int:
    """Create a new analysis result record."""
    now = _now_iso()
    webhook_json = json.dumps(
        request.webhook.dict()) if request.webhook else None

    with db_manager.get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO results (repo_url, team_name, leader_name, branch_name, status, created_at, updated_at, webhook_url) "
            "VALUES (?, ?, ?, ?, 'pending', ?, ?, ?)",
            (request.repoUrl, request.teamName, request.leaderName,
             request.branch, now, now, webhook_json),
        )
        return cur.lastrowid


def db_update_result(result_id: int, **kwargs) -> None:
    """Update an analysis result record."""
    if not kwargs:
        return

    kwargs["updated_at"] = _now_iso()
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [result_id]

    with db_manager.get_connection() as conn:
        conn.execute(f"UPDATE results SET {sets} WHERE id = ?", values)


def db_get_result(result_id: int) -> Optional[Dict]:
    """Get a single analysis result by ID."""
    return db_manager.fetch_one("SELECT * FROM results WHERE id = ?",
                                (result_id, ))


def db_list_results(
    status: Optional[str],
    team: Optional[str],
    limit: int,
    offset: int,
) -> Tuple[List[Dict], int]:
    """List analysis results with filtering and pagination."""
    conditions, params = [], []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if team:
        conditions.append("team_name LIKE ?")
        params.append(f"%{team}%")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count
    total = db_manager.fetch_one(
        f"SELECT COUNT(*) as count FROM results {where}",
        tuple(params))["count"]

    # Get paginated results
    rows = db_manager.fetch_all(
        f"SELECT * FROM results {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset))

    return rows, total


def _deserialise_row(row: Dict) -> Dict:
    """Parse JSON columns back into objects for API responses."""
    for col in ("summary", "issues", "webhook_url"):
        if row.get(col) and isinstance(row[col], str):
            try:
                row[col] = json.loads(row[col])
            except (json.JSONDecodeError, TypeError):
                pass
    return row


# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _tool_available(tool: str) -> bool:
    """Check if a CLI tool is available on PATH."""
    return shutil.which(tool) is not None


# ---------------------------------------------------------------------------
# Command runner
# ---------------------------------------------------------------------------


def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    timeout: int = 60,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[int, str, str]:
    """
    Run a subprocess command safely.
    Returns (returncode, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                **(env or {})
            },
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        logger.warning("command.timeout", cmd=cmd[0], timeout=timeout)
        return -1, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------


def safe_file_path(base: Path, rel: str) -> Optional[Path]:
    """
    Resolve a relative path safely under base to prevent path traversal.
    Returns None if the resolved path escapes base.
    """
    try:
        resolved = (base / rel).resolve()
        base_resolved = base.resolve()
        resolved.relative_to(base_resolved)  # raises ValueError if outside
        return resolved
    except (ValueError, Exception):
        return None


def _check_repo_size(repo_dir: Path) -> bool:
    """Return True if repo is within the size limit."""
    total = sum(f.stat().st_size for f in repo_dir.rglob("*") if f.is_file())
    return total <= MAX_REPO_SIZE


# ---------------------------------------------------------------------------
# Language analysers
# ---------------------------------------------------------------------------


def _analyse_python_flake8(file_path: Path, repo_dir: Path) -> List[Issue]:
    """Run flake8 on a Python file and return issues."""
    issues: List[Issue] = []
    if not _tool_available("flake8"):
        return issues

    rel = str(file_path.relative_to(repo_dir))
    code, stdout, stderr = run_command(
        [
            "flake8", "--format=%(path)s:%(row)d:%(col)d: %(code)s %(text)s",
            str(file_path)
        ],
        cwd=str(repo_dir),
        timeout=30,
    )

    for line in stdout.splitlines():
        # format: path:row:col: CODE message
        m = re.match(r'.+?:(\d+):(\d+):\s+([A-Z]\d+)\s+(.+)', line)
        if m:
            row, col, flake_code, msg = m.groups()
            severity = "error" if flake_code.startswith("E9") else "warning"
            issues.append(
                Issue(
                    file=rel,
                    line=int(row),
                    column=int(col),
                    type="LINTING",
                    code=flake_code,
                    message=msg.strip(),
                    severity=severity,
                    language="python",
                ))

    return issues


def _analyse_python_regex(file_path: Path, repo_dir: Path) -> List[Issue]:
    """Regex-based Python analysis as a fallback when flake8 is unavailable."""
    issues: List[Issue] = []
    rel = str(file_path.relative_to(repo_dir))

    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return issues

    for i, line in enumerate(source.splitlines(), start=1):
        stripped = line.rstrip()

        # Trailing whitespace
        if stripped != line.rstrip('\n'):
            pass  # minor, skip

        # Lines that are very long
        if len(stripped) > 120:
            issues.append(
                Issue(
                    file=rel,
                    line=i,
                    column=121,
                    type="LINTING",
                    code="E501",
                    message=f"Line too long ({len(stripped)} > 120 characters)",
                    severity="warning",
                    language="python",
                ))

        # Use of bare except
        if re.match(r'\s*except\s*:', line):
            issues.append(
                Issue(
                    file=rel,
                    line=i,
                    column=1,
                    type="LOGIC",
                    code="E722",
                    message="Do not use bare 'except'",
                    severity="warning",
                    language="python",
                ))

        # Dangerous eval/exec
        if re.search(r'\beval\s*\(', line) or re.search(r'\bexec\s*\(', line):
            issues.append(
                Issue(
                    file=rel,
                    line=i,
                    column=line.index("eval") +
                    1 if "eval" in line else line.index("exec") + 1,
                    type="SECURITY",
                    code="S001",
                    message="Use of eval/exec is a potential security risk",
                    severity="error",
                    language="python",
                ))

    return issues


def _analyse_js_eslint(file_path: Path, repo_dir: Path) -> List[Issue]:
    """Run eslint on a JS/TS file and return issues."""
    issues: List[Issue] = []
    if not _tool_available("eslint"):
        return issues

    rel = str(file_path.relative_to(repo_dir))
    code, stdout, stderr = run_command(
        ["eslint", "--format=json", str(file_path)],
        cwd=str(repo_dir),
        timeout=30,
    )

    try:
        data = json.loads(stdout)
        for file_result in data:
            for msg in file_result.get("messages", []):
                issues.append(
                    Issue(
                        file=rel,
                        line=msg.get("line", 0),
                        column=msg.get("column", 0),
                        type="LINTING",
                        code=msg.get("ruleId") or "",
                        message=msg.get("message", ""),
                        severity="error"
                        if msg.get("severity") == 2 else "warning",
                        language=file_path.suffix.lstrip("."),
                    ))
    except (json.JSONDecodeError, KeyError):
        pass

    return issues


def _analyse_go(file_path: Path, repo_dir: Path) -> List[Issue]:
    """Run golint on a Go file and return issues."""
    issues: List[Issue] = []
    if not _tool_available("golint"):
        return issues

    rel = str(file_path.relative_to(repo_dir))
    code, stdout, stderr = run_command(
        ["golint", str(file_path)],
        cwd=str(repo_dir),
        timeout=30,
    )

    for line in stdout.splitlines():
        m = re.match(r'.+?:(\d+):(\d+):\s+(.+)', line)
        if m:
            row, col, msg = m.groups()
            issues.append(
                Issue(
                    file=rel,
                    line=int(row),
                    column=int(col),
                    type="LINTING",
                    code="",
                    message=msg.strip(),
                    severity="warning",
                    language="go",
                ))

    return issues


def _analyse_rust(file_path: Path, repo_dir: Path) -> List[Issue]:
    """Run cargo clippy on the Rust project and collect issues."""
    issues: List[Issue] = []
    if not _tool_available("cargo"):
        return issues

    rel = str(file_path.relative_to(repo_dir))
    code, stdout, stderr = run_command(
        ["cargo", "clippy", "--message-format=json", "--quiet"],
        cwd=str(repo_dir),
        timeout=120,
    )

    for line in stderr.splitlines():
        try:
            msg = json.loads(line)
            if msg.get("reason") != "compiler-message":
                continue
            inner = msg.get("message", {})
            spans = inner.get("spans", [{}])
            span = spans[0] if spans else {}
            if not span:
                continue
            issues.append(
                Issue(
                    file=span.get("file_name", rel),
                    line=span.get("line_start", 0),
                    column=span.get("column_start", 0),
                    type="LINTING",
                    code=inner.get("code", {}).get("code", "")
                    if inner.get("code") else "",
                    message=inner.get("message", ""),
                    severity="error"
                    if inner.get("level") == "error" else "warning",
                    language="rust",
                ))
        except (json.JSONDecodeError, KeyError, IndexError):
            continue

    return issues


# ---------------------------------------------------------------------------
# File analyser dispatcher
# ---------------------------------------------------------------------------


def analyse_file(file_path: Path, repo_dir: Path) -> List[Issue]:
    """
    Dispatch analysis to the correct analyser based on file extension.
    Falls back to regex analysis for Python when flake8 is unavailable.
    """
    ext = file_path.suffix.lower()

    if ext == ".py":
        if _tool_available("flake8"):
            return _analyse_python_flake8(file_path, repo_dir)
        return _analyse_python_regex(file_path, repo_dir)

    if ext in (".js", ".ts", ".jsx", ".tsx"):
        return _analyse_js_eslint(file_path, repo_dir)

    if ext == ".go":
        return _analyse_go(file_path, repo_dir)

    if ext == ".rs":
        return _analyse_rust(file_path, repo_dir)

    return []


# ---------------------------------------------------------------------------
# Parallel file analysis
# ---------------------------------------------------------------------------


def analyse_files_parallel(files: List[Path], repo_dir: Path) -> List[Issue]:
    """Analyse multiple files in parallel using a thread pool."""
    all_issues: List[Issue] = []

    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        futures = {
            executor.submit(analyse_file, f, repo_dir): f
            for f in files
        }
        for future in as_completed(futures):
            try:
                all_issues.extend(future.result())
            except Exception as e:
                logger.warning("file.analysis_error",
                               file=str(futures[future]),
                               error=str(e))

    return all_issues


# ---------------------------------------------------------------------------
# Dependency scanning
# ---------------------------------------------------------------------------


def scan_dependencies(repo_dir: Path) -> List[Issue]:
    """Scan Python dependencies for known vulnerabilities using safety."""
    issues: List[Issue] = []
    req_file = repo_dir / "requirements.txt"

    if not req_file.exists() or not _tool_available("safety"):
        return issues

    code, stdout, stderr = run_command(
        ["safety", "check", "-r",
         str(req_file), "--json"],
        cwd=str(repo_dir),
        timeout=60,
    )

    try:
        data = json.loads(stdout)
        for vuln in data:
            # safety JSON format: [package, affected_versions, installed, description, vuln_id]
            if isinstance(vuln, list) and len(vuln) >= 4:
                issues.append(
                    Issue(
                        file="requirements.txt",
                        line=0,
                        column=0,
                        type="SECURITY",
                        code=str(vuln[4]) if len(vuln) > 4 else "",
                        message=f"{vuln[0]} {vuln[2]}: {vuln[3]}",
                        severity="error",
                        language="python",
                    ))
    except (json.JSONDecodeError, IndexError):
        pass

    return issues


# ---------------------------------------------------------------------------
# Webhook sender
# ---------------------------------------------------------------------------


@retry(stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=2, max=10))
def send_webhook(webhook: WebhookConfig, payload: Dict[str, Any]) -> None:
    """Send a webhook notification with retry logic."""
    import urllib.request

    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    if webhook.secret:
        import hmac
        sig = hmac.new(webhook.secret.encode(), data,
                       hashlib.sha256).hexdigest()
        headers["X-Signature-SHA256"] = sig

    req = urllib.request.Request(webhook.url,
                                 data=data,
                                 headers=headers,
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("webhook.sent", url=webhook.url, status=resp.status)
    except Exception as e:
        logger.warning("webhook.failed", url=webhook.url, error=str(e))
        raise


# ---------------------------------------------------------------------------
# Core agent task (runs in thread pool)
# ---------------------------------------------------------------------------


def run_agent_task(result_id: int, request: AnalysisRequest) -> None:
    """
    Clone the repository, analyse all supported files, persist results.
    This runs synchronously inside a ThreadPoolExecutor thread.
    """
    if active_analyses:
        active_analyses.inc()

    start_time = time.monotonic()
    tmp_dir: Optional[str] = None

    try:
        db_update_result(result_id, status="processing")
        logger.info("agent.started", result_id=result_id, repo=request.repoUrl)

        # --- Clone ---
        tmp_dir = tempfile.mkdtemp(prefix="agent_")
        repo_dir = Path(tmp_dir) / "repo"

        clone_cmd = ["git", "clone", "--depth=1"]
        if request.branch:
            clone_cmd += ["-b", request.branch]
        clone_cmd += [request.repoUrl, str(repo_dir)]

        code, stdout, stderr = run_command(clone_cmd,
                                           timeout=settings.clone_timeout_sec)
        if code != 0:
            raise RuntimeError(f"Git clone failed: {stderr.strip()}")

        # --- Size check ---
        if not _check_repo_size(repo_dir):
            raise RuntimeError(
                f"Repository exceeds size limit of {settings.max_repo_size_mb} MB"
            )

        # --- Collect files ---
        all_files = [
            f for f in repo_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        if len(all_files) > settings.max_files:
            logger.warning(
                "agent.file_limit",
                result_id=result_id,
                total=len(all_files),
                limit=settings.max_files,
            )
            all_files = all_files[:settings.max_files]

        # --- Analyse ---
        issues = analyse_files_parallel(all_files, repo_dir)
        issues += scan_dependencies(repo_dir)

        # --- Build summary ---
        by_lang: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for issue in issues:
            by_lang[issue.language] = by_lang.get(issue.language, 0) + 1
            by_severity[issue.severity] = by_severity.get(issue.severity,
                                                          0) + 1
            by_type[issue.type] = by_type.get(issue.type, 0) + 1

        summary = {
            "total_files_scanned": len(all_files),
            "total_issues": len(issues),
            "issues_by_language": by_lang,
            "issues_by_severity": by_severity,
            "issues_by_type": by_type,
            "duration_seconds": round(time.monotonic() - start_time, 2),
        }

        issues_json = json.dumps([i.dict() for i in issues])
        summary_json = json.dumps(summary)

        db_update_result(
            result_id,
            status="completed",
            summary=summary_json,
            issues=issues_json,
        )

        logger.info(
            "agent.completed",
            result_id=result_id,
            issues=len(issues),
            duration=summary["duration_seconds"],
        )

        # --- Metrics ---
        if analysis_counter:
            analysis_counter.labels(status="completed",
                                    has_issues=str(len(issues) > 0)).inc()
        if analysis_duration:
            analysis_duration.labels(
                language="mixed",
                status="completed").observe(time.monotonic() - start_time)

        # --- Webhook ---
        row = db_get_result(result_id)
        if row and row.get("webhook_url"):
            try:
                wh_data = json.loads(row["webhook_url"]) if isinstance(
                    row["webhook_url"], str) else row["webhook_url"]
                if "completed" in wh_data.get("events", []):
                    wh = WebhookConfig(**wh_data)
                    send_webhook(
                        wh, {
                            "event": "completed",
                            "result_id": result_id,
                            "summary": summary
                        })
            except Exception as e:
                logger.warning("webhook.error",
                               result_id=result_id,
                               error=str(e))

    except Exception as e:
        logger.error("agent.failed", result_id=result_id, error=str(e))
        db_update_result(result_id,
                         status="failed",
                         summary=json.dumps({"error": str(e)}))

        if analysis_counter:
            analysis_counter.labels(status="failed", has_issues="false").inc()

        # Fire failure webhook
        try:
            row = db_get_result(result_id)
            if row and row.get("webhook_url"):
                wh_data = json.loads(row["webhook_url"]) if isinstance(
                    row["webhook_url"], str) else row["webhook_url"]
                if "failed" in wh_data.get("events", []):
                    wh = WebhookConfig(**wh_data)
                    send_webhook(wh, {
                        "event": "failed",
                        "result_id": result_id,
                        "error": str(e)
                    })
        except Exception:
            pass

    finally:
        if active_analyses:
            active_analyses.dec()

        if tmp_dir and os.path.exists(tmp_dir):
            try:
                shutil.rmtree(tmp_dir)
            except Exception as e:
                logger.warning("agent.cleanup_failed",
                               tmp_dir=tmp_dir,
                               error=str(e))


# ---------------------------------------------------------------------------
# FastAPI app with lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    logger.info("app.starting", version="3.0.0")
    app.state.background_tasks = set()

    yield

    logger.info("app.shutting_down")

    # Cancel tracked background tasks
    for task in list(app.state.background_tasks):
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    if redis_client:
        redis_client.close()

    logger.info("app.shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title="Code Analysis Agent",
    version="3.0.0",
    description="Automated repository linting, issue detection, and fix agent.",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",")
    if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs"}

SUPPORTED_LANGUAGES = {
    ".py": {
        "linter": "flake8",
        "formatter": "black"
    },
    ".js": {
        "linter": "eslint",
        "formatter": "prettier"
    },
    ".ts": {
        "linter": "eslint",
        "formatter": "prettier"
    },
    ".jsx": {
        "linter": "eslint",
        "formatter": "prettier"
    },
    ".tsx": {
        "linter": "eslint",
        "formatter": "prettier"
    },
    ".go": {
        "linter": "golint",
        "formatter": "gofmt"
    },
    ".rs": {
        "linter": "clippy",
        "formatter": "rustfmt"
    },
}

# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@app.post("/run-agent", status_code=202)
async def run_agent(
        request_body: AnalysisRequest,
        background_tasks: BackgroundTasks,
        req: Request,
        db: DatabaseManager = Depends(get_db),
):
    """
    Submit a repository for analysis.
    Returns immediately with the result ID; poll /results/{id} for completion.
    """
    client_ip = req.client.host if req.client else "unknown"
    check_rate_limit(client_ip)
    check_auth(req)

    # Check cache for recent identical analysis
    if redis_client:
        cache_key = f"repo:{hashlib.sha256(f'{request_body.repoUrl}:{request_body.branch}'.encode()).hexdigest()}"
        cached = redis_client.get(cache_key)
        if cached:
            logger.info("cache.hit", repo_url=request_body.repoUrl)
            return JSONResponse(
                status_code=202,
                content={
                    "cached": True,
                    "data": json.loads(cached)
                },
            )

    result_id = db_create_result(request_body)

    # FIX: Use FastAPI's BackgroundTasks properly; also track the asyncio task for shutdown.
    task = asyncio.create_task(
        asyncio.to_thread(run_agent_task, result_id, request_body))
    app.state.background_tasks.add(task)
    task.add_done_callback(app.state.background_tasks.discard)

    row = db_get_result(result_id)
    return _deserialise_row(row)


@app.post("/batch-analysis", status_code=202)
async def batch_analysis(
    request_body: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    req: Request,
):
    """Submit multiple repositories for analysis."""
    client_ip = req.client.host if req.client else "unknown"
    check_rate_limit(client_ip)
    check_auth(req)

    result_ids = []

    for analysis_req in request_body.requests:
        result_id = db_create_result(analysis_req)
        result_ids.append(result_id)

        if request_body.parallel:
            task = asyncio.create_task(
                asyncio.to_thread(run_agent_task, result_id, analysis_req))
            app.state.background_tasks.add(task)
            task.add_done_callback(app.state.background_tasks.discard)
        else:
            # Sequential: use FastAPI background tasks (runs one after another)
            background_tasks.add_task(run_agent_task, result_id, analysis_req)

    return {
        "result_ids": result_ids,
        "count": len(result_ids),
        "parallel": request_body.parallel,
        "status": "processing",
    }


@app.get("/results")
async def list_results(
        req: Request,
        status: Optional[str] = Query(
            None,
            description="Filter by status (pending/processing/completed/failed)"
        ),
        team: Optional[str] = Query(
            None, description="Filter by team name (partial match)"),
        limit: int = Query(20, ge=1, le=100),
        offset: int = Query(0, ge=0),
):
    """List analysis results with filtering and pagination."""
    check_auth(req)

    rows, total = db_list_results(status, team, limit, offset)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_deserialise_row(r) for r in rows],
    }


@app.get("/results/{result_id}")
async def get_result(result_id: int, req: Request):
    """Get a specific analysis result by ID."""
    check_auth(req)

    # Check cache
    if redis_client:
        cache_key = f"analysis:{result_id}"
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    row = db_get_result(result_id)
    if not row:
        raise HTTPException(status_code=404, detail="Result not found.")

    result = _deserialise_row(row)

    # Cache completed results for 5 minutes
    if redis_client and row.get("status") == "completed":
        try:
            redis_client.setex(f"analysis:{result_id}", 300,
                               json.dumps(result))
        except Exception:
            pass

    return result


@app.delete("/results/{result_id}", status_code=204)
async def delete_result(result_id: int, req: Request):
    """Delete a result record (completed or failed only)."""
    check_auth(req)

    row = db_get_result(result_id)
    if not row:
        raise HTTPException(status_code=404, detail="Result not found.")

    if row["status"] in ("pending", "processing"):
        raise HTTPException(status_code=409,
                            detail="Cannot delete an active analysis.")

    with db_manager.get_connection() as conn:
        conn.execute("DELETE FROM results WHERE id = ?", (result_id, ))

    if redis_client:
        try:
            redis_client.delete(f"analysis:{result_id}")
        except Exception:
            pass


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_ok = True
    redis_ok = redis_client is not None

    try:
        with db_manager.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception as e:
        db_ok = False
        logger.error("health.db_failed", error=str(e))

    if redis_client:
        try:
            redis_client.ping()
        except Exception as e:
            redis_ok = False
            logger.error("health.redis_failed", error=str(e))

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": _now_iso(),
        "database": "ok" if db_ok else "error",
        # FIX: redis_client may be None; report 'disabled' in that case
        "redis": "ok" if redis_ok else
        ("error" if redis_client else "disabled"),
        "tools": {
            "flake8": _tool_available("flake8"),
            "eslint": _tool_available("eslint"),
            "golint": _tool_available("golint"),
            "cargo": _tool_available("cargo"),
            "npm": _tool_available("npm"),
            "safety": _tool_available("safety"),
        },
        "config": {
            "rateLimitRpm": settings.rate_limit_rpm,
            "maxFilesPerRepo": settings.max_files,
            "maxRepoSizeMB": settings.max_repo_size_mb,
            "maxWorkers": settings.max_workers,
        },
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/stats")
async def get_stats(req: Request):
    """Get analysis statistics."""
    check_auth(req)

    with db_manager.get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]

        status_counts: Dict[str, int] = {}
        for row in conn.execute(
                "SELECT status, COUNT(*) FROM results GROUP BY status"):
            status_counts[row[0]] = row[1]

        issues_stats = conn.execute("""
            SELECT
                SUM(json_array_length(issues)) as total_issues,
                AVG(json_array_length(issues)) as avg_issues
            FROM results
            WHERE status = 'completed' AND issues IS NOT NULL
        """).fetchone()

    return {
        "total_analyses":
        total,
        "status_breakdown":
        status_counts,
        "total_issues":
        issues_stats[0] if issues_stats and issues_stats[0] else 0,
        "avg_issues_per_repo":
        round(issues_stats[1], 2) if issues_stats and issues_stats[1] else 0,
        # FIX: Guard against active_analyses being None (metrics registration failure)
        "active_analyses":
        active_analyses._value.get() if active_analyses else 0,
    }


# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------


@app.exception_handler(Exception)
async def global_exception_handler(req: Request, exc: Exception):
    """Global exception handler for unhandled exceptions."""
    logger.error(
        "unhandled_exception",
        path=req.url.path,
        method=req.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def get_module_name() -> str:
    """Determine the module name for uvicorn, falling back to 'main'."""
    import __main__
    import inspect

    try:
        if hasattr(__main__, "__file__") and __main__.__file__:
            return Path(__main__.__file__).stem
    except Exception:
        pass

    try:
        frame = inspect.currentframe()
        if frame:
            current_file = inspect.getfile(frame)
            if current_file and current_file != "<string>" and os.path.exists(
                    current_file):
                return Path(current_file).stem
    except Exception:
        pass

    try:
        if sys.argv and sys.argv[0] and sys.argv[0] != "-c":
            return Path(sys.argv[0]).stem
    except Exception:
        pass

    logger.info("module_name.fallback", name="main")
    return "main"


if __name__ == "__main__":
    import uvicorn

    module_name = get_module_name()
    print(f"Starting server with module: {module_name}")
    print(
        f"Settings: host={settings.host}, port={settings.port}, reload={settings.reload}"
    )

    uvicorn.run(
        f"{module_name}:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
    )

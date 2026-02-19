"""
Code Analysis Agent - Production-ready version with comprehensive fixes and improvements.
Version: 3.1.0
"""

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
import hmac
import urllib.request
import urllib.parse
import inspect
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set, Union
from datetime import datetime, timezone
from weakref import WeakSet
from functools import lru_cache, wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import signal
import gc
import fnmatch
import threading
from datetime import timedelta

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, PlainTextResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, field_validator, Field, ConfigDict
from pydantic_settings import BaseSettings
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
import redis
import git
from git import Repo, GitCommandError
import aiohttp
import aiofiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pytz

# ---------------------------------------------------------------------------
# Configuration Management
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Application settings with environment variable override."""
    # Database
    db_path: str = "agent_results.db"
    database_url: Optional[str] = None
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_echo: bool = False

    # Repository limits
    max_repo_size_mb: int = 500
    clone_timeout_sec: int = 120
    analysis_timeout_sec: int = 300
    max_files: int = 500
    max_file_size_kb: int = 1024  # Skip files larger than 1MB

    # Rate limiting
    rate_limit_rpm: int = 10
    rate_limit_burst: int = 20

    # Authentication
    api_key: Optional[str] = None
    api_key_header: str = "X-API-Key"

    # CORS
    cors_origins: str = "*"
    cors_allow_credentials: bool = True
    cors_allow_methods: List[str] = ["*"]
    cors_allow_headers: List[str] = ["*"]

    # Redis (optional)
    redis_url: Optional[str] = None
    redis_ssl: bool = False
    redis_cache_ttl: int = 300

    # Server
    host: str = "127.0.0.1"
    port: int = 5001
    reload: bool = False
    workers: int = 4
    max_request_size: int = 10_485_760  # 10MB

    # Worker pool
    max_workers: int = 4
    worker_queue_size: int = 100

    # Logging
    log_level: str = "INFO"
    log_json: bool = True
    log_file: Optional[str] = None

    # Security
    secret_key: str = Field(default="change-me-in-production", min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    bcrypt_rounds: int = 12

    # Analysis
    supported_extensions: List[str] = [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
        ".java", ".rb", ".php", ".c", ".cpp", ".h", ".hpp"
    ]
    enable_auto_fix: bool = False
    enable_deep_analysis: bool = False

    # Notification
    max_webhook_retries: int = 3
    webhook_timeout_sec: int = 10

    # Cleanup
    cleanup_temp_dirs: bool = True
    temp_dir_age_hours: int = 24
    enable_scheduled_cleanup: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Initialize settings
settings = Settings()

# Convert MB to bytes
MAX_REPO_SIZE = settings.max_repo_size_mb * 1024 * 1024
MAX_FILE_SIZE = settings.max_file_size_kb * 1024

# ---------------------------------------------------------------------------
# Structured Logging
# ---------------------------------------------------------------------------

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=structlog.threadlocal.wrap_dict(dict),
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Setup logging
logging.basicConfig(
    format="%(message)s",
    level=getattr(logging, settings.log_level),
    handlers=[
        logging.StreamHandler(),
        *(logging.FileHandler(settings.log_file) if settings.log_file else [])
    ]
)

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------------------------

# Clean up any existing metrics to avoid duplicates
for collector in list(REGISTRY._collector_to_names):
    try:
        REGISTRY.unregister(collector)
    except KeyError:
        pass

# Define metrics
analysis_duration = Histogram(
    'analysis_duration_seconds',
    'Time spent on analysis',
    ['language', 'status'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

analysis_counter = Counter(
    'analysis_total',
    'Total analyses performed',
    ['status', 'has_issues']
)

active_analyses = Gauge(
    'active_analyses',
    'Number of active analyses'
)

file_analysis_duration = Histogram(
    'file_analysis_duration_seconds',
    'Time spent analyzing individual files',
    ['language']
)

cache_hits = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type']
)

cache_misses = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

error_counter = Counter(
    'errors_total',
    'Total errors by type',
    ['error_type', 'component']
)

# ---------------------------------------------------------------------------
# Redis Cache (with connection pooling)
# ---------------------------------------------------------------------------

class RedisManager:
    """Manages Redis connections with pooling and failover."""

    def __init__(self):
        self._client = None
        self._pool = None
        self._connected = False

    def connect(self):
        """Establish Redis connection."""
        if not settings.redis_url:
            return

        try:
            self._pool = redis.ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                ssl=settings.redis_ssl,
                max_connections=10,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            self._client = redis.Redis(connection_pool=self._pool)
            self._client.ping()
            self._connected = True
            logger.info("redis.connected", url=settings.redis_url)
        except Exception as e:
            self._connected = False
            logger.warning("redis.connection_failed", error=str(e))
            error_counter.labels(error_type="redis_connection", component="cache").inc()

    @property
    def client(self) -> Optional[redis.Redis]:
        """Get Redis client."""
        return self._client if self._connected else None

    def close(self):
        """Close Redis connections."""
        if self._pool:
            self._pool.disconnect()
            self._connected = False
            logger.info("redis.disconnected")

    async def get_cached(self, key: str) -> Optional[Any]:
        """Get cached value with metrics."""
        if not self.client:
            cache_misses.labels(cache_type="redis").inc()
            return None

        try:
            value = await asyncio.to_thread(self.client.get, key)
            if value:
                cache_hits.labels(cache_type="redis").inc()
                return json.loads(value)
            cache_misses.labels(cache_type="redis").inc()
            return None
        except Exception as e:
            logger.warning("redis.get_failed", key=key, error=str(e))
            error_counter.labels(error_type="redis_get", component="cache").inc()
            return None

    async def set_cached(self, key: str, value: Any, ttl: int = None):
        """Set cached value with TTL."""
        if not self.client:
            return

        try:
            ttl = ttl or settings.redis_cache_ttl
            await asyncio.to_thread(
                self.client.setex,
                key,
                ttl,
                json.dumps(value, default=str)
            )
        except Exception as e:
            logger.warning("redis.set_failed", key=key, error=str(e))
            error_counter.labels(error_type="redis_set", component="cache").inc()


redis_manager = RedisManager()

# ---------------------------------------------------------------------------
# Database Manager (Enhanced)
# ---------------------------------------------------------------------------

class DatabaseManager:
    """Enhanced database manager with connection pooling and migrations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._local = threading.local()
        self._init_db()
        self._run_migrations()

    def _get_conn(self):
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30,
                isolation_level=None  # Autocommit mode
            )
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn.execute("PRAGMA busy_timeout=30000")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.execute("PRAGMA cache_size=-64000")  # 64MB
            self._local.conn.execute("PRAGMA mmap_size=268435456")  # 256MB
        return self._local.conn

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
                    webhook_url TEXT,
                    metadata    TEXT,
                    started_at  TEXT,
                    completed_at TEXT,
                    duration_ms INTEGER,
                    git_commit_sha TEXT,
                    git_tag     TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_results_status ON results(status);
                CREATE INDEX IF NOT EXISTS idx_results_created ON results(created_at);
                CREATE INDEX IF NOT EXISTS idx_results_team ON results(team_name);
                CREATE INDEX IF NOT EXISTS idx_results_repo ON results(repo_url);
                CREATE INDEX IF NOT EXISTS idx_results_updated ON results(updated_at);

                CREATE TABLE IF NOT EXISTS analysis_queue (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id   INTEGER NOT NULL,
                    priority    INTEGER DEFAULT 0,
                    status      TEXT DEFAULT 'queued',
                    created_at  TEXT NOT NULL,
                    started_at  TEXT,
                    completed_at TEXT,
                    worker_id   TEXT,
                    retry_count INTEGER DEFAULT 0,
                    error_msg   TEXT,
                    FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_queue_status ON analysis_queue(status, priority);

                CREATE TABLE IF NOT EXISTS file_cache (
                    file_hash   TEXT PRIMARY KEY,
                    repo_url    TEXT NOT NULL,
                    file_path   TEXT NOT NULL,
                    issues      TEXT,
                    analyzed_at TEXT NOT NULL,
                    size_bytes  INTEGER,
                    language    TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_file_cache_repo ON file_cache(repo_url);

                CREATE TABLE IF NOT EXISTS rate_limits (
                    ip_address  TEXT PRIMARY KEY,
                    request_count INTEGER DEFAULT 1,
                    window_start REAL NOT NULL,
                    updated_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS api_keys (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_hash    TEXT UNIQUE NOT NULL,
                    team_name   TEXT NOT NULL,
                    created_by  TEXT NOT NULL,
                    created_at  TEXT NOT NULL,
                    expires_at  TEXT,
                    last_used   TEXT,
                    is_active   INTEGER DEFAULT 1,
                    permissions TEXT
                );

                CREATE TABLE IF NOT EXISTS webhook_delivery (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id   INTEGER NOT NULL,
                    webhook_url TEXT NOT NULL,
                    event       TEXT NOT NULL,
                    status      INTEGER,
                    response    TEXT,
                    attempt     INTEGER DEFAULT 1,
                    created_at  TEXT NOT NULL,
                    delivered_at TEXT,
                    FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE
                );

                CREATE TRIGGER IF NOT EXISTS update_results_timestamp
                    AFTER UPDATE ON results
                BEGIN
                    UPDATE results SET updated_at = datetime('now')
                    WHERE id = NEW.id;
                END;
            """)

            logger.info("database.initialized", path=self.db_path)

    def _run_migrations(self):
        """Run database migrations."""
        with self.get_connection() as conn:
            # Check if migrations table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    applied_at TEXT NOT NULL
                )
            """)

            # Get current version
            current = conn.execute(
                "SELECT MAX(version) FROM migrations"
            ).fetchone()[0] or 0

            migrations = [
                (1, """
                    ALTER TABLE results ADD COLUMN metadata TEXT;
                    ALTER TABLE results ADD COLUMN started_at TEXT;
                    ALTER TABLE results ADD COLUMN completed_at TEXT;
                    ALTER TABLE results ADD COLUMN duration_ms INTEGER;
                """),
                (2, """
                    ALTER TABLE results ADD COLUMN git_commit_sha TEXT;
                    ALTER TABLE results ADD COLUMN git_tag TEXT;
                """),
                (3, """
                    CREATE TABLE IF NOT EXISTS file_cache (
                        file_hash TEXT PRIMARY KEY,
                        repo_url TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        issues TEXT,
                        analyzed_at TEXT NOT NULL,
                        size_bytes INTEGER,
                        language TEXT
                    );
                """),
            ]

            for version, sql in migrations:
                if version > current:
                    try:
                        conn.executescript(sql)
                        conn.execute(
                            "INSERT INTO migrations (version, applied_at) VALUES (?, datetime('now'))",
                            (version,)
                        )
                        logger.info("migration.applied", version=version)
                    except Exception as e:
                        logger.error("migration.failed", version=version, error=str(e))
                        error_counter.labels(error_type="migration", component="database").inc()

    @contextmanager
    def get_connection(self):
        """Get a database connection as a context manager."""
        conn = None
        try:
            conn = self._get_conn()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("database.error", error=str(e))
            error_counter.labels(error_type="database", component="database").inc()
            raise
        finally:
            # Don't close connection, just return to pool
            pass

    @contextmanager
    def transaction(self):
        """Database transaction context manager."""
        with self.get_connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    async def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a query asynchronously."""
        return await asyncio.to_thread(self._execute_sync, query, params)

    def _execute_sync(self, query: str, params: tuple) -> sqlite3.Cursor:
        """Synchronous query execution."""
        with self.get_connection() as conn:
            return conn.execute(query, params)

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch one row as dict."""
        return await asyncio.to_thread(self._fetch_one_sync, query, params)

    def _fetch_one_sync(self, query: str, params: tuple) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(query, params).fetchone()
            return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows as dicts."""
        return await asyncio.to_thread(self._fetch_all_sync, query, params)

    def _fetch_all_sync(self, query: str, params: tuple) -> List[Dict]:
        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    async def vacuum(self):
        """VACUUM the database."""
        await asyncio.to_thread(self._vacuum_sync)

    def _vacuum_sync(self):
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            logger.info("database.vacuumed")


# Initialize database manager
db_manager = DatabaseManager(settings.db_path)

# ---------------------------------------------------------------------------
# Enhanced Pydantic models
# ---------------------------------------------------------------------------


class WebhookConfig(BaseModel):
    """Webhook configuration for analysis notifications."""
    url: str = Field(..., description="Webhook URL")
    secret: Optional[str] = Field(None, description="Secret for signing payloads")
    events: List[str] = Field(["completed", "failed"], description="Events to trigger on")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")
    timeout: int = Field(10, description="Timeout in seconds", ge=1, le=60)

    @field_validator("url")
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        parsed = urllib.parse.urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP/HTTPS URLs are allowed")
        if not parsed.netloc:
            raise ValueError("Invalid URL")
        return v

    @field_validator("events")
    def validate_events(cls, v: List[str]) -> List[str]:
        valid_events = {"started", "completed", "failed", "progress"}
        for event in v:
            if event not in valid_events:
                raise ValueError(f"Invalid event: {event}. Must be one of {valid_events}")
        return v


class Issue(BaseModel):
    """Code issue model with enhanced fields."""
    file: str = Field(..., description="File path")
    line: int = Field(..., ge=0, description="Line number")
    column: int = Field(0, ge=0, description="Column number")
    end_line: Optional[int] = Field(None, ge=0, description="End line for range")
    end_column: Optional[int] = Field(None, ge=0, description="End column for range")
    type: str = Field(..., description="Issue type")
    code: str = Field("", description="Error/warning code")
    message: str = Field(..., description="Issue description")
    severity: str = Field("warning", description="Severity level")
    language: str = Field("unknown", description="Programming language")
    category: str = Field("style", description="Issue category")
    fixable: bool = Field(False, description="Whether issue can be auto-fixed")
    suggested_fix: Optional[str] = Field(None, description="Suggested fix")
    documentation_url: Optional[str] = Field(None, description="URL to documentation")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "file": "main.py",
                "line": 42,
                "column": 8,
                "type": "LINTING",
                "code": "E501",
                "message": "Line too long (89 > 79 characters)",
                "severity": "warning",
                "language": "python"
            }
        }
    )


class AnalysisRequest(BaseModel):
    """Enhanced request model for repository analysis."""
    repoUrl: str = Field(..., description="Git repository URL")
    teamName: str = Field(..., description="Team name", max_length=100)
    leaderName: str = Field(..., description="Team leader name", max_length=100)
    webhook: Optional[WebhookConfig] = Field(None, description="Webhook configuration")
    branch: Optional[str] = Field(None, description="Branch to analyze", max_length=100)
    tag: Optional[str] = Field(None, description="Tag to analyze", max_length=100)
    commit_sha: Optional[str] = Field(None, description="Specific commit to analyze")
    depth: int = Field(1, description="Git clone depth", ge=1, le=10)
    submodules: bool = Field(False, description="Clone submodules")
    exclude_patterns: List[str] = Field(default_factory=list, description="File patterns to exclude")
    include_patterns: List[str] = Field(default_factory=list, description="File patterns to include")
    enable_deep_analysis: bool = Field(False, description="Enable deep analysis")
    auto_fix: bool = Field(False, description="Auto-fix issues when possible")
    priority: int = Field(0, description="Analysis priority", ge=0, le=10)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("repoUrl")
    def validate_repo_url(cls, v: str) -> str:
        v = v.strip()
        # Check for git URL patterns
        git_patterns = [
            r'^git@[\w\.-]+:[\w\.-]+/[\w\.-]+\.git$',
            r'^https?://[\w\.-]+/[\w\.-]+/[\w\.-]+(\.git)?$',
            r'^ssh://[\w\.-]+@[\w\.-]+/[\w\.-]+/[\w\.-]+\.git$'
        ]

        if not any(re.match(p, v) for p in git_patterns):
            parsed = urllib.parse.urlparse(v)
            if parsed.scheme not in ("http", "https", "git", "ssh"):
                raise ValueError("Only http/https/git/ssh URLs are allowed")
            if not parsed.netloc:
                raise ValueError("Invalid repository URL")

        # Security checks
        if re.search(r'[;&|`$()<>"\'\\\s]', v):
            raise ValueError("URL contains disallowed characters")
        if len(v) > 512:
            raise ValueError("URL is too long")

        # Normalize URL
        if not v.endswith('.git'):
            v += '.git'

        return v

    @field_validator("teamName", "leaderName")
    def validate_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) > 100:
            raise ValueError("Name too long (max 100 characters)")
        if not re.match(r'^[\w\s\-\.@]+$', v):
            raise ValueError("Name contains invalid characters")
        return v

    @field_validator("exclude_patterns", "include_patterns")
    def validate_patterns(cls, v: List[str]) -> List[str]:
        for pattern in v:
            if len(pattern) > 200:
                raise ValueError(f"Pattern too long: {pattern}")
            # Validate glob pattern
            try:
                re.compile(pattern.replace('*', '.*').replace('?', '.'))
            except re.error:
                raise ValueError(f"Invalid pattern: {pattern}")
        return v


class BatchAnalysisRequest(BaseModel):
    """Enhanced batch analysis request model."""
    requests: List[AnalysisRequest] = Field(..., min_length=1, max_length=50)
    parallel: bool = Field(True, description="Run analyses in parallel")
    continue_on_error: bool = Field(False, description="Continue on individual failures")
    priority: int = Field(0, description="Batch priority", ge=0, le=10)
    webhook: Optional[WebhookConfig] = Field(None, description="Global webhook for all analyses")


class AnalysisResult(BaseModel):
    """Enhanced analysis result model."""
    id: int
    repoUrl: str
    teamName: str
    leaderName: str
    branchName: Optional[str] = None
    tag: Optional[str] = None
    commitSha: Optional[str] = None
    status: str
    summary: Optional[Dict[str, Any]] = None
    issues: Optional[List[Issue]] = None
    createdAt: datetime
    updatedAt: datetime
    startedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None
    durationMs: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    webhook: Optional[WebhookConfig] = None

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str = "3.1.0"
    database: str
    redis: str
    disk_space: Dict[str, Any]
    tools: Dict[str, bool]
    active_analyses: int
    queue_size: int
    config: Dict[str, Any]


class StatsResponse(BaseModel):
    """Statistics response model."""
    total_analyses: int
    status_breakdown: Dict[str, int]
    total_issues: int
    avg_issues_per_repo: float
    active_analyses: int
    queue_size: int
    avg_duration_ms: Optional[float]
    top_issue_types: List[Dict[str, Any]]
    top_languages: List[Dict[str, Any]]
    analyses_trend: List[Dict[str, Any]]


class ApiKeyCreate(BaseModel):
    """API key creation request."""
    team_name: str
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)
    permissions: List[str] = Field(default_factory=list)


class ApiKeyResponse(BaseModel):
    """API key response."""
    key: str
    team_name: str
    created_at: datetime
    expires_at: Optional[datetime]


# ---------------------------------------------------------------------------
# Rate Limiter (Enhanced with persistent storage)
# ---------------------------------------------------------------------------

class RateLimiter:
    """Enhanced rate limiter with persistent storage."""

    def __init__(self):
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.monotonic()

    async def check_rate_limit(self, ip: str) -> None:
        """Check if IP has exceeded rate limit."""
        now = time.monotonic()

        # Periodic cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            await self._cleanup_old_entries()
            self._last_cleanup = now

        # Get current window
        window_start = now - 60  # 60 second window

        # Try Redis first
        if redis_manager.client:
            await self._check_rate_limit_redis(ip, now, window_start)
        else:
            await self._check_rate_limit_sqlite(ip, now, window_start)

    async def _check_rate_limit_redis(self, ip: str, now: float, window_start: float):
        """Check rate limit using Redis."""
        key = f"rate_limit:{ip}"

        # Use Redis pipelining for atomic operation
        pipe = redis_manager.client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)  # Remove old entries
        pipe.zcard(key)  # Get current count
        pipe.zadd(key, {str(now): now})  # Add current request
        pipe.expire(key, 120)  # Set expiry
        results = pipe.execute()

        count = results[1]  # zcard result

        if count >= settings.rate_limit_rpm:
            logger.warning("rate_limit.exceeded", ip=ip, count=count)
            error_counter.labels(error_type="rate_limit", component="api").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {settings.rate_limit_rpm} requests per minute."
            )

    async def _check_rate_limit_sqlite(self, ip: str, now: float, window_start: float):
        """Check rate limit using SQLite."""
        async with db_manager.transaction() as conn:
            # Clean old entries
            await conn.execute(
                "DELETE FROM rate_limits WHERE window_start < ?",
                (window_start,)
            )

            # Get current count
            row = await conn.execute(
                "SELECT request_count FROM rate_limits WHERE ip_address = ?",
                (ip,)
            ).fetchone()

            count = row[0] if row else 0

            if count >= settings.rate_limit_rpm:
                logger.warning("rate_limit.exceeded", ip=ip, count=count)
                error_counter.labels(error_type="rate_limit", component="api").inc()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {settings.rate_limit_rpm} requests per minute."
                )

            # Update or insert
            if row:
                await conn.execute(
                    "UPDATE rate_limits SET request_count = request_count + 1, updated_at = ? WHERE ip_address = ?",
                    (datetime.now(timezone.utc).isoformat(), ip)
                )
            else:
                await conn.execute(
                    "INSERT INTO rate_limits (ip_address, request_count, window_start, updated_at) VALUES (?, 1, ?, ?)",
                    (ip, now, datetime.now(timezone.utc).isoformat())
                )

    async def _cleanup_old_entries(self):
        """Clean up old rate limit entries."""
        window_start = time.monotonic() - 120  # Clean entries older than 2 minutes

        if redis_manager.client:
            # Cleanup Redis keys
            keys = redis_manager.client.keys("rate_limit:*")
            for key in keys:
                redis_manager.client.zremrangebyscore(key, 0, window_start)
        else:
            # Cleanup SQLite
            async with db_manager.transaction() as conn:
                await conn.execute(
                    "DELETE FROM rate_limits WHERE window_start < ?",
                    (window_start,)
                )


rate_limiter = RateLimiter()

# ---------------------------------------------------------------------------
# Authentication (Enhanced)
# ---------------------------------------------------------------------------

class AuthManager:
    """Enhanced authentication manager."""

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 60

    async def check_auth(self, request: Request) -> None:
        """Check authentication."""
        if not settings.api_key:
            return

        # Get API key from header
        api_key = request.headers.get(settings.api_key_header)
        if not api_key:
            # Try Bearer token
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                api_key = auth[7:]

        if not api_key:
            logger.warning("auth.missing", path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Validate API key
        if not await self._validate_api_key(api_key, request):
            logger.warning("auth.invalid", path=request.url.path)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )

    async def _validate_api_key(self, api_key: str, request: Request) -> bool:
        """Validate API key against database."""
        # Check cache first
        now = time.monotonic()
        if api_key in self._cache:
            expiry, _ = self._cache[api_key]
            if now < expiry:
                return True

        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Check database
        row = await db_manager.fetch_one(
            "SELECT id, team_name, expires_at, is_active, permissions FROM api_keys WHERE key_hash = ? AND is_active = 1",
            (key_hash,)
        )

        if not row:
            return False

        # Check expiry
        if row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                return False

        # Update last used
        await db_manager.execute(
            "UPDATE api_keys SET last_used = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), row["id"])
        )

        # Add to cache
        self._cache[api_key] = (now + self._cache_ttl, row)

        # Add team info to request state
        request.state.team = row["team_name"]
        request.state.permissions = json.loads(row["permissions"]) if row["permissions"] else []

        return True

    async def create_api_key(self, team_name: str, expires_in_days: Optional[int] = None,
                            permissions: Optional[List[str]] = None) -> str:
        """Create a new API key."""
        # Generate random key
        api_key = hashlib.sha256(os.urandom(32)).hexdigest()[:32]
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()

        # Store in database
        await db_manager.execute(
            """
            INSERT INTO api_keys (key_hash, team_name, created_by, created_at, expires_at, permissions)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                key_hash,
                team_name,
                "system",
                datetime.now(timezone.utc).isoformat(),
                expires_at,
                json.dumps(permissions or [])
            )
        )

        return api_key

    async def revoke_api_key(self, key_hash: str) -> None:
        """Revoke an API key."""
        await db_manager.execute(
            "UPDATE api_keys SET is_active = 0 WHERE key_hash = ?",
            (key_hash,)
        )

        # Clear from cache
        self._cache = {k: v for k, v in self._cache.items() if v[1]["key_hash"] != key_hash}


auth_manager = AuthManager()

# Dependency for FastAPI
async def require_auth(request: Request):
    """Authentication dependency."""
    await auth_manager.check_auth(request)

# ---------------------------------------------------------------------------
# Enhanced Webhook Sender
# ---------------------------------------------------------------------------

class WebhookSender:
    """Enhanced webhook sender with retry logic and delivery tracking."""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=settings.webhook_timeout_sec),
                connector=aiohttp.TCPConnector(limit=100)
            )
        return self._session

    async def close(self):
        """Close session."""
        if self._session and not self._session.closed:
            await self._session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def send_webhook(self, webhook: WebhookConfig, payload: Dict[str, Any],
                          result_id: int, event: str) -> bool:
        """Send webhook with retry logic."""
        session = await self.get_session()

        # Prepare payload
        full_payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result_id": result_id,
            "data": payload
        }

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "CodeAnalysisAgent/3.1.0",
            **webhook.headers
        }

        # Add signature if secret provided
        if webhook.secret:
            body = json.dumps(full_payload, default=str).encode()
            signature = hmac.new(
                webhook.secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            headers["X-Signature-SHA256"] = signature

        # Track delivery
        delivery_id = await self._track_delivery_start(result_id, webhook.url, event)

        try:
            async with session.post(
                webhook.url,
                json=full_payload,
                headers=headers,
                timeout=webhook.timeout
            ) as response:
                response_text = await response.text()

                # Track delivery result
                await self._track_delivery_complete(
                    delivery_id,
                    response.status,
                    response_text[:1000]  # Limit response size
                )

                if 200 <= response.status < 300:
                    logger.info(
                        "webhook.sent",
                        url=webhook.url,
                        event=event,
                        status=response.status
                    )
                    return True
                else:
                    logger.warning(
                        "webhook.failed",
                        url=webhook.url,
                        event=event,
                        status=response.status,
                        response=response_text[:200]
                    )
                    return False

        except Exception as e:
            logger.warning(
                "webhook.error",
                url=webhook.url,
                event=event,
                error=str(e)
            )
            await self._track_delivery_error(delivery_id, str(e))
            raise

    async def _track_delivery_start(self, result_id: int, url: str, event: str) -> int:
        """Track webhook delivery start."""
        cursor = await db_manager.execute(
            """
            INSERT INTO webhook_delivery (result_id, webhook_url, event, created_at)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """,
            (result_id, url, event, datetime.now(timezone.utc).isoformat())
        )
        return cursor.lastrowid

    async def _track_delivery_complete(self, delivery_id: int, status: int, response: str):
        """Track webhook delivery completion."""
        await db_manager.execute(
            """
            UPDATE webhook_delivery
            SET status = ?, response = ?, delivered_at = ?
            WHERE id = ?
            """,
            (status, response, datetime.now(timezone.utc).isoformat(), delivery_id)
        )

    async def _track_delivery_error(self, delivery_id: int, error: str):
        """Track webhook delivery error."""
        await db_manager.execute(
            """
            UPDATE webhook_delivery
            SET response = ?, delivered_at = ?
            WHERE id = ?
            """,
            (error, datetime.now(timezone.utc).isoformat(), delivery_id)
        )


webhook_sender = WebhookSender()

# ---------------------------------------------------------------------------
# Enhanced Git Operations
# ---------------------------------------------------------------------------

class GitManager:
    """Enhanced Git operations with better error handling and security."""

    def __init__(self):
        self._git_config = {
            'core.longpaths': 'true' if sys.platform == 'win32' else 'false',
            'core.autocrlf': 'false',
            'core.eol': 'lf',
            'core.symlinks': 'false',
            'advice.detachedHead': 'false',
            'clone.defaultRemoteName': 'origin',
            'clone.rejectShallow': 'false'
        }

    async def clone_repository(
        self,
        url: str,
        dest_path: Path,
        branch: Optional[str] = None,
        tag: Optional[str] = None,
        commit_sha: Optional[str] = None,
        depth: int = 1,
        submodules: bool = False
    ) -> Dict[str, Any]:
        """Clone repository with advanced options."""
        start_time = time.monotonic()

        # Validate URL
        if not self._validate_git_url(url):
            raise ValueError(f"Invalid or potentially malicious Git URL: {url}")

        try:
            # Configure Git environment
            env = os.environ.copy()
            env['GIT_TERMINAL_PROMPT'] = '0'
            env['GIT_ASKPASS'] = 'echo'
            env['GIT_SSH_COMMAND'] = 'ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

            # Prepare clone options
            clone_kwargs = {
                'depth': depth,
                'env': env,
                'no_single_branch': False,
                'config': self._git_config
            }

            if branch:
                clone_kwargs['branch'] = branch
            elif tag:
                # For tags, we need to clone then checkout
                clone_kwargs['branch'] = 'master'  # Clone default branch first

            # Clone repository
            repo = await asyncio.to_thread(
                Repo.clone_from,
                url,
                str(dest_path),
                **clone_kwargs
            )

            # Handle tag or specific commit
            if tag and not branch:
                await asyncio.to_thread(repo.git.checkout, tag)
            elif commit_sha:
                await asyncio.to_thread(repo.git.checkout, commit_sha)

            # Handle submodules
            if submodules:
                await asyncio.to_thread(repo.submodule_update, init=True, recursive=True)

            # Get repository info
            info = await self._get_repo_info(repo)
            info['clone_duration'] = time.monotonic() - start_time

            return info

        except GitCommandError as e:
            logger.error("git.clone_failed", url=url, error=str(e))
            error_counter.labels(error_type="git_clone", component="git").inc()
            raise RuntimeError(f"Git clone failed: {e.stderr or str(e)}") from e
        except Exception as e:
            logger.error("git.clone_error", url=url, error=str(e))
            error_counter.labels(error_type="git_error", component="git").inc()
            raise

    def _validate_git_url(self, url: str) -> bool:
        """Validate Git URL for security."""
        # Block potentially dangerous patterns
        dangerous_patterns = [
            r'[;&|`$()<>"\'\\]',  # Shell metacharacters
            r'^-{2,}',  # Options starting with dash
            r'@[^\w\.-]',  # Invalid characters after @
            r'\.{2,}',  # Path traversal
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, url):
                return False

        # Parse URL
        try:
            # Handle SSH URLs
            if url.startswith('git@'):
                parts = url.split('@')[1].split(':')
                if len(parts) != 2:
                    return False
                host, path = parts
                if not host or not path:
                    return False
                if not path.endswith('.git') and not path.endswith('/'):
                    return False
                return True

            # Handle HTTP/HTTPS URLs
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme in ('http', 'https', 'git', 'ssh'):
                if not parsed.netloc:
                    return False
                if parsed.scheme in ('http', 'https') and parsed.username:
                    # Block credentials in URL
                    return False
                return True

            return False

        except Exception:
            return False

    async def _get_repo_info(self, repo: Repo) -> Dict[str, Any]:
        """Get repository information."""
        try:
            return {
                'commit_sha': repo.head.commit.hexsha,
                'commit_message': repo.head.commit.message.strip(),
                'commit_author': str(repo.head.commit.author),
                'commit_date': repo.head.commit.committed_datetime.isoformat(),
                'branch': repo.active_branch.name if not repo.head.is_detached else None,
                'tags': [tag.name for tag in repo.tags],
                'remotes': [remote.url for remote in repo.remotes],
                'is_dirty': repo.is_dirty(),
                'untracked_files': len(repo.untracked_files)
            }
        except Exception as e:
            logger.warning("git.info_error", error=str(e))
            return {}

    async def check_repo_size(self, repo_dir: Path) -> Tuple[bool, int]:
        """Check if repository is within size limit."""
        total = 0
        file_count = 0

        try:
            for file_path in repo_dir.rglob('*'):
                if file_path.is_file():
                    try:
                        size = file_path.stat().st_size
                        total += size
                        file_count += 1

                        # Early exit if already over limit
                        if total > MAX_REPO_SIZE:
                            return False, total

                    except (OSError, PermissionError):
                        continue

            return total <= MAX_REPO_SIZE, total

        except Exception as e:
            logger.error("size_check.failed", error=str(e))
            return False, total


git_manager = GitManager()

# ---------------------------------------------------------------------------
# Enhanced File Analysis
# ---------------------------------------------------------------------------

class FileAnalyzer:
    """Enhanced file analyzer with caching and parallel processing."""

    def __init__(self):
        self._tool_cache = {}
        self._executor = ThreadPoolExecutor(max_workers=settings.max_workers)

    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash of file content."""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(65536), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    async def analyze_file(
        self,
        file_path: Path,
        repo_dir: Path,
        use_cache: bool = True
    ) -> List[Issue]:
        """Analyze a single file with caching."""
        start_time = time.monotonic()
        ext = file_path.suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            return []

        # Check cache
        if use_cache:
            file_hash = self._get_file_hash(file_path)
            if file_hash:
                cached = await self._get_cached_analysis(file_hash)
                if cached:
                    cache_hits.labels(cache_type="file").inc()
                    return cached

        # Analyze file
        try:
            issues = await self._analyze_file_with_timeout(file_path, repo_dir)

            # Cache result
            if use_cache and file_hash:
                await self._cache_analysis(file_hash, issues, file_path, repo_dir)

            # Record metrics
            duration = time.monotonic() - start_time
            file_analysis_duration.labels(language=ext.lstrip('.')).observe(duration)

            return issues

        except Exception as e:
            logger.error(
                "file.analysis_failed",
                file=str(file_path),
                error=str(e)
            )
            error_counter.labels(error_type="file_analysis", component="analyzer").inc()
            return []

    async def _analyze_file_with_timeout(
        self,
        file_path: Path,
        repo_dir: Path
    ) -> List[Issue]:
        """Analyze file with timeout."""
        try:
            return await asyncio.wait_for(
                run_in_threadpool(self._analyze_file_sync, file_path, repo_dir),
                timeout=30
            )
        except asyncio.TimeoutError:
            logger.warning("file.analysis_timeout", file=str(file_path))
            return []

    def _analyze_file_sync(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """Synchronous file analysis."""
        ext = file_path.suffix.lower()

        # Skip large files
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                logger.debug("file.skipped_large", file=str(file_path))
                return []
        except OSError:
            return []

        # Language-specific analysis
        if ext == '.py':
            return self._analyze_python(file_path, repo_dir)
        elif ext in ('.js', '.ts', '.jsx', '.tsx'):
            return self._analyze_javascript(file_path, repo_dir)
        elif ext == '.go':
            return self._analyze_go(file_path, repo_dir)
        elif ext == '.rs':
            return self._analyze_rust(file_path, repo_dir)
        elif ext in ('.java', '.class'):
            return self._analyze_java(file_path, repo_dir)
        elif ext in ('.rb', '.erb'):
            return self._analyze_ruby(file_path, repo_dir)
        elif ext == '.php':
            return self._analyze_php(file_path, repo_dir)
        elif ext in ('.c', '.cpp', '.h', '.hpp'):
            return self._analyze_cpp(file_path, repo_dir)

        return []

    def _analyze_python(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """Python analysis with multiple tools."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # Try flake8 first
        if self._check_tool('flake8'):
            issues.extend(self._run_flake8(file_path, rel_path))
        else:
            # Fallback to regex analysis
            issues.extend(self._analyze_python_regex(file_path, rel_path))

        # Try pylint for deeper analysis
        if self._check_tool('pylint') and settings.enable_deep_analysis:
            issues.extend(self._run_pylint(file_path, rel_path))

        # Try bandit for security issues
        if self._check_tool('bandit'):
            issues.extend(self._run_bandit(file_path, rel_path))

        # Try mypy for type checking
        if self._check_tool('mypy'):
            issues.extend(self._run_mypy(file_path, rel_path))

        return issues

    def _run_flake8(self, file_path: Path, rel_path: str) -> List[Issue]:
        """Run flake8 on a Python file."""
        issues = []

        code, stdout, stderr = run_command(
            [
                'flake8',
                '--format=%(path)s:%(row)d:%(col)d:%(code)s:%(text)s',
                '--max-line-length=120',
                '--extend-ignore=E203,W503',
                str(file_path)
            ],
            cwd=str(file_path.parent),
            timeout=30
        )

        for line in stdout.splitlines():
            parts = line.split(':', 4)
            if len(parts) >= 5:
                _, row, col, code, msg = parts
                severity = 'error' if code.startswith(('E9', 'F')) else 'warning'
                issues.append(Issue(
                    file=rel_path,
                    line=int(row),
                    column=int(col),
                    type='LINTING',
                    code=code,
                    message=msg.strip(),
                    severity=severity,
                    language='python',
                    category='style' if code.startswith('E') else 'error',
                    fixable=code in self._get_fixable_codes('flake8')
                ))

        return issues

    def _run_pylint(self, file_path: Path, rel_path: str) -> List[Issue]:
        """Run pylint on a Python file."""
        issues = []

        code, stdout, stderr = run_command(
            ['pylint', '--output-format=json', str(file_path)],
            cwd=str(file_path.parent),
            timeout=60
        )

        try:
            data = json.loads(stdout)
            for msg in data:
                issues.append(Issue(
                    file=rel_path,
                    line=msg.get('line', 0),
                    column=msg.get('column', 0),
                    end_line=msg.get('endLine'),
                    end_column=msg.get('endColumn'),
                    type='LINTING',
                    code=msg.get('symbol', ''),
                    message=msg.get('message', ''),
                    severity='error' if msg.get('type') in ('error', 'fatal') else 'warning',
                    language='python',
                    category=msg.get('type', 'refactor'),
                    fixable='--fix' in msg.get('message', '')
                ))
        except (json.JSONDecodeError, KeyError):
            pass

        return issues

    def _run_bandit(self, file_path: Path, rel_path: str) -> List[Issue]:
        """Run bandit security linter."""
        issues = []

        code, stdout, stderr = run_command(
            ['bandit', '-f', 'json', str(file_path)],
            cwd=str(file_path.parent),
            timeout=30
        )

        try:
            data = json.loads(stdout)
            for result in data.get('results', []):
                issues.append(Issue(
                    file=rel_path,
                    line=result.get('line_number', 0),
                    column=0,
                    type='SECURITY',
                    code=result.get('test_id', ''),
                    message=f"{result.get('test_name')}: {result.get('issue_text', '')}",
                    severity=result.get('issue_severity', 'medium').lower(),
                    language='python',
                    category='security',
                    documentation_url=result.get('more_info')
                ))
        except (json.JSONDecodeError, KeyError):
            pass

        return issues

    def _run_mypy(self, file_path: Path, rel_path: str) -> List[Issue]:
        """Run mypy type checker."""
        issues = []

        code, stdout, stderr = run_command(
            ['mypy', '--no-color-output', str(file_path)],
            cwd=str(file_path.parent),
            timeout=30
        )

        for line in stdout.splitlines():
            match = re.match(r'(.+):(\d+):(\d+):\s+(.+?):\s+(.+)', line)
            if match:
                _, row, col, level, msg = match.groups()
                issues.append(Issue(
                    file=rel_path,
                    line=int(row),
                    column=int(col),
                    type='TYPE_CHECKING',
                    code='',
                    message=msg.strip(),
                    severity='error' if level == 'error' else 'warning',
                    language='python',
                    category='type'
                ))

        return issues

    def _analyze_python_regex(self, file_path: Path, rel_path: str) -> List[Issue]:
        """Regex-based Python analysis as fallback."""
        issues = []

        try:
            source = file_path.read_text(encoding='utf-8', errors='replace')
        except Exception:
            return issues

        lines = source.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.rstrip()

            # Line length
            if len(stripped) > 120:
                issues.append(Issue(
                    file=rel_path,
                    line=i,
                    column=121,
                    type='LINTING',
                    code='E501',
                    message=f'Line too long ({len(stripped)} > 120 characters)',
                    severity='warning',
                    language='python',
                    category='style',
                    fixable=True
                ))

            # Trailing whitespace
            if line != stripped:
                issues.append(Issue(
                    file=rel_path,
                    line=i,
                    column=len(stripped) + 1,
                    type='LINTING',
                    code='W291',
                    message='Trailing whitespace',
                    severity='warning',
                    language='python',
                    category='style',
                    fixable=True
                ))

            # Bare except
            if re.match(r'\s*except\s*:', line):
                issues.append(Issue(
                    file=rel_path,
                    line=i,
                    column=1,
                    type='LOGIC',
                    code='E722',
                    message="Do not use bare 'except'",
                    severity='error',
                    language='python',
                    category='error'
                ))

            # eval/exec
            if re.search(r'\beval\s*\(', line) or re.search(r'\bexec\s*\(', line):
                col = line.find('eval') + 1 if 'eval' in line else line.find('exec') + 1
                issues.append(Issue(
                    file=rel_path,
                    line=i,
                    column=col,
                    type='SECURITY',
                    code='S001',
                    message='Use of eval/exec is a potential security risk',
                    severity='error',
                    language='python',
                    category='security'
                ))

            # TODO/FIXME comments
            if re.search(r'#\s*(TODO|FIXME|XXX)', line, re.I):
                col = line.find('#') + 1
                issues.append(Issue(
                    file=rel_path,
                    line=i,
                    column=col,
                    type='COMMENT',
                    code='T000',
                    message='TODO/FIXME comment found',
                    severity='info',
                    language='python',
                    category='documentation'
                ))

        return issues

    def _analyze_javascript(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """JavaScript/TypeScript analysis."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # Try ESLint
        if self._check_tool('eslint'):
            code, stdout, stderr = run_command(
                ['eslint', '--format=json', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            try:
                data = json.loads(stdout)
                for file_result in data:
                    for msg in file_result.get('messages', []):
                        issues.append(Issue(
                            file=rel_path,
                            line=msg.get('line', 0),
                            column=msg.get('column', 0),
                            end_line=msg.get('endLine'),
                            end_column=msg.get('endColumn'),
                            type='LINTING',
                            code=msg.get('ruleId', ''),
                            message=msg.get('message', ''),
                            severity='error' if msg.get('severity') == 2 else 'warning',
                            language=file_path.suffix.lstrip('.'),
                            category=msg.get('ruleId', '').split('/')[0] if '/' in msg.get('ruleId', '') else 'general',
                            fixable=msg.get('fix') is not None
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        # Try Prettier for formatting issues
        if self._check_tool('prettier'):
            code, stdout, stderr = run_command(
                ['prettier', '--check', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            if code != 0:
                issues.append(Issue(
                    file=rel_path,
                    line=0,
                    column=0,
                    type='FORMATTING',
                    code='PRETTIER',
                    message='Code formatting issues detected',
                    severity='warning',
                    language=file_path.suffix.lstrip('.'),
                    category='style',
                    fixable=True
                ))

        return issues

    def _analyze_go(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """Go analysis."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # golint
        if self._check_tool('golint'):
            code, stdout, stderr = run_command(
                ['golint', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            for line in stdout.splitlines():
                match = re.match(r'(.+):(\d+):(\d+):\s+(.+)', line)
                if match:
                    _, row, col, msg = match.groups()
                    issues.append(Issue(
                        file=rel_path,
                        line=int(row),
                        column=int(col),
                        type='LINTING',
                        code='',
                        message=msg.strip(),
                        severity='warning',
                        language='go',
                        category='style'
                    ))

        # go vet
        if self._check_tool('go'):
            code, stdout, stderr = run_command(
                ['go', 'vet', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            for line in stderr.splitlines():
                match = re.match(r'(.+):(\d+):(\d+):\s+(.+)', line)
                if match:
                    _, row, col, msg = match.groups()
                    issues.append(Issue(
                        file=rel_path,
                        line=int(row),
                        column=int(col),
                        type='VET',
                        code='',
                        message=msg.strip(),
                        severity='error',
                        language='go',
                        category='compiler'
                    ))

        return issues

    def _analyze_rust(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """Rust analysis."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # cargo clippy
        if self._check_tool('cargo'):
            code, stdout, stderr = run_command(
                ['cargo', 'clippy', '--message-format=json', '--quiet'],
                cwd=str(repo_dir),
                timeout=120
            )

            for line in stderr.splitlines():
                try:
                    msg = json.loads(line)
                    if msg.get('reason') != 'compiler-message':
                        continue

                    inner = msg.get('message', {})
                    spans = inner.get('spans', [{}])
                    span = spans[0] if spans else {}

                    if not span:
                        continue

                    file_name = span.get('file_name', rel_path)
                    if Path(file_name).name != Path(rel_path).name:
                        continue

                    issues.append(Issue(
                        file=rel_path,
                        line=span.get('line_start', 0),
                        column=span.get('column_start', 0),
                        end_line=span.get('line_end'),
                        end_column=span.get('column_end'),
                        type='LINTING',
                        code=inner.get('code', {}).get('code', ''),
                        message=inner.get('message', ''),
                        severity='error' if inner.get('level') == 'error' else 'warning',
                        language='rust',
                        category=inner.get('level', 'warning')
                    ))
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

        return issues

    def _analyze_java(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """Java analysis."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # Checkstyle
        if self._check_tool('checkstyle'):
            code, stdout, stderr = run_command(
                ['checkstyle', '-c', '/sun_checks.xml', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            # Parse checkstyle XML output
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(stdout)
                for file_elem in root.findall('.//file'):
                    for error in file_elem.findall('error'):
                        issues.append(Issue(
                            file=rel_path,
                            line=int(error.get('line', 0)),
                            column=int(error.get('column', 0)),
                            type='LINTING',
                            code=error.get('source', ''),
                            message=error.get('message', ''),
                            severity=error.get('severity', 'warning'),
                            language='java',
                            category='style'
                        ))
            except (ET.ParseError, ValueError):
                pass

        return issues

    def _analyze_ruby(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """Ruby analysis."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # Rubocop
        if self._check_tool('rubocop'):
            code, stdout, stderr = run_command(
                ['rubocop', '--format', 'json', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            try:
                data = json.loads(stdout)
                for file_result in data.get('files', []):
                    for offense in file_result.get('offenses', []):
                        location = offense.get('location', {})
                        issues.append(Issue(
                            file=rel_path,
                            line=location.get('line', 0),
                            column=location.get('column', 0),
                            end_line=location.get('last_line'),
                            end_column=location.get('last_column'),
                            type='LINTING',
                            code=offense.get('cop_name', ''),
                            message=offense.get('message', ''),
                            severity=offense.get('severity', 'warning'),
                            language='ruby',
                            category='style',
                            fixable=offense.get('correctable', False)
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        return issues

    def _analyze_php(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """PHP analysis."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # PHP CodeSniffer
        if self._check_tool('phpcs'):
            code, stdout, stderr = run_command(
                ['phpcs', '--report=json', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            try:
                data = json.loads(stdout)
                files = data.get('files', {})
                for file_result in files.values():
                    for msg in file_result.get('messages', []):
                        issues.append(Issue(
                            file=rel_path,
                            line=msg.get('line', 0),
                            column=msg.get('column', 0),
                            type='LINTING',
                            code=msg.get('source', ''),
                            message=msg.get('message', ''),
                            severity=msg.get('type', 'error').lower(),
                            language='php',
                            category='style',
                            fixable=msg.get('fixable', False)
                        ))
            except (json.JSONDecodeError, KeyError):
                pass

        return issues

    def _analyze_cpp(self, file_path: Path, repo_dir: Path) -> List[Issue]:
        """C/C++ analysis."""
        issues = []
        rel_path = str(file_path.relative_to(repo_dir))

        # cppcheck
        if self._check_tool('cppcheck'):
            code, stdout, stderr = run_command(
                ['cppcheck', '--enable=all', '--xml', str(file_path)],
                cwd=str(repo_dir),
                timeout=30
            )

            # Parse cppcheck XML output
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(stdout)
                for error in root.findall('.//error'):
                    location = error.find('location')
                    if location is not None:
                        issues.append(Issue(
                            file=rel_path,
                            line=int(location.get('line', 0)),
                            column=int(location.get('column', 0)),
                            type='LINTING',
                            code=error.get('id', ''),
                            message=error.get('msg', ''),
                            severity=error.get('severity', 'warning'),
                            language=file_path.suffix.lstrip('.'),
                            category=error.get('severity', 'style')
                        ))
            except (ET.ParseError, ValueError):
                pass

        return issues

    def _check_tool(self, tool: str) -> bool:
        """Check if a tool is available with caching."""
        if tool not in self._tool_cache:
            self._tool_cache[tool] = shutil.which(tool) is not None
        return self._tool_cache[tool]

    def _get_fixable_codes(self, tool: str) -> Set[str]:
        """Get set of fixable error codes for a tool."""
        fixable = {
            'flake8': {'E111', 'E114', 'E115', 'E116', 'E117', 'E121', 'E122',
                      'E123', 'E124', 'E125', 'E126', 'E127', 'E128', 'E129',
                      'E131', 'E133', 'E201', 'E202', 'E203', 'E211', 'E221',
                      'E222', 'E223', 'E224', 'E225', 'E226', 'E227', 'E228',
                      'E231', 'E241', 'E242', 'E251', 'E252', 'E261', 'E262',
                      'E265', 'E266', 'E271', 'E272', 'E273', 'E274', 'E275'}
        }
        return fixable.get(tool, set())

    async def _get_cached_analysis(self, file_hash: str) -> Optional[List[Issue]]:
        """Get cached analysis results."""
        if not file_hash or not redis_manager.client:
            return None

        cached = await redis_manager.get_cached(f"file_analysis:{file_hash}")
        if cached:
            return [Issue(**issue) for issue in cached]
        return None

    async def _cache_analysis(
        self,
        file_hash: str,
        issues: List[Issue],
        file_path: Path,
        repo_dir: Path
    ):
        """Cache analysis results."""
        if not file_hash or not redis_manager.client:
            return

        # Don't cache if no issues
        if not issues:
            return

        # Cache for 1 hour
        await redis_manager.set_cached(
            f"file_analysis:{file_hash}",
            [issue.dict() for issue in issues],
            ttl=3600
        )


file_analyzer = FileAnalyzer()

# ---------------------------------------------------------------------------
# Enhanced Analysis Manager
# ---------------------------------------------------------------------------

class AnalysisManager:
    """Manages analysis jobs with queueing and prioritization."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=settings.worker_queue_size)
        self._workers: List[asyncio.Task] = []
        self._active_jobs: Dict[int, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._scheduler = BackgroundScheduler(timezone=pytz.UTC)

    async def start(self):
        """Start worker pool."""
        for i in range(settings.max_workers):
            worker = asyncio.create_task(self._worker_loop(i), name=f"worker-{i}")
            self._workers.append(worker)
        logger.info("workers.started", count=settings.max_workers)

        # Start cleanup scheduler
        if settings.enable_scheduled_cleanup:
            self._scheduler.add_job(
                self._cleanup_old_jobs,
                IntervalTrigger(hours=settings.temp_dir_age_hours),
                id='cleanup_old_jobs'
            )
            self._scheduler.start()

    async def stop(self):
        """Stop worker pool."""
        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("workers.stopped")

        if self._scheduler.running:
            self._scheduler.shutdown()

    async def submit_job(self, result_id: int, request: AnalysisRequest) -> None:
        """Submit analysis job to queue."""
        await self._queue.put((result_id, request))
        logger.info("job.submitted", result_id=result_id, queue_size=self._queue.qsize())

        # Update queue status
        await db_manager.execute(
            """
            INSERT INTO analysis_queue (result_id, priority, created_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (result_id, request.priority, datetime.now(timezone.utc).isoformat(), 'queued')
        )

    async def _worker_loop(self, worker_id: int):
        """Worker loop processing jobs."""
        while True:
            try:
                result_id, request = await self._queue.get()

                # Update worker status
                async with self._lock:
                    self._active_jobs[result_id] = asyncio.current_task()

                active_analyses.inc()

                try:
                    logger.info("worker.started", worker_id=worker_id, result_id=result_id)

                    # Update queue status
                    await db_manager.execute(
                        """
                        UPDATE analysis_queue
                        SET status = ?, started_at = ?, worker_id = ?
                        WHERE result_id = ?
                        """,
                        ('processing', datetime.now(timezone.utc).isoformat(), f"worker-{worker_id}", result_id)
                    )

                    # Run analysis
                    await self._run_analysis(result_id, request)

                    # Update queue status
                    await db_manager.execute(
                        """
                        UPDATE analysis_queue
                        SET status = ?, completed_at = ?
                        WHERE result_id = ?
                        """,
                        ('completed', datetime.now(timezone.utc).isoformat(), result_id)
                    )

                except Exception as e:
                    logger.error("worker.failed", worker_id=worker_id, result_id=result_id, error=str(e))

                    # Update queue status
                    await db_manager.execute(
                        """
                        UPDATE analysis_queue
                        SET status = ?, error_msg = ?
                        WHERE result_id = ?
                        """,
                        ('failed', str(e)[:1000], result_id)
                    )

                    error_counter.labels(error_type="analysis", component="worker").inc()

                finally:
                    active_analyses.dec()
                    async with self._lock:
                        self._active_jobs.pop(result_id, None)
                    self._queue.task_done()

            except asyncio.CancelledError:
                logger.info("worker.stopped", worker_id=worker_id)
                break
            except Exception as e:
                logger.error("worker.error", worker_id=worker_id, error=str(e))
                await asyncio.sleep(1)

    async def _run_analysis(self, result_id: int, request: AnalysisRequest):
        """Run analysis for a single job."""
        start_time = time.monotonic()
        tmp_dir: Optional[Path] = None

        try:
            # Update status
            await db_manager.execute(
                "UPDATE results SET status = ?, started_at = ? WHERE id = ?",
                ('processing', datetime.now(timezone.utc).isoformat(), result_id)
            )

            # Send started webhook
            await self._send_webhook_if_needed(request.webhook, result_id, 'started', {})

            # Create temp directory
            tmp_dir = Path(tempfile.mkdtemp(prefix=f"agent_{result_id}_"))
            repo_dir = tmp_dir / "repo"

            # Clone repository
            repo_info = await git_manager.clone_repository(
                url=request.repoUrl,
                dest_path=repo_dir,
                branch=request.branch,
                tag=request.tag,
                commit_sha=request.commit_sha,
                depth=request.depth,
                submodules=request.submodules
            )

            # Check size
            within_limit, total_size = await git_manager.check_repo_size(repo_dir)
            if not within_limit:
                raise RuntimeError(
                    f"Repository exceeds size limit of {settings.max_repo_size_mb} MB "
                    f"(actual: {total_size / (1024*1024):.1f} MB)"
                )

            # Collect files
            files = await self._collect_files(repo_dir, request)

            if len(files) > settings.max_files:
                logger.warning(
                    "analysis.file_limit",
                    result_id=result_id,
                    total=len(files),
                    limit=settings.max_files
                )
                files = files[:settings.max_files]

            # Send progress webhook
            await self._send_webhook_if_needed(
                request.webhook,
                result_id,
                'progress',
                {'files_scanned': 0, 'total_files': len(files)}
            )

            # Analyze files
            all_issues = []
            for i, file_path in enumerate(files):
                issues = await file_analyzer.analyze_file(
                    file_path,
                    repo_dir,
                    use_cache=True
                )
                all_issues.extend(issues)

                # Send progress every 10 files
                if i % 10 == 0:
                    await self._send_webhook_if_needed(
                        request.webhook,
                        result_id,
                        'progress',
                        {'files_scanned': i + 1, 'total_files': len(files)}
                    )

            # Scan dependencies
            deps_issues = await self._scan_dependencies(repo_dir)
            all_issues.extend(deps_issues)

            # Build summary
            summary = self._build_summary(all_issues, files, start_time, repo_info)

            # Update database
            await db_manager.execute(
                """
                UPDATE results
                SET status = ?, summary = ?, issues = ?, completed_at = ?, duration_ms = ?,
                    git_commit_sha = ?, git_tag = ?, metadata = ?
                WHERE id = ?
                """,
                (
                    'completed',
                    json.dumps(summary, default=str),
                    json.dumps([issue.dict() for issue in all_issues], default=str),
                    datetime.now(timezone.utc).isoformat(),
                    int((time.monotonic() - start_time) * 1000),
                    repo_info.get('commit_sha'),
                    request.tag,
                    json.dumps(request.metadata),
                    result_id
                )
            )

            # Update metrics
            analysis_counter.labels(
                status='completed',
                has_issues=str(len(all_issues) > 0)
            ).inc()

            analysis_duration.labels(
                language='mixed',
                status='completed'
            ).observe(time.monotonic() - start_time)

            # Send completion webhook
            await self._send_webhook_if_needed(
                request.webhook,
                result_id,
                'completed',
                {'summary': summary, 'issues_count': len(all_issues)}
            )

            logger.info(
                "analysis.completed",
                result_id=result_id,
                issues=len(all_issues),
                files=len(files),
                duration=summary['duration_seconds']
            )

        except Exception as e:
            logger.error("analysis.failed", result_id=result_id, error=str(e))

            # Update database
            await db_manager.execute(
                """
                UPDATE results
                SET status = ?, summary = ?, completed_at = ?, duration_ms = ?
                WHERE id = ?
                """,
                (
                    'failed',
                    json.dumps({'error': str(e)}),
                    datetime.now(timezone.utc).isoformat(),
                    int((time.monotonic() - start_time) * 1000),
                    result_id
                )
            )

            # Update metrics
            analysis_counter.labels(status='failed', has_issues='false').inc()

            # Send failure webhook
            await self._send_webhook_if_needed(
                request.webhook,
                result_id,
                'failed',
                {'error': str(e)}
            )

            raise

        finally:
            # Cleanup
            if tmp_dir and settings.cleanup_temp_dirs:
                try:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning("cleanup.failed", tmp_dir=str(tmp_dir), error=str(e))

    async def _collect_files(self, repo_dir: Path, request: AnalysisRequest) -> List[Path]:
        """Collect files for analysis with pattern filtering."""
        files = []

        for file_path in repo_dir.rglob('*'):
            if not file_path.is_file():
                continue

            # Skip .git directory
            if '.git' in file_path.parts:
                continue

            # Check extension
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue

            # Check size
            try:
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    continue
            except OSError:
                continue

            # Get relative path for pattern matching
            rel_path = str(file_path.relative_to(repo_dir))

            # Apply exclude patterns
            if request.exclude_patterns:
                excluded = False
                for pattern in request.exclude_patterns:
                    if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                        excluded = True
                        break
                if excluded:
                    continue

            # Apply include patterns (if specified)
            if request.include_patterns:
                included = False
                for pattern in request.include_patterns:
                    if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(file_path.name, pattern):
                        included = True
                        break
                if not included:
                    continue

            files.append(file_path)

        return files

    async def _scan_dependencies(self, repo_dir: Path) -> List[Issue]:
        """Scan dependencies for vulnerabilities."""
        issues = []

        # Python dependencies
        req_files = list(repo_dir.glob('requirements*.txt')) + list(repo_dir.glob('Pipfile*'))
        for req_file in req_files:
            if req_file.exists():
                issues.extend(await self._scan_python_deps(req_file))

        # JavaScript dependencies
        package_files = list(repo_dir.glob('package*.json'))
        for package_file in package_files:
            if package_file.exists():
                issues.extend(await self._scan_js_deps(package_file))

        # Go dependencies
        go_mod = repo_dir / 'go.mod'
        if go_mod.exists():
            issues.extend(await self._scan_go_deps(go_mod))

        return issues

    async def _scan_python_deps(self, req_file: Path) -> List[Issue]:
        """Scan Python dependencies using safety."""
        issues = []

        if not shutil.which('safety'):
            return issues

        # Run safety check
        code, stdout, stderr = await asyncio.to_thread(
            run_command,
            ['safety', 'check', '-r', str(req_file), '--json'],
            cwd=str(req_file.parent),
            timeout=60
        )

        try:
            data = json.loads(stdout)
            for vuln in data:
                if isinstance(vuln, list) and len(vuln) >= 4:
                    issues.append(Issue(
                        file=req_file.name,
                        line=0,
                        column=0,
                        type='SECURITY',
                        code=str(vuln[4]) if len(vuln) > 4 else '',
                        message=f"{vuln[0]} {vuln[2]}: {vuln[3]}",
                        severity='error',
                        language='python',
                        category='dependency',
                        documentation_url=f"https://safety.readthedocs.io/en/latest/{vuln[4]}" if len(vuln) > 4 else None
                    ))
        except (json.JSONDecodeError, IndexError):
            pass

        return issues

    async def _scan_js_deps(self, package_file: Path) -> List[Issue]:
        """Scan JavaScript dependencies using npm audit."""
        issues = []

        if not shutil.which('npm'):
            return issues

        # Run npm audit
        code, stdout, stderr = await asyncio.to_thread(
            run_command,
            ['npm', 'audit', '--json'],
            cwd=str(package_file.parent),
            timeout=60
        )

        try:
            data = json.loads(stdout)
            vulnerabilities = data.get('vulnerabilities', {})

            for pkg, info in vulnerabilities.items():
                if info.get('severity') in ['high', 'critical']:
                    issues.append(Issue(
                        file=package_file.name,
                        line=0,
                        column=0,
                        type='SECURITY',
                        code=info.get('cves', [''])[0] if info.get('cves') else '',
                        message=f"{pkg}: {info.get('severity', 'unknown')} severity - {info.get('title', '')}",
                        severity='error' if info.get('severity') == 'critical' else 'warning',
                        language='javascript',
                        category='dependency',
                        documentation_url=info.get('url', '')
                    ))
        except (json.JSONDecodeError, KeyError):
            pass

        return issues

    async def _scan_go_deps(self, go_mod: Path) -> List[Issue]:
        """Scan Go dependencies using govulncheck."""
        issues = []

        if not shutil.which('govulncheck'):
            return issues

        # Run govulncheck
        code, stdout, stderr = await asyncio.to_thread(
            run_command,
            ['govulncheck', '-json', './...'],
            cwd=str(go_mod.parent),
            timeout=120
        )

        try:
            data = json.loads(stdout)
            for vuln in data.get('Vulns', []):
                issues.append(Issue(
                    file='go.mod',
                    line=0,
                    column=0,
                    type='SECURITY',
                    code=vuln.get('ID', ''),
                    message=f"{vuln.get('PkgPath', '')}: {vuln.get('Title', '')}",
                    severity='error',
                    language='go',
                    category='dependency',
                    documentation_url=vuln.get('URL', '')
                ))
        except (json.JSONDecodeError, KeyError):
            pass

        return issues

    def _build_summary(
        self,
        issues: List[Issue],
        files: List[Path],
        start_time: float,
        repo_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build analysis summary."""
        by_lang: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_category: Dict[str, int] = {}

        for issue in issues:
            by_lang[issue.language] = by_lang.get(issue.language, 0) + 1
            by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
            by_type[issue.type] = by_type.get(issue.type, 0) + 1
            by_category[issue.category] = by_category.get(issue.category, 0) + 1

        return {
            'total_files_scanned': len(files),
            'total_issues': len(issues),
            'issues_by_language': by_lang,
            'issues_by_severity': by_severity,
            'issues_by_type': by_type,
            'issues_by_category': by_category,
            'duration_seconds': round(time.monotonic() - start_time, 2),
            'fixable_issues': sum(1 for i in issues if i.fixable),
            'repo_info': repo_info
        }

    async def _send_webhook_if_needed(
        self,
        webhook: Optional[WebhookConfig],
        result_id: int,
        event: str,
        payload: Dict[str, Any]
    ):
        """Send webhook if configured for this event."""
        if not webhook or event not in webhook.events:
            return

        try:
            await webhook_sender.send_webhook(webhook, payload, result_id, event)
        except Exception as e:
            logger.warning("webhook.send_failed", result_id=result_id, event=event, error=str(e))

    async def _cleanup_old_jobs(self):
        """Clean up old temporary directories."""
        try:
            temp_base = Path(tempfile.gettempdir())
            pattern = 'agent_*'

            for temp_dir in temp_base.glob(pattern):
                if not temp_dir.is_dir():
                    continue

                # Check age
                mtime = temp_dir.stat().st_mtime
                age_hours = (time.time() - mtime) / 3600

                if age_hours > settings.temp_dir_age_hours:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.info("cleanup.removed", dir=str(temp_dir), age_hours=round(age_hours, 1))

        except Exception as e:
            logger.error("cleanup.failed", error=str(e))

    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def get_active_jobs(self) -> List[int]:
        """Get list of active job IDs."""
        return list(self._active_jobs.keys())


analysis_manager = AnalysisManager()

# ---------------------------------------------------------------------------
# Command runner (enhanced)
# ---------------------------------------------------------------------------

def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    timeout: int = 60,
    env: Optional[Dict[str, str]] = None,
    shell: bool = False,
) -> Tuple[int, str, str]:
    """
    Run a subprocess command safely with enhanced options.
    Returns (returncode, stdout, stderr).
    """
    # Security: never use shell=True unless explicitly required
    if shell:
        # Sanitize command when using shell
        cmd_str = ' '.join(cmd)
        if re.search(r'[;&|`$()<>"\'\\]', cmd_str):
            logger.error("command.insecure_shell", cmd=cmd_str)
            return -1, "", "Insecure shell command blocked"

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                'PATH': os.environ.get('PATH', ''),
                'PYTHONIOENCODING': 'utf-8',
                **(env or {})
            },
            shell=shell,
            check=False
        )

        # Truncate output if too large
        max_output = 10000
        stdout = result.stdout[:max_output] + ('...' if len(result.stdout) > max_output else '')
        stderr = result.stderr[:max_output] + ('...' if len(result.stderr) > max_output else '')

        return result.returncode, stdout, stderr

    except subprocess.TimeoutExpired:
        logger.warning("command.timeout", cmd=cmd[0], timeout=timeout)
        return -1, "", f"Command timed out after {timeout}s"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except PermissionError:
        return -1, "", f"Permission denied: {cmd[0]}"
    except Exception as e:
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# FastAPI app with enhanced lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enhanced lifespan context manager."""
    logger.info(
        "app.starting",
        version="3.1.0",
        host=settings.host,
        port=settings.port
    )

    # Initialize components
    redis_manager.connect()
    await analysis_manager.start()

    # Track background tasks
    app.state.background_tasks = set()

    yield

    logger.info("app.shutting_down")

    # Stop analysis manager
    await analysis_manager.stop()

    # Close webhook sender
    await webhook_sender.close()

    # Cancel tracked background tasks
    for task in list(app.state.background_tasks):
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning("task.cancellation_error", error=str(e))

    # Close Redis connection
    redis_manager.close()

    logger.info("app.shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title="Code Analysis Agent",
    version="3.1.0",
    description="Enterprise-grade automated repository linting and issue detection service.",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = set(settings.supported_extensions)

SUPPORTED_LANGUAGES = {
    '.py': {
        'name': 'Python',
        'linter': 'flake8',
        'formatter': 'black',
        'tools': ['flake8', 'pylint', 'bandit', 'mypy', 'safety']
    },
    '.js': {
        'name': 'JavaScript',
        'linter': 'eslint',
        'formatter': 'prettier',
        'tools': ['eslint', 'prettier', 'npm']
    },
    '.ts': {
        'name': 'TypeScript',
        'linter': 'eslint',
        'formatter': 'prettier',
        'tools': ['eslint', 'prettier', 'tsc', 'npm']
    },
    '.jsx': {
        'name': 'React JSX',
        'linter': 'eslint',
        'formatter': 'prettier',
        'tools': ['eslint', 'prettier', 'npm']
    },
    '.tsx': {
        'name': 'React TSX',
        'linter': 'eslint',
        'formatter': 'prettier',
        'tools': ['eslint', 'prettier', 'tsc', 'npm']
    },
    '.go': {
        'name': 'Go',
        'linter': 'golint',
        'formatter': 'gofmt',
        'tools': ['golint', 'go', 'govulncheck']
    },
    '.rs': {
        'name': 'Rust',
        'linter': 'clippy',
        'formatter': 'rustfmt',
        'tools': ['cargo', 'clippy', 'rustfmt']
    },
    '.java': {
        'name': 'Java',
        'linter': 'checkstyle',
        'formatter': 'google-java-format',
        'tools': ['checkstyle', 'java']
    },
    '.rb': {
        'name': 'Ruby',
        'linter': 'rubocop',
        'formatter': 'rubocop',
        'tools': ['rubocop', 'bundler']
    },
    '.php': {
        'name': 'PHP',
        'linter': 'phpcs',
        'formatter': 'phpcbf',
        'tools': ['phpcs', 'phpcbf', 'composer']
    },
    '.c': {
        'name': 'C',
        'linter': 'cppcheck',
        'formatter': 'clang-format',
        'tools': ['cppcheck', 'clang-format', 'gcc']
    },
    '.cpp': {
        'name': 'C++',
        'linter': 'cppcheck',
        'formatter': 'clang-format',
        'tools': ['cppcheck', 'clang-format', 'g++']
    },
    '.h': {
        'name': 'C Header',
        'linter': 'cppcheck',
        'formatter': 'clang-format',
        'tools': ['cppcheck', 'clang-format']
    },
    '.hpp': {
        'name': 'C++ Header',
        'linter': 'cppcheck',
        'formatter': 'clang-format',
        'tools': ['cppcheck', 'clang-format']
    },
}

# ---------------------------------------------------------------------------
# API endpoints (enhanced)
# ---------------------------------------------------------------------------


@app.post("/api/v1/analyze", status_code=202)
async def analyze_repository(
    request_body: AnalysisRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    _=Depends(require_auth),
):
    """
    Submit a repository for analysis.
    Returns immediately with the result ID; poll /api/v1/results/{id} for completion.
    """
    # Rate limiting
    client_ip = req.client.host if req.client else "unknown"
    await rate_limiter.check_rate_limit(client_ip)

    # Check cache for recent identical analysis
    if redis_manager.client:
        cache_key = f"repo:{hashlib.sha256(f'{request_body.repoUrl}:{request_body.branch}:{request_body.tag}:{request_body.commit_sha}'.encode()).hexdigest()}"
        cached = await redis_manager.get_cached(cache_key)
        if cached:
            logger.info("cache.hit", repo_url=request_body.repoUrl)
            cache_hits.labels(cache_type="repo").inc()
            return JSONResponse(
                status_code=202,
                content={
                    "cached": True,
                    "data": cached
                },
            )

    # Create result record
    result_id = await db_manager.execute(
        """
        INSERT INTO results (repo_url, team_name, leader_name, branch_name, tag, status, created_at, updated_at, webhook_url, metadata)
        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        RETURNING id
        """,
        (
            request_body.repoUrl,
            request_body.teamName,
            request_body.leaderName,
            request_body.branch,
            request_body.tag,
            datetime.now(timezone.utc).isoformat(),
            datetime.now(timezone.utc).isoformat(),
            json.dumps(request_body.webhook.dict()) if request_body.webhook else None,
            json.dumps(request_body.metadata)
        )
    )

    # Submit to analysis queue
    await analysis_manager.submit_job(result_id, request_body)

    # Get created record
    row = await db_manager.fetch_one("SELECT * FROM results WHERE id = ?", (result_id,))

    return JSONResponse(
        status_code=202,
        content=_deserialise_row(row)
    )


@app.post("/api/v1/batch-analyze", status_code=202)
async def batch_analyze(
    request_body: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    _=Depends(require_auth),
):
    """Submit multiple repositories for analysis."""
    client_ip = req.client.host if req.client else "unknown"
    await rate_limiter.check_rate_limit(client_ip)

    result_ids = []
    failed = []

    for i, analysis_req in enumerate(request_body.requests):
        try:
            # Create result record
            result_id = await db_manager.execute(
                """
                INSERT INTO results (repo_url, team_name, leader_name, branch_name, tag, status, created_at, updated_at, webhook_url, metadata)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    analysis_req.repoUrl,
                    analysis_req.teamName,
                    analysis_req.leaderName,
                    analysis_req.branch,
                    analysis_req.tag,
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(request_body.webhook.dict()) if request_body.webhook else None,
                    json.dumps(analysis_req.metadata)
                )
            )

            # Use batch webhook if none provided
            webhook = analysis_req.webhook or request_body.webhook
            if webhook:
                analysis_req.webhook = webhook

            # Submit to queue
            await analysis_manager.submit_job(result_id, analysis_req)
            result_ids.append(result_id)

        except Exception as e:
            logger.error("batch.submission_failed", index=i, error=str(e))
            failed.append({"index": i, "error": str(e)})

            if not request_body.continue_on_error:
                break

    return {
        "result_ids": result_ids,
        "count": len(result_ids),
        "failed": failed,
        "parallel": request_body.parallel,
        "status": "processing",
    }


@app.get("/api/v1/results", response_model=Dict[str, Any])
async def list_results(
    req: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
    team: Optional[str] = Query(None, description="Filter by team name"),
    repo_url: Optional[str] = Query(None, description="Filter by repository URL"),
    from_date: Optional[datetime] = Query(None, description="From date"),
    to_date: Optional[datetime] = Query(None, description="To date"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _=Depends(require_auth),
):
    """List analysis results with enhanced filtering."""
    conditions = []
    params = []

    if status:
        conditions.append("status = ?")
        params.append(status)

    if team:
        conditions.append("team_name LIKE ?")
        params.append(f"%{team}%")

    if repo_url:
        conditions.append("repo_url LIKE ?")
        params.append(f"%{repo_url}%")

    if from_date:
        conditions.append("created_at >= ?")
        params.append(from_date.isoformat())

    if to_date:
        conditions.append("created_at <= ?")
        params.append(to_date.isoformat())

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count
    total_row = await db_manager.fetch_one(
        f"SELECT COUNT(*) as count FROM results {where}",
        tuple(params)
    )
    total = total_row["count"] if total_row else 0

    # Get paginated results
    rows = await db_manager.fetch_all(
        f"SELECT * FROM results {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset)
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_deserialise_row(r) for r in rows],
    }


@app.get("/api/v1/results/{result_id}", response_model=AnalysisResult)
async def get_result(
    result_id: int,
    req: Request,
    _=Depends(require_auth),
):
    """Get a specific analysis result by ID."""
    # Check cache
    if redis_manager.client:
        cached = await redis_manager.get_cached(f"analysis:{result_id}")
        if cached:
            cache_hits.labels(cache_type="analysis").inc()
            return cached

    row = await db_manager.fetch_one("SELECT * FROM results WHERE id = ?", (result_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Result not found.")

    result = _deserialise_row(row)

    # Cache completed results
    if redis_manager.client and row.get("status") == "completed":
        await redis_manager.set_cached(f"analysis:{result_id}", result)

    return result


@app.delete("/api/v1/results/{result_id}", status_code=204)
async def delete_result(
    result_id: int,
    req: Request,
    _=Depends(require_auth),
):
    """Delete a result record."""
    row = await db_manager.fetch_one("SELECT status FROM results WHERE id = ?", (result_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Result not found.")

    if row["status"] in ("pending", "processing"):
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an active analysis. Cancel it first."
        )

    await db_manager.execute("DELETE FROM results WHERE id = ?", (result_id,))

    # Clear cache
    if redis_manager.client:
        await redis_manager.set_cached(f"analysis:{result_id}", None, ttl=1)


@app.post("/api/v1/results/{result_id}/cancel", status_code=202)
async def cancel_analysis(
    result_id: int,
    req: Request,
    _=Depends(require_auth),
):
    """Cancel a running analysis."""
    row = await db_manager.fetch_one("SELECT status FROM results WHERE id = ?", (result_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Result not found.")

    if row["status"] not in ("pending", "processing"):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel analysis with status: {row['status']}"
        )

    # Update status
    await db_manager.execute(
        "UPDATE results SET status = ?, summary = ? WHERE id = ?",
        ('cancelled', json.dumps({'error': 'Cancelled by user'}), result_id)
    )

    return {"status": "cancelled", "result_id": result_id}


@app.get("/api/v1/health", response_model=HealthCheck)
async def health_check():
    """Enhanced health check endpoint."""
    db_ok = True
    redis_ok = False

    try:
        await db_manager.fetch_one("SELECT 1")
    except Exception as e:
        db_ok = False
        logger.error("health.db_failed", error=str(e))
        error_counter.labels(error_type="health_db", component="health").inc()

    if redis_manager.client:
        try:
            redis_manager.client.ping()
            redis_ok = True
        except Exception as e:
            redis_ok = False
            logger.error("health.redis_failed", error=str(e))
            error_counter.labels(error_type="health_redis", component="health").inc()

    # Check disk space
    disk = shutil.disk_usage(settings.db_path)
    disk_free_gb = disk.free / (1024**3)

    return {
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "3.1.0",
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else ("error" if redis_manager.client else "disabled"),
        "disk_space": {
            "free_gb": round(disk_free_gb, 2),
            "total_gb": round(disk.total / (1024**3), 2),
            "usage_percent": round((disk.used / disk.total) * 100, 2)
        },
        "active_analyses": active_analyses._value.get() if active_analyses else 0,
        "queue_size": analysis_manager.get_queue_size(),
        "tools": {
            lang: file_analyzer._check_tool(info['linter'])
            for lang, info in SUPPORTED_LANGUAGES.items()
        },
        "config": {
            "rate_limit_rpm": settings.rate_limit_rpm,
            "max_files_per_repo": settings.max_files,
            "max_repo_size_mb": settings.max_repo_size_mb,
            "max_workers": settings.max_workers,
            "queue_size": settings.worker_queue_size,
            "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        },
    }


@app.get("/api/v1/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats(
    req: Request,
    days: int = Query(30, ge=1, le=365),
    _=Depends(require_auth),
):
    """Get enhanced analysis statistics."""
    # Get basic stats
    total = await db_manager.fetch_one("SELECT COUNT(*) as count FROM results")

    status_counts = {}
    rows = await db_manager.fetch_all(
        "SELECT status, COUNT(*) as count FROM results GROUP BY status"
    )
    for row in rows:
        status_counts[row["status"]] = row["count"]

    # Get issues stats
    issues_row = await db_manager.fetch_one("""
        SELECT
            SUM(json_array_length(issues)) as total_issues,
            AVG(json_array_length(issues)) as avg_issues,
            AVG(duration_ms) as avg_duration
        FROM results
        WHERE status = 'completed' AND issues IS NOT NULL
    """)

    # Get top issue types
    issue_types = await db_manager.fetch_all("""
        SELECT
            json_extract(value, '$.type') as issue_type,
            COUNT(*) as count
        FROM results, json_each(issues)
        WHERE status = 'completed' AND issues IS NOT NULL
        GROUP BY issue_type
        ORDER BY count DESC
        LIMIT 10
    """)

    # Get top languages
    languages = await db_manager.fetch_all("""
        SELECT
            json_extract(value, '$.language') as language,
            COUNT(*) as count
        FROM results, json_each(issues)
        WHERE status = 'completed' AND issues IS NOT NULL
        GROUP BY language
        ORDER BY count DESC
        LIMIT 10
    """)

    # Get trend (last 7 days)
    trend = await db_manager.fetch_all("""
        SELECT
            date(created_at) as day,
            COUNT(*) as count,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
        FROM results
        WHERE created_at >= date('now', ?)
        GROUP BY date(created_at)
        ORDER BY day DESC
        LIMIT 30
    """, (f'-{days} days',))

    return {
        "total_analyses": total["count"] if total else 0,
        "status_breakdown": status_counts,
        "total_issues": issues_row["total_issues"] if issues_row and issues_row["total_issues"] else 0,
        "avg_issues_per_repo": round(issues_row["avg_issues"], 2) if issues_row and issues_row["avg_issues"] else 0,
        "active_analyses": active_analyses._value.get() if active_analyses else 0,
        "queue_size": analysis_manager.get_queue_size(),
        "avg_duration_ms": round(issues_row["avg_duration"], 2) if issues_row and issues_row["avg_duration"] else None,
        "top_issue_types": [{"type": r["issue_type"], "count": r["count"]} for r in issue_types],
        "top_languages": [{"language": r["language"], "count": r["count"]} for r in languages],
        "analyses_trend": [{"date": r["day"], "total": r["count"], "completed": r["completed"]} for r in trend],
    }


@app.post("/api/v1/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    request_body: ApiKeyCreate,
    req: Request,
    _=Depends(require_auth),
):
    """Create a new API key (admin only)."""
    # Check if requester is admin (simplified - in production, check permissions)
    if not hasattr(req.state, 'permissions') or 'admin' not in req.state.permissions:
        raise HTTPException(status_code=403, detail="Admin permission required")

    api_key = await auth_manager.create_api_key(
        request_body.team_name,
        request_body.expires_in_days,
        request_body.permissions
    )

    expires_at = None
    if request_body.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request_body.expires_in_days)

    return {
        "key": api_key,
        "team_name": request_body.team_name,
        "created_at": datetime.now(timezone.utc),
        "expires_at": expires_at,
    }


@app.delete("/api/v1/api-keys/{key_hash}")
async def revoke_api_key(
    key_hash: str,
    req: Request,
    _=Depends(require_auth),
):
    """Revoke an API key (admin only)."""
    if not hasattr(req.state, 'permissions') or 'admin' not in req.state.permissions:
        raise HTTPException(status_code=403, detail="Admin permission required")

    await auth_manager.revoke_api_key(key_hash)
    return {"status": "revoked"}


@app.get("/api/v1/queue")
async def get_queue_status(
    req: Request,
    _=Depends(require_auth),
):
    """Get analysis queue status."""
    queued = await db_manager.fetch_all(
        "SELECT * FROM analysis_queue WHERE status = 'queued' ORDER BY priority DESC, created_at ASC LIMIT 100"
    )

    processing = await db_manager.fetch_all(
        "SELECT * FROM analysis_queue WHERE status = 'processing'"
    )

    return {
        "queue_size": analysis_manager.get_queue_size(),
        "queued_count": len(queued),
        "processing_count": len(processing),
        "active_jobs": analysis_manager.get_active_jobs(),
        "queued_jobs": [dict(r) for r in queued],
        "processing_jobs": [dict(r) for r in processing],
    }


@app.post("/api/v1/webhooks/test")
async def test_webhook(
    webhook: WebhookConfig,
    req: Request,
    _=Depends(require_auth),
):
    """Test webhook configuration."""
    try:
        result = await webhook_sender.send_webhook(
            webhook,
            {"test": True, "message": "Test webhook"},
            0,
            "test"
        )
        return {"success": result, "message": "Webhook delivered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook failed: {str(e)}")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(req: Request, exc: HTTPException):
    """HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(ValueError)
async def value_error_handler(req: Request, exc: ValueError):
    """Value error handler."""
    logger.warning("validation.error", path=req.url.path, error=str(exc))
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(req: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        path=req.url.path,
        method=req.method,
        error=str(exc),
        exc_info=True,
    )
    error_counter.labels(error_type="unhandled", component="api").inc()

    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _deserialise_row(row: Dict) -> Dict:
    """Parse JSON columns back into objects."""
    result = dict(row)

    for col in ("summary", "issues", "webhook_url", "metadata"):
        if result.get(col) and isinstance(result[col], str):
            try:
                result[col] = json.loads(result[col])
            except (json.JSONDecodeError, TypeError):
                pass

    # Parse datetime fields
    for col in ("created_at", "updated_at", "started_at", "completed_at"):
        if result.get(col) and isinstance(result[col], str):
            try:
                result[col] = datetime.fromisoformat(result[col])
            except (ValueError, TypeError):
                pass

    return result


def get_module_name() -> str:
    """Determine the module name for uvicorn."""
    import __main__

    try:
        if hasattr(__main__, "__file__") and __main__.__file__:
            return Path(__main__.__file__).stem
    except Exception:
        pass

    try:
        if sys.argv and sys.argv[0] and sys.argv[0] != "-c":
            return Path(sys.argv[0]).stem
    except Exception:
        pass

    return "main"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    module_name = get_module_name()

    print(f"\n{'='*60}")
    print(f"Code Analysis Agent v3.1.0")
    print(f"{'='*60}")
    print(f"Server: http://{settings.host}:{settings.port}")
    print(f"Docs:   http://{settings.host}:{settings.port}/api/docs")
    print(f"Health: http://{settings.host}:{settings.port}/api/v1/health")
    print(f"{'='*60}\n")

    print(f"Configuration:")
    print(f"  Database: {settings.db_path}")
    print(f"  Redis: {'enabled' if redis_manager.client else 'disabled'}")
    print(f"  Max workers: {settings.max_workers}")
    print(f"  Rate limit: {settings.rate_limit_rpm} requests/minute")
    print(f"  Max repo size: {settings.max_repo_size_mb} MB")
    print(f"  Max files: {settings.max_files}")
    print(f"{'='*60}\n")

    # Run with uvicorn
    uvicorn.run(
        f"{module_name}:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        workers=settings.workers,
        limit_max_requests=settings.max_request_size,
        timeout_keep_alive=30,
    )

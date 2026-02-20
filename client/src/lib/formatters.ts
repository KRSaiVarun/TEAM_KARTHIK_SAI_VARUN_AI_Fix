/**
 * Formatting utilities for consistent output across the system
 */

export interface BugInfo {
  filePath: string;
  lineNumber: number;
  bugType: string;
  errorMessage: string;
  fixApplied: string;
}

/**
 * Format bug output EXACTLY as specified:
 * Input: src/utils.py — Line 15: Unused import 'os'
 * Output: LINTING error in src/utils.py line 15 → Fix: remove the import statement
 *
 * Rules:
 * - Must match wording exactly
 * - Must include arrow symbol →
 * - Must include lowercase "line"
 * - Must include file path
 */
export function formatBugOutput(bug: BugInfo): string {
  const { filePath, lineNumber, bugType, fixApplied } = bug;

  // Format: BUGTYPE error in filepath line number → Fix: fix_applied
  return `${bugType} error in ${filePath} line ${lineNumber} → Fix: ${fixApplied}`;
}

/**
 * Parse bug input and format to output
 * Input format: "src/utils.py — Line 15: Unused import 'os'"
 * Output format: "LINTING error in src/utils.py line 15 → Fix: remove the import statement"
 */
export function parseBugInput(
  input: string,
  bugType: string,
  fixApplied: string,
): string {
  try {
    // Parse: "filepath — Line number: message"
    const match = /^(.+?)\s*—\s*Line\s+(\d+):/i.exec(input);

    if (!match) {
      console.warn(`Failed to parse bug input: ${input}`);
      return input;
    }

    const filePath = match[1].trim();
    const lineNumber = Number.parseInt(match[2], 10);

    return formatBugOutput({
      filePath,
      lineNumber,
      bugType,
      errorMessage: input,
      fixApplied,
    });
  } catch (error) {
    console.error("Error formatting bug output:", error);
    return input;
  }
}

/**
 * Generate branch name using EXACT format:
 * TEAM_NAME_LEADER_NAME_AI_Fix
 */
export function generateBranchName(
  teamName: string,
  leaderName: string,
): string {
  // Remove special characters and spaces, convert to uppercase
  const cleanTeam = teamName
    .toUpperCase()
    .replaceAll(/\s+/g, "_")
    .replaceAll(/[^A-Z0-9_]/g, "");

  const cleanLeader = leaderName
    .toUpperCase()
    .replaceAll(/\s+/g, "_")
    .replaceAll(/[^A-Z0-9_]/g, "");

  return `${cleanTeam}_${cleanLeader}_AI_Fix`;
}

/**
 * Format duration from milliseconds to readable format
 * Example: 125000 → "2m 5s"
 */
export function formatDuration(ms: number): string {
  if (!ms || ms < 0) return "0s";

  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  }

  if (minutes > 0) {
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }

  return `${seconds}s`;
}

/**
 * Format timestamp to readable format
 * Example: "2026-02-20T14:30:45.000Z" → "Feb 20, 2:30 PM"
 */
export function formatTimestamp(timestamp: string | Date): string {
  const date = typeof timestamp === "string" ? new Date(timestamp) : timestamp;

  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    hour12: true,
  });
}

/**
 * Calculate time difference between two timestamps
 * Returns { hours, minutes, seconds, totalMs }
 */
export function calculateTimeDifference(
  startTime: string | Date,
  endTime: string | Date,
): {
  hours: number;
  minutes: number;
  seconds: number;
  totalMs: number;
  formatted: string;
} {
  const start = typeof startTime === "string" ? new Date(startTime) : startTime;
  const end = typeof endTime === "string" ? new Date(endTime) : endTime;

  const totalMs = Math.max(0, end.getTime() - start.getTime());
  const totalSeconds = Math.floor(totalMs / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (seconds > 0 || parts.length === 0) parts.push(`${seconds}s`);

  return {
    hours,
    minutes,
    seconds,
    totalMs,
    formatted: parts.join(" "),
  };
}

/**
 * Format percentage with decimal places
 */
export function formatPercentage(
  current: number,
  total: number,
  decimals = 1,
): string {
  if (total === 0) return "0%";
  const percentage = (current / total) * 100;
  return `${percentage.toFixed(decimals)}%`;
}

/**
 * Retry counter format: "3/5" meaning 3 out of 5 retries
 */
export function formatRetryCounter(
  currentAttempt: number,
  maxRetries: number,
): string {
  return `${currentAttempt}/${maxRetries}`;
}

import { formatBugOutput } from "@/lib/formatters";
import { motion } from "framer-motion";
import {
    AlertCircle,
    CheckCircle2,
    Clock,
    Filter,
    XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "./ui/select";

interface Bug {
  id: number;
  projectId: number;
  filePath: string;
  bugType: string;
  lineNumber: number;
  errorMessage: string;
  fixApplied: string;
  status: "fixed" | "failed" | "pending";
  createdAt: string;
}

interface FixesAppliedTableProps {
  readonly bugs: Bug[];
  readonly isLoading?: boolean;
}

type BugTypeFilter =
  | "all"
  | "LINTING"
  | "SYNTAX"
  | "LOGIC"
  | "TYPE_ERROR"
  | "IMPORT"
  | "INDENTATION";
type StatusFilter = "all" | "fixed" | "failed" | "pending";

export function EnhancedFixesAppliedTable({
  bugs,
  isLoading,
}: FixesAppliedTableProps) {
  const [bugTypeFilter, setBugTypeFilter] = useState<BugTypeFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortBy, setSortBy] = useState<"status" | "type" | "file">("status");

  // Filter and sort bugs
  const filteredBugs = useMemo(() => {
    let filtered = bugs.filter((bug) => {
      const typeMatch =
        bugTypeFilter === "all" || bug.bugType === bugTypeFilter;
      const statusMatch = statusFilter === "all" || bug.status === statusFilter;
      return typeMatch && statusMatch;
    });

    // Sort
    filtered.sort((a, b) => {
      switch (sortBy) {
        case "status":
          const statusOrder = { fixed: 0, pending: 1, failed: 2 };
          return (
            statusOrder[a.status as keyof typeof statusOrder] -
            statusOrder[b.status as keyof typeof statusOrder]
          );
        case "type":
          return a.bugType.localeCompare(b.bugType);
        case "file":
          return a.filePath.localeCompare(b.filePath);
        default:
          return 0;
      }
    });

    return filtered;
  }, [bugs, bugTypeFilter, statusFilter, sortBy]);

  const stats = {
    total: bugs.length,
    fixed: bugs.filter((b) => b.status === "fixed").length,
    failed: bugs.filter((b) => b.status === "failed").length,
    pending: bugs.filter((b) => b.status === "pending").length,
  };

  const getStatusIcon = (status: Bug["status"]) => {
    switch (status) {
      case "fixed":
        return <CheckCircle2 className="w-5 h-5 text-green-400" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-400" />;
      case "pending":
        return <Clock className="w-5 h-5 text-yellow-400" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: Bug["status"]) => {
    switch (status) {
      case "fixed":
        return "success";
      case "failed":
        return "destructive";
      case "pending":
        return "secondary";
      default:
        return "outline";
    }
  };

  const getBugTypeColor = (bugType: string) => {
    switch (bugType) {
      case "LINTING":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30";
      case "SYNTAX":
        return "bg-red-500/20 text-red-400 border-red-500/30";
      case "LOGIC":
        return "bg-orange-500/20 text-orange-400 border-orange-500/30";
      case "TYPE_ERROR":
        return "bg-purple-500/20 text-purple-400 border-purple-500/30";
      case "IMPORT":
        return "bg-cyan-500/20 text-cyan-400 border-cyan-500/30";
      case "INDENTATION":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
      default:
        return "bg-gray-500/20 text-gray-400 border-gray-500/30";
    }
  };

  if (isLoading) {
    return (
      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Fixes Applied</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-12 bg-card/50 animate-pulse rounded-lg"
              />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass-card">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between mb-4">
          <CardTitle>Fixes Applied</CardTitle>
          <div className="text-xs text-muted-foreground">
            {filteredBugs.length} / {bugs.length} bugs
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-2 mb-4">
          <div className="bg-green-500/10 rounded-lg p-2 text-center">
            <p className="text-xs text-muted-foreground">Fixed</p>
            <p className="font-bold text-green-400">{stats.fixed}</p>
          </div>
          <div className="bg-yellow-500/10 rounded-lg p-2 text-center">
            <p className="text-xs text-muted-foreground">Pending</p>
            <p className="font-bold text-yellow-400">{stats.pending}</p>
          </div>
          <div className="bg-red-500/10 rounded-lg p-2 text-center">
            <p className="text-xs text-muted-foreground">Failed</p>
            <p className="font-bold text-red-400">{stats.failed}</p>
          </div>
          <div className="bg-blue-500/10 rounded-lg p-2 text-center">
            <p className="text-xs text-muted-foreground">Success Rate</p>
            <p className="font-bold text-blue-400">
              {stats.total > 0
                ? Math.round((stats.fixed / stats.total) * 100)
                : 0}
              %
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <Select
            value={bugTypeFilter}
            onValueChange={(v) => setBugTypeFilter(v as BugTypeFilter)}
          >
            <SelectTrigger className="w-32 h-8 text-xs">
              <Filter className="w-3 h-3 mr-1" />
              <SelectValue placeholder="Bug Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="LINTING">Linting</SelectItem>
              <SelectItem value="SYNTAX">Syntax</SelectItem>
              <SelectItem value="LOGIC">Logic</SelectItem>
              <SelectItem value="TYPE_ERROR">Type Error</SelectItem>
              <SelectItem value="IMPORT">Import</SelectItem>
              <SelectItem value="INDENTATION">Indentation</SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={statusFilter}
            onValueChange={(v) => setStatusFilter(v as StatusFilter)}
          >
            <SelectTrigger className="w-32 h-8 text-xs">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="fixed">Fixed</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent>
        {filteredBugs.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {bugs.length === 0
              ? "No bugs detected - Great job! ✨"
              : "No bugs match the current filters"}
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {filteredBugs.map((bug, idx) => (
              <motion.div
                key={bug.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="border border-border/50 rounded-lg p-3 bg-card/50 hover:bg-card/80 transition"
              >
                <div className="flex items-start justify-between gap-3">
                  {/* Icon and Content */}
                  <div className="flex-1 flex gap-3 min-w-0">
                    {getStatusIcon(bug.status)}
                    <div className="flex-1 min-w-0">
                      {/* Bug Type and File */}
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <Badge
                          variant="outline"
                          className={`text-xs ${getBugTypeColor(bug.bugType)}`}
                        >
                          {bug.bugType}
                        </Badge>
                        <span className="text-xs font-mono text-muted-foreground truncate">
                          {bug.filePath}
                        </span>
                      </div>

                      {/* Formatted Output - EXACT matching required */}
                      <p className="text-sm font-mono text-foreground mb-2 break-all">
                        {formatBugOutput({
                          filePath: bug.filePath,
                          lineNumber: bug.lineNumber,
                          bugType: bug.bugType,
                          errorMessage: bug.errorMessage,
                          fixApplied: bug.fixApplied,
                        })}
                      </p>

                      {/* Original error message */}
                      <p className="text-xs text-muted-foreground mb-2">
                        {bug.errorMessage}
                      </p>

                      {/* Status Badge */}
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={getStatusColor(bug.status) as any}
                          className="text-xs"
                        >
                          {bug.status.charAt(0).toUpperCase() +
                            bug.status.slice(1)}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  {/* Line Number */}
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-muted-foreground">Line</p>
                    <p className="font-mono font-bold text-primary text-lg">
                      {bug.lineNumber}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

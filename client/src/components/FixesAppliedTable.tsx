import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { type Bug } from "@shared/schema";
import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, XCircle, Zap } from "lucide-react";

interface FixesAppliedTableProps {
  bugs: Bug[];
  isLoading?: boolean;
}

const BUG_TYPE_ICONS: Record<string, React.ReactNode> = {
  LINTING: <AlertTriangle className="w-4 h-4" />,
  SYNTAX: <Zap className="w-4 h-4" />,
  LOGIC: <AlertTriangle className="w-4 h-4" />,
  TYPE_ERROR: <AlertTriangle className="w-4 h-4" />,
  IMPORT: <AlertTriangle className="w-4 h-4" />,
  INDENTATION: <AlertTriangle className="w-4 h-4" />,
};

const BUG_TYPE_COLORS: Record<string, string> = {
  LINTING: "bg-yellow-500/20 text-yellow-200 border-yellow-500/30",
  SYNTAX: "bg-red-500/20 text-red-200 border-red-500/30",
  LOGIC: "bg-orange-500/20 text-orange-200 border-orange-500/30",
  TYPE_ERROR: "bg-red-500/20 text-red-200 border-red-500/30",
  IMPORT: "bg-purple-500/20 text-purple-200 border-purple-500/30",
  INDENTATION: "bg-blue-500/20 text-blue-200 border-blue-500/30",
};

export function FixesAppliedTable({ bugs, isLoading }: FixesAppliedTableProps) {
  const sortedBugs = [...(bugs || [])].sort((a, b) => {
    // Sort by status (fixed first), then by type
    const statusOrder = { fixed: 0, pending: 1, failed: 2 };
    const aStatus = statusOrder[a.status as keyof typeof statusOrder] ?? 3;
    const bStatus = statusOrder[b.status as keyof typeof statusOrder] ?? 3;
    return aStatus - bStatus;
  });

  if (isLoading) {
    return (
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-400" />
            Fixes Applied
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-16 bg-black/40 animate-pulse rounded-lg border border-white/5"
              />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass-card overflow-hidden">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-green-400" />
            Fixes Applied
          </CardTitle>
          <Badge variant="outline" className="bg-black/40">
            {sortedBugs.length} issues
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {sortedBugs.length === 0 ? (
          <div className="text-center py-12">
            <CheckCircle2 className="w-12 h-12 text-green-500/50 mx-auto mb-3" />
            <p className="text-muted-foreground">
              No bugs detected. Great code!
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-full">
              {/* Table Header */}
              <div className="grid grid-cols-12 gap-3 px-4 py-3 bg-black/40 border-b border-white/10 sticky top-0 z-10 rounded-t-lg">
                <div className="col-span-3 text-xs font-semibold text-muted-foreground uppercase">
                  File
                </div>
                <div className="col-span-2 text-xs font-semibold text-muted-foreground uppercase">
                  Bug Type
                </div>
                <div className="col-span-1 text-xs font-semibold text-muted-foreground uppercase">
                  Line
                </div>
                <div className="col-span-3 text-xs font-semibold text-muted-foreground uppercase">
                  Commit
                </div>
                <div className="col-span-2 text-xs font-semibold text-muted-foreground uppercase text-right">
                  Status
                </div>
              </div>

              {/* Table Rows */}
              <div className="space-y-1 p-1">
                {sortedBugs.map((bug, idx) => (
                  <motion.div
                    key={bug.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className={`grid grid-cols-12 gap-3 px-4 py-3 rounded-lg border ${
                      bug.status === "fixed"
                        ? "bg-green-500/5 border-green-500/20 hover:bg-green-500/10"
                        : bug.status === "failed"
                          ? "bg-red-500/5 border-red-500/20 hover:bg-red-500/10"
                          : "bg-yellow-500/5 border-yellow-500/20 hover:bg-yellow-500/10"
                    } transition-colors group`}
                  >
                    {/* File Path */}
                    <div className="col-span-3">
                      <p
                        className="text-sm font-mono truncate"
                        title={bug.filePath}
                      >
                        {bug.filePath.split("/").pop()}
                      </p>
                      <p className="text-xs text-muted-foreground truncate mt-0.5">
                        {bug.filePath}
                      </p>
                    </div>

                    {/* Bug Type Badge */}
                    <div className="col-span-2 flex items-center">
                      <Badge
                        variant="outline"
                        className={`flex items-center gap-1.5 fonts-mono text-xs ${BUG_TYPE_COLORS[bug.bugType] || "bg-gray-500/20 text-gray-200"}`}
                      >
                        {BUG_TYPE_ICONS[bug.bugType]}
                        {bug.bugType}
                      </Badge>
                    </div>

                    {/* Line Number */}
                    <div className="col-span-1 flex items-center">
                      <span className="text-sm font-mono text-muted-foreground">
                        {bug.lineNumber || "—"}
                      </span>
                    </div>

                    {/* Commit Message / Fix Applied */}
                    <div className="col-span-3">
                      <p
                        className="text-sm text-foreground/80 truncate line-clamp-2"
                        title={bug.fixApplied || ""}
                      >
                        {bug.fixApplied || (
                          <span className="text-muted-foreground italic">
                            No fix message
                          </span>
                        )}
                      </p>
                    </div>

                    {/* Status */}
                    <div className="col-span-2 flex items-center justify-end">
                      <div className="flex items-center gap-2">
                        {bug.status === "fixed" ? (
                          <>
                            <span className="text-xs font-semibold text-green-400">
                              Fixed
                            </span>
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                          </>
                        ) : bug.status === "failed" ? (
                          <>
                            <span className="text-xs font-semibold text-red-400">
                              Failed
                            </span>
                            <XCircle className="w-4 h-4 text-red-400" />
                          </>
                        ) : (
                          <>
                            <span className="text-xs font-semibold text-yellow-400">
                              Pending
                            </span>
                            <AlertTriangle className="w-4 h-4 text-yellow-400 animate-pulse" />
                          </>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Summary Footer */}
        {sortedBugs.length > 0 && (
          <div className="mt-6 pt-4 border-t border-white/10 grid grid-cols-3 gap-4">
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">Total Issues</p>
              <p className="text-2xl font-bold">{sortedBugs.length}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">Fixed</p>
              <p className="text-2xl font-bold text-green-400">
                {sortedBugs.filter((b) => b.status === "fixed").length}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-muted-foreground mb-1">Success Rate</p>
              <p className="text-2xl font-bold text-emerald-400">
                {sortedBugs.length > 0
                  ? Math.round(
                      (sortedBugs.filter((b) => b.status === "fixed").length /
                        sortedBugs.length) *
                        100,
                    )
                  : 0}
                %
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

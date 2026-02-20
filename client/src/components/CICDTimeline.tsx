import { formatRetryCounter, formatTimestamp } from "@/lib/formatters";
import { motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Clock, XCircle } from "lucide-react";
import { Badge } from "./ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";

interface TimelineEntry {
  id: string;
  timestamp: string;
  attempt: number;
  status: "pending" | "running" | "success" | "failed";
  duration?: number;
  error?: string;
}

interface CICDTimelineProps {
  readonly timeline: TimelineEntry[];
  readonly maxRetries: number;
  readonly isLoading?: boolean;
}

export function CICDTimeline({
  timeline,
  maxRetries,
  isLoading,
}: CICDTimelineProps) {
  const getStatusIcon = (status: TimelineEntry["status"]) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="w-6 h-6 text-green-400" />;
      case "failed":
        return <XCircle className="w-6 h-6 text-red-400" />;
      case "running":
        return <Clock className="w-6 h-6 text-blue-400 animate-spin" />;
      case "pending":
        return <AlertCircle className="w-6 h-6 text-yellow-400" />;
      default:
        return <Clock className="w-6 h-6 text-gray-400" />;
    }
  };

  const getStatusColor = (status: TimelineEntry["status"]) => {
    switch (status) {
      case "success":
        return "success";
      case "failed":
        return "destructive";
      case "running":
        return "secondary";
      case "pending":
        return "outline";
      default:
        return "secondary";
    }
  };

  const getStatusLabel = (status: TimelineEntry["status"]) =>
    status.charAt(0).toUpperCase() + status.slice(1);

  if (!timeline || timeline.length === 0) {
    return (
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            CI/CD Timeline
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            {isLoading
              ? "Analysis in progress..."
              : "No timeline data available yet"}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          CI/CD Timeline
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {timeline.map((entry, idx) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="relative"
            >
              {/* Timeline line connector */}
              {idx < timeline.length - 1 && (
                <div className="absolute left-3 top-12 w-0.5 h-12 bg-gradient-to-b from-border to-transparent" />
              )}

              {/* Entry Card */}
              <div className="flex gap-4">
                {/* Icon */}
                <div className="flex-shrink-0 pt-1">
                  {getStatusIcon(entry.status)}
                </div>

                {/* Content */}
                <div className="flex-1 bg-card/50 rounded-lg p-4 border border-border/50">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-semibold">
                        Run Attempt{" "}
                        <span className="font-mono text-primary">
                          {formatRetryCounter(entry.attempt, maxRetries)}
                        </span>
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatTimestamp(entry.timestamp)}
                      </p>
                    </div>
                    <Badge variant={getStatusColor(entry.status) as any}>
                      {getStatusLabel(entry.status)}
                    </Badge>
                  </div>

                  {/* Duration */}
                  {entry.duration && (
                    <div className="mt-2 text-xs text-muted-foreground">
                      ⏱️ Duration:{" "}
                      <span className="font-mono">
                        {Math.round(entry.duration / 1000)}s
                      </span>
                    </div>
                  )}

                  {/* Error message */}
                  {entry.error && (
                    <div className="mt-2 p-2 bg-red-500/10 rounded border border-red-500/30">
                      <p className="text-xs text-red-400 font-mono">
                        {entry.error}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}

          {/* Current status indicator */}
          {isLoading && (
            <motion.div
              animate={{ opacity: [0.5, 1] }}
              transition={{ duration: 1, repeat: Infinity }}
              className="text-center text-sm text-blue-400 font-medium"
            >
              ⚙️ Analysis in progress...
            </motion.div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

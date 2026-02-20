import { Card, CardContent } from "@/components/ui/card";
import { calculateTimeDifference, formatTimestamp } from "@/lib/formatters";
import { motion } from "framer-motion";
import { Clock } from "lucide-react";

interface TotalTimeDisplayProps {
  startTime: string | Date | null;
  endTime: string | Date | null;
  isRunning?: boolean;
}

export function TotalTimeDisplay({
  startTime,
  endTime,
  isRunning = false,
}: TotalTimeDisplayProps) {
  if (!startTime) {
    return null;
  }

  // Calculate time difference
  const timeDiff = calculateTimeDifference(startTime, endTime || new Date());

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
    >
      <Card className="glass-card border-2 border-primary/30 bg-gradient-to-r from-primary/10 to-transparent">
        <CardContent className="pt-6">
          <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              <h3 className="font-semibold text-lg">Total Time Taken</h3>
              {isRunning && (
                <span className="text-xs text-blue-400 animate-pulse font-mono">
                  (running...)
                </span>
              )}
            </div>

            {/* Main Time Display */}
            <div className="text-center py-6 bg-black/40 rounded-lg border border-border/50">
              <motion.div
                animate={isRunning ? { scale: [1, 1.05, 1] } : {}}
                transition={isRunning ? { duration: 2, repeat: Infinity } : {}}
                className="text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400"
              >
                {timeDiff.formatted}
              </motion.div>
            </div>

            {/* Timeline Details */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-card/50 rounded-lg p-3 border border-border/50">
                <p className="text-xs text-muted-foreground mb-1">Start Time</p>
                <p className="text-sm font-mono text-foreground">
                  {formatTimestamp(startTime)}
                </p>
              </div>

              {endTime && (
                <div className="bg-card/50 rounded-lg p-3 border border-border/50">
                  <p className="text-xs text-muted-foreground mb-1">End Time</p>
                  <p className="text-sm font-mono text-foreground">
                    {formatTimestamp(endTime)}
                  </p>
                </div>
              )}
            </div>

            {/* Breakdown */}
            <div className="bg-black/40 rounded-lg p-4 border border-border/50">
              <p className="text-xs text-muted-foreground mb-3">
                Duration Breakdown
              </p>
              <div className="space-y-2 text-sm">
                {timeDiff.hours > 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Hours:</span>
                    <span className="font-mono font-semibold text-cyan-400">
                      {timeDiff.hours}h
                    </span>
                  </div>
                )}
                {timeDiff.minutes > 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Minutes:</span>
                    <span className="font-mono font-semibold text-cyan-400">
                      {timeDiff.minutes % 60}m
                    </span>
                  </div>
                )}
                {timeDiff.seconds >= 0 && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Seconds:</span>
                    <span className="font-mono font-semibold text-cyan-400">
                      {timeDiff.seconds % 60}s
                    </span>
                  </div>
                )}
                <div className="pt-2 border-t border-border/50 mt-2">
                  <div className="flex justify-between font-semibold">
                    <span>Total:</span>
                    <span className="font-mono text-primary">
                      {(timeDiff.totalMs / 1000).toFixed(2)}s
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

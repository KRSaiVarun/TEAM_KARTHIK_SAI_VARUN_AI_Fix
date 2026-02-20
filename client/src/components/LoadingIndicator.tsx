import { Card, CardContent } from "@/components/ui/card";
import { motion } from "framer-motion";
import { Loader2, Zap } from "lucide-react";

interface LoadingIndicatorProps {
  isLoading: boolean;
  progress?: number;
  stage?: string;
}

export function LoadingIndicator({
  isLoading,
  progress = 0,
  stage = "Initializing analysis...",
}: LoadingIndicatorProps) {
  if (!isLoading) return null;

  const stages = [
    "Cloning repository...",
    "Analyzing files...",
    "Running tests...",
    "Detecting issues...",
    "Applying fixes...",
    "Generating report...",
  ];

  const currentStageIndex = Math.floor((progress / 100) * stages.length);
  const currentStage = stages[currentStageIndex] || stage;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
    >
      <Card className="glass-card w-96 border-primary/50">
        <CardContent className="pt-8 space-y-6">
          {/* Animated Icon */}
          <div className="flex justify-center">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            >
              <Loader2 className="w-12 h-12 text-primary" />
            </motion.div>
          </div>

          {/* Stage Text */}
          <div className="text-center space-y-2">
            <h3 className="text-lg font-semibold">🤖 AI Agent Active</h3>
            <p className="text-sm text-muted-foreground">{currentStage}</p>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="w-full bg-black/40 rounded-full h-2 overflow-hidden border border-border">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5 }}
                className="h-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500"
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Progress</span>
              <span className="font-mono">{Math.round(progress)}%</span>
            </div>
          </div>

          {/* Stage Indicators */}
          <div className="flex gap-1 justify-center">
            {stages.map((_, idx) => (
              <motion.div
                key={idx}
                className={`h-1.5 w-1.5 rounded-full transition-all ${
                  idx <= currentStageIndex ? "bg-primary w-2" : "bg-border"
                }`}
                animate={
                  idx === currentStageIndex ? { scale: [1, 1.2, 1] } : {}
                }
                transition={{ duration: 1, repeat: Infinity }}
              />
            ))}
          </div>

          {/* Tip */}
          <div className="bg-blue-500/10 rounded-lg p-3 border border-blue-500/30">
            <div className="flex gap-2 items-start">
              <Zap className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-blue-300">
                The AI agent is analyzing your repository. This may take a few
                minutes depending on the repository size.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

/**
 * Standalone compact loading indicator (for inline usage)
 */
export function CompactLoadingIndicator() {
  return (
    <div className="flex items-center gap-2">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
      >
        <Loader2 className="w-4 h-4 text-primary" />
      </motion.div>
      <span className="text-sm text-muted-foreground animate-pulse">
        Analysis in progress...
      </span>
    </div>
  );
}

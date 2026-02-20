import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { motion } from "framer-motion";
import { AlertCircle, Award, BarChart3, TrendingUp, Zap } from "lucide-react";

interface EnhancedScoreBreakdownProps {
  baseScore?: number;
  completionTime?: number; // in seconds
  commitCount?: number;
  totalBugsDetected?: number;
  totalBugsFixed?: number;
}

interface ScoreComponent {
  label: string;
  value: number;
  color: string;
  percentage: number;
  type: "base" | "bonus" | "penalty";
}

export function EnhancedScoreBreakdown({
  baseScore = 100,
  completionTime = 0,
  commitCount = 0,
  totalBugsDetected = 0,
  totalBugsFixed = 0,
}: EnhancedScoreBreakdownProps) {
  // Calculate bonuses using Pure Bonus Algorithm
  const speedBonus =
    completionTime > 0 && completionTime < 180
      ? 15
      : completionTime < 300
        ? 10
        : completionTime < 600
          ? 5
          : 0;

  const commitBonus = Math.max(0, 30 - commitCount);
  const qualityBonus =
    totalBugsDetected > 0
      ? Math.round((totalBugsFixed / totalBugsDetected) * 20)
      : 0;

  const finalScore = baseScore + speedBonus + commitBonus + qualityBonus;
  const maxPossibleScore = 100 + 15 + 30 + 20; // 165

  // Build components array for chart
  const components: ScoreComponent[] = [
    {
      label: "Base Score",
      value: baseScore,
      color: "bg-blue-500",
      percentage: (baseScore / maxPossibleScore) * 100,
      type: "base",
    },
    ...(speedBonus > 0
      ? [
          {
            label: "Speed Bonus",
            value: speedBonus,
            color: "bg-green-500",
            percentage: (speedBonus / maxPossibleScore) * 100,
            type: "bonus" as const,
          },
        ]
      : []),
    ...(commitBonus > 0
      ? [
          {
            label: "Commit Bonus",
            value: commitBonus,
            color: "bg-cyan-500",
            percentage: (commitBonus / maxPossibleScore) * 100,
            type: "bonus" as const,
          },
        ]
      : []),
    ...(qualityBonus > 0
      ? [
          {
            label: "Quality Bonus",
            value: qualityBonus,
            color: "bg-purple-500",
            percentage: (qualityBonus / maxPossibleScore) * 100,
            type: "bonus" as const,
          },
        ]
      : []),
  ];

  const scorePercentage = (finalScore / maxPossibleScore) * 100;

  return (
    <div className="space-y-6">
      {/* Main Score Card */}
      <Card className="glass-card border-2 border-primary/50 overflow-hidden">
        <CardHeader className="pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Award className="w-5 h-5 text-yellow-400" />
              <CardTitle>Performance Score</CardTitle>
            </div>
            <Badge variant="outline" className="text-lg px-3 py-1">
              {completionTime > 0 &&
                `${Math.floor(completionTime / 60)}m ${completionTime % 60}s`}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Large Score Display */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", stiffness: 100 }}
            className="text-center py-8"
          >
            <div className="text-6xl font-bold bg-gradient-to-r from-yellow-400 via-orange-400 to-red-400 bg-clip-text text-transparent">
              {finalScore}
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              {scorePercentage >= 100
                ? "Perfect Score! 🎉"
                : scorePercentage >= 80
                  ? "Excellent! 🌟"
                  : "Good Progress! 📈"}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              out of {maxPossibleScore} possible points
            </p>
          </motion.div>

          {/* Horizontal Bar Chart */}
          <div className="space-y-4">
            <p className="text-sm font-semibold text-muted-foreground uppercase">
              Score Breakdown
            </p>

            {/* Stacked Bar Chart */}
            <div className="flex h-12 rounded-lg overflow-hidden border border-border bg-black/40 gap-0.5 p-0.5">
              {components.map((component, idx) => (
                <motion.div
                  key={component.label}
                  initial={{ width: 0 }}
                  animate={{ width: `${component.percentage}%` }}
                  transition={{ delay: idx * 0.1, duration: 0.5 }}
                  className={`${component.color} transition-all relative group`}
                  title={`${component.label}: ${component.value} (${component.percentage.toFixed(1)}%)`}
                >
                  <div className="hidden group-hover:flex absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 bg-black text-white text-xs px-2 py-1 rounded whitespace-nowrap z-50">
                    {component.label}: {component.value}
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Progress percentage */}
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Progress</span>
              <span className="font-mono">
                {Math.round(scorePercentage)}% of max
              </span>
            </div>
          </div>

          {/* Components Table */}
          <div className="space-y-3 pt-4 border-t border-white/10">
            <p className="text-xs font-semibold text-muted-foreground uppercase">
              Components
            </p>
            {components.map((item, idx) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="flex items-center justify-between text-sm p-3 rounded border border-border/50 bg-card/50"
              >
                <div className="flex items-center gap-3 flex-1">
                  <div className={`w-3 h-3 rounded-full ${item.color}`} />
                  <span className="text-foreground/80 font-medium">
                    {item.label}
                  </span>
                  {item.type === "bonus" && (
                    <Zap className="w-3 h-3 text-yellow-400 ml-auto mr-2" />
                  )}
                  {item.type === "penalty" && (
                    <AlertCircle className="w-3 h-3 text-red-400 ml-auto mr-2" />
                  )}
                </div>
                <span
                  className={`font-mono font-bold text-base ${
                    item.value > 0
                      ? "text-green-400"
                      : item.value < 0
                        ? "text-red-400"
                        : "text-blue-400"
                  }`}
                >
                  {item.value > 0 ? "+" : ""}
                  {item.value}
                </span>
              </motion.div>
            ))}
          </div>

          {/* Statistics Footer */}
          <div className="grid grid-cols-2 gap-3 pt-4 border-t border-white/10">
            <div className="bg-black/40 rounded-lg p-3 border border-white/5">
              <p className="text-xs text-muted-foreground mb-1">
                Issues Detected
              </p>
              <p className="text-2xl font-bold text-red-400">
                {totalBugsDetected}
              </p>
            </div>
            <div className="bg-black/40 rounded-lg p-3 border border-white/5">
              <p className="text-xs text-muted-foreground mb-1">Issues Fixed</p>
              <p className="text-2xl font-bold text-green-400">
                {totalBugsFixed}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Metrics Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Completion Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-400">
              {completionTime > 0 ? `${Math.floor(completionTime / 60)}m` : "—"}
            </p>
            {completionTime > 0 && completionTime < 180 && (
              <p className="text-xs text-green-400 mt-1">
                ⚡ +15 pts speed bonus!
              </p>
            )}
            {completionTime > 0 &&
              completionTime >= 180 &&
              completionTime < 300 && (
                <p className="text-xs text-green-400 mt-1">
                  ⚡ +10 pts speed bonus!
                </p>
              )}
            {completionTime > 0 &&
              completionTime >= 300 &&
              completionTime < 600 && (
                <p className="text-xs text-blue-400 mt-1">⏱️ +5 pts bonus</p>
              )}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Total Commits
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-purple-400">{commitCount}</p>
            {commitBonus > 0 && (
              <p className="text-xs text-green-400 mt-1">
                ✨ +{commitBonus} pts bonus!
              </p>
            )}
            {commitBonus === 0 && commitCount >= 30 && (
              <p className="text-xs text-muted-foreground mt-1">
                Max commits reached
              </p>
            )}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Award className="w-4 h-4" />
              Quality Score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-emerald-400">
              {totalBugsDetected > 0
                ? `${Math.round((totalBugsFixed / totalBugsDetected) * 100)}%`
                : "—"}
            </p>
            {qualityBonus > 0 && (
              <p className="text-xs text-green-400 mt-1">
                ✨ +{qualityBonus} pts bonus
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { motion } from "framer-motion";
import { Award, TrendingUp } from "lucide-react";

interface ScoreBreakdownProps {
  baseScore?: number;
  completionTime?: number; // in seconds
  commitCount?: number;
  totalBugsDetected?: number;
  totalBugsFixed?: number;
}

export function ScoreBreakdownPanel({
  baseScore = 100,
  completionTime = 0,
  commitCount = 0,
  totalBugsDetected = 0,
  totalBugsFixed = 0,
}: ScoreBreakdownProps) {
  // Calculate bonuses (Pure Bonus Algorithm)
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

  const scoreBreakdown = [
    { label: "Base Score", value: baseScore, color: "bg-blue-500" },
    ...(speedBonus > 0
      ? [{ label: "Speed Bonus", value: speedBonus, color: "bg-green-500" }]
      : []),
    ...(commitBonus > 0
      ? [
          {
            label: "Commit Bonus",
            value: commitBonus,
            color: "bg-cyan-500",
          },
        ]
      : []),
    ...(qualityBonus > 0
      ? [
          {
            label: "Quality Bonus",
            value: qualityBonus,
            color: "bg-purple-500",
          },
        ]
      : []),
  ];

  const maxScore = Math.max(
    ...scoreBreakdown.map((item) => Math.abs(item.value)),
  );
  const scorePercentage = (finalScore / baseScore) * 100;

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
                `${Math.round(completionTime / 60)}m ${completionTime % 60}s`}
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
                : `${Math.round(scorePercentage)}% of base score`}
            </p>
          </motion.div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Score Progress</span>
              <span>
                {finalScore}/{baseScore}
              </span>
            </div>
            <div className="w-full bg-black/40 rounded-full h-3 overflow-hidden border border-white/10">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(scorePercentage, 100)}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className={`h-full rounded-full transition-all ${
                  scorePercentage >= 100
                    ? "bg-gradient-to-r from-green-500 to-emerald-500"
                    : scorePercentage >= 80
                      ? "bg-gradient-to-r from-yellow-500 to-orange-500"
                      : "bg-gradient-to-r from-orange-500 to-red-500"
                }`}
              />
            </div>
          </div>

          {/* Breakdown Items */}
          <div className="space-y-3 pt-4 border-t border-white/10">
            <p className="text-xs font-semibold text-muted-foreground uppercase">
              Score Breakdown
            </p>
            {scoreBreakdown.map((item, idx) => (
              <motion.div
                key={item.label}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="flex items-center justify-between text-sm"
              >
                <div className="flex items-center gap-3 flex-1">
                  <div className={`w-2 h-2 rounded-full ${item.color}`} />
                  <span className="text-foreground/80">{item.label}</span>
                </div>
                <span
                  className={`font-mono font-bold ${
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
                Bugs Detected
              </p>
              <p className="text-2xl font-bold text-red-400">
                {totalBugsDetected}
              </p>
            </div>
            <div className="bg-black/40 rounded-lg p-3 border border-white/5">
              <p className="text-xs text-muted-foreground mb-1">Bugs Fixed</p>
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
            <CardTitle className="text-sm">Completion Time</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-blue-400">
              {completionTime > 0 ? `${Math.round(completionTime / 60)}m` : "—"}
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
            <CardTitle className="text-sm">Total Commits</CardTitle>
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
              <TrendingUp className="w-4 h-4" />
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
                ✨ Bonus: +{qualityBonus} pts
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

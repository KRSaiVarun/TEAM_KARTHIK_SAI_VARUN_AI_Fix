import { cn } from "@/lib/utils";
import { Loader2, CheckCircle, XCircle, Clock } from "lucide-react";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const getStatusConfig = (s: string) => {
    switch (s.toLowerCase()) {
      case "completed":
      case "fixed":
        return {
          color: "text-green-400 border-green-400/20 bg-green-400/10",
          icon: CheckCircle,
          label: "Completed",
        };
      case "failed":
        return {
          color: "text-red-400 border-red-400/20 bg-red-400/10",
          icon: XCircle,
          label: "Failed",
        };
      case "running":
        return {
          color: "text-blue-400 border-blue-400/20 bg-blue-400/10",
          icon: Loader2,
          label: "Running",
          animate: true,
        };
      case "pending":
      default:
        return {
          color: "text-yellow-400 border-yellow-400/20 bg-yellow-400/10",
          icon: Clock,
          label: "Pending",
        };
    }
  };

  const config = getStatusConfig(status);
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider",
        config.color,
        className
      )}
    >
      <Icon className={cn("w-3.5 h-3.5", config.animate && "animate-spin")} />
      {config.label}
    </div>
  );
}

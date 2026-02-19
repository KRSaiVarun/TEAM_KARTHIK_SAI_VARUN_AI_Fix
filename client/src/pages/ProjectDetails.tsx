import { useParams, Link } from "wouter";
import { useProject, useProjectBugs } from "@/hooks/use-projects";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { 
  ArrowLeft, 
  GitBranch, 
  Bug as BugIcon, 
  FileCode, 
  Terminal, 
  CheckCircle2, 
  AlertCircle,
  ExternalLink
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { format } from "date-fns";

export default function ProjectDetails() {
  const params = useParams<{ id: string }>();
  const id = parseInt(params.id || "0");
  
  const { data: project, isLoading: isProjectLoading } = useProject(id);
  const { data: bugs, isLoading: isBugsLoading } = useProjectBugs(id);

  if (isProjectLoading || !project) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-muted-foreground animate-pulse">Loading project data...</p>
        </div>
      </div>
    );
  }

  const bugStats = {
    total: bugs?.length || 0,
    fixed: bugs?.filter(b => b.status === 'fixed').length || 0,
    pending: bugs?.filter(b => b.status === 'pending').length || 0,
  };

  return (
    <div className="min-h-screen bg-background text-foreground pb-20">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm" className="gap-2">
                <ArrowLeft className="w-4 h-4" /> Back
              </Button>
            </Link>
            <div className="h-6 w-px bg-border mx-2" />
            <div className="flex flex-col">
              <h1 className="text-lg font-bold leading-none">{project.teamName} / {project.leaderName}</h1>
              <span className="text-xs text-muted-foreground font-mono mt-1">{project.repoUrl}</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
             {project.status === 'running' && (
               <span className="text-xs text-blue-400 font-mono animate-pulse">
                 Agent Active...
               </span>
             )}
            <StatusBadge status={project.status || 'pending'} />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Top Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="glass-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Branch Created</CardTitle>
              <GitBranch className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-xs font-mono font-bold truncate text-primary">
                {project.branchName || "Waiting for agent..."}
              </div>
            </CardContent>
          </Card>
          
          <Card className="glass-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Issues</CardTitle>
              <AlertCircle className="h-4 w-4 text-red-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{bugStats.total}</div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Auto-Fixed</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-400">{bugStats.fixed}</div>
            </CardContent>
          </Card>

          <Card className="glass-card">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <BugIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {bugStats.total > 0 
                  ? Math.round((bugStats.fixed / bugStats.total) * 100) 
                  : 0}%
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Area */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left: Bug List */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <FileCode className="w-5 h-5 text-primary" />
                Detected Issues
              </h2>
            </div>
            
            {isBugsLoading ? (
               <div className="space-y-4">
                 {[1,2,3].map(i => (
                   <div key={i} className="h-24 bg-card/50 animate-pulse rounded-xl" />
                 ))}
               </div>
            ) : (
              <div className="space-y-4">
                <AnimatePresence>
                  {bugs?.map((bug, idx) => (
                    <motion.div
                      key={bug.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.1 }}
                    >
                      <Card className="border-border hover:border-primary/50 transition-colors duration-200 overflow-hidden group">
                        <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-blue-500 to-purple-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                        <CardContent className="p-6">
                          <div className="flex items-start justify-between gap-4">
                            <div className="space-y-1.5 flex-1">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-muted-foreground">
                                  {bug.bugType}
                                </span>
                                <span className="text-sm font-mono text-primary truncate max-w-[300px]">
                                  {bug.filePath}:{bug.lineNumber}
                                </span>
                              </div>
                              <p className="text-sm text-foreground/80 font-mono bg-black/20 p-2 rounded border border-white/5">
                                {bug.errorMessage}
                              </p>
                              
                              {bug.fixApplied && (
                                <div className="mt-3 pt-3 border-t border-white/5">
                                  <p className="text-xs text-green-400 flex items-center gap-1.5">
                                    <CheckCircle2 className="w-3 h-3" />
                                    Fix Applied: <span className="font-mono text-foreground/70">{bug.fixApplied}</span>
                                  </p>
                                </div>
                              )}
                            </div>
                            <StatusBadge status={bug.status || 'pending'} />
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </AnimatePresence>
                
                {bugs?.length === 0 && (
                  <div className="text-center py-20 bg-card/30 rounded-2xl border border-dashed border-border">
                    <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4 opacity-50" />
                    <h3 className="text-lg font-medium">All Clear</h3>
                    <p className="text-muted-foreground">No bugs detected in this repository.</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right: Live Logs / Activity */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Terminal className="w-5 h-5 text-primary" />
              Agent Activity
            </h2>
            
            <Card className="bg-black/40 border-border h-[600px] flex flex-col font-mono text-xs">
              <CardHeader className="py-3 px-4 border-b border-white/5 bg-white/5">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
                  </div>
                  <span className="ml-2 text-muted-foreground">agent_logs.txt</span>
                </div>
              </CardHeader>
              <ScrollArea className="flex-1 p-4">
                <div className="space-y-2">
                  <div className="text-green-400/80">
                    <span className="opacity-50">[{format(new Date(project.createdAt || new Date()), 'HH:mm:ss')}]</span> 
                    {' '}System initialized
                  </div>
                  
                  {project.status === 'running' && (
                     <>
                        <div className="text-blue-400/80">
                            <span className="opacity-50">[{format(new Date(), 'HH:mm:ss')}]</span>
                            {' '}Cloning repository {project.repoUrl}...
                        </div>
                        <div className="text-blue-400/80">
                             <span className="opacity-50">[{format(new Date(), 'HH:mm:ss')}]</span>
                             {' '}Analyzing project structure...
                        </div>
                        <div className="text-yellow-400/80 animate-pulse">
                             <span className="opacity-50">[{format(new Date(), 'HH:mm:ss')}]</span>
                             {' '}Running test suite...
                        </div>
                     </>
                  )}

                  {bugs?.map((bug) => (
                    <div key={bug.id} className="text-red-400/80">
                      <span className="opacity-50">[{format(new Date(bug.createdAt || new Date()), 'HH:mm:ss')}]</span>
                      {' '}Detected {bug.bugType} in {bug.filePath.split('/').pop()}
                    </div>
                  ))}

                  {project.status === 'completed' && (
                    <div className="text-green-400/80 border-t border-white/10 pt-2 mt-2">
                        <span className="opacity-50">[{format(new Date(), 'HH:mm:ss')}]</span>
                        {' '}Analysis complete. Branch ready.
                    </div>
                  )}
                  
                  {project.status === 'failed' && (
                    <div className="text-red-500 border-t border-white/10 pt-2 mt-2">
                        <span className="opacity-50">[{format(new Date(), 'HH:mm:ss')}]</span>
                        {' '}Analysis failed. Check logs above.
                    </div>
                  )}
                </div>
              </ScrollArea>
              
              {project.status === 'running' && (
                 <div className="p-2 border-t border-white/5 text-center">
                    <span className="inline-flex items-center gap-2 text-muted-foreground animate-pulse">
                       <Loader2 className="w-3 h-3 animate-spin" /> Processing...
                    </span>
                 </div>
              )}
            </Card>
          </div>
          
        </div>
      </main>
    </div>
  );
}

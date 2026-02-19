import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useLocation } from "wouter";
import { motion } from "framer-motion";
import { useCreateProject } from "@/hooks/use-projects";
import { insertProjectSchema } from "@shared/schema";
import { 
  Form, 
  FormControl, 
  FormField, 
  FormItem, 
  FormLabel, 
  FormMessage 
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Github, Bot, Sparkles, ArrowRight } from "lucide-react";

const formSchema = insertProjectSchema.pick({
  repoUrl: true,
  teamName: true,
  leaderName: true,
});

type FormValues = z.infer<typeof formSchema>;

export default function Home() {
  const [, setLocation] = useLocation();
  const { mutate, isPending } = useCreateProject();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      repoUrl: "",
      teamName: "",
      leaderName: "",
    },
  });

  const onSubmit = (data: FormValues) => {
    mutate(data, {
      onSuccess: (project) => {
        setLocation(`/project/${project.id}`);
      },
    });
  };

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-blue-900/20 via-background to-background flex items-center justify-center p-4">
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        
        {/* Left Column: Marketing/Hero */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
          className="space-y-6"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium border border-primary/20">
            <Sparkles className="w-4 h-4" />
            <span>AI-Powered Code Repair</span>
          </div>
          
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight leading-tight">
            Fix your code <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">
              in seconds.
            </span>
          </h1>
          
          <p className="text-lg text-muted-foreground max-w-md leading-relaxed">
            Deploy our autonomous agent to clone, test, and patch your repository automatically. Zero config required.
          </p>

          <div className="grid grid-cols-2 gap-4 pt-4">
            <div className="p-4 rounded-xl bg-card border border-border/50">
              <Bot className="w-8 h-8 text-blue-400 mb-2" />
              <h3 className="font-semibold text-foreground">Auto-Detection</h3>
              <p className="text-sm text-muted-foreground">Finds bugs instantly</p>
            </div>
            <div className="p-4 rounded-xl bg-card border border-border/50">
              <Github className="w-8 h-8 text-purple-400 mb-2" />
              <h3 className="font-semibold text-foreground">Git Integration</h3>
              <p className="text-sm text-muted-foreground">Commits fixes automatically</p>
            </div>
          </div>
        </motion.div>

        {/* Right Column: Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <Card className="glass-card border-t border-t-white/10 shadow-2xl shadow-blue-900/10">
            <CardHeader>
              <CardTitle className="text-xl">Start New Analysis</CardTitle>
              <CardDescription>Enter your repository details to begin</CardDescription>
            </CardHeader>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="repoUrl"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>GitHub Repository URL</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <Github className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                            <Input 
                              placeholder="https://github.com/username/repo" 
                              className="pl-9 glass-input" 
                              {...field} 
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="teamName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Team Name</FormLabel>
                          <FormControl>
                            <Input placeholder="Engineering" className="glass-input" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    
                    <FormField
                      control={form.control}
                      name="leaderName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Leader Name</FormLabel>
                          <FormControl>
                            <Input placeholder="John Doe" className="glass-input" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <Button 
                    type="submit" 
                    className="w-full mt-2 font-semibold h-11"
                    disabled={isPending}
                  >
                    {isPending ? (
                      "Initializing Agent..."
                    ) : (
                      <>
                        Run Analysis <ArrowRight className="w-4 h-4 ml-2" />
                      </>
                    )}
                  </Button>
                </form>
              </Form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}

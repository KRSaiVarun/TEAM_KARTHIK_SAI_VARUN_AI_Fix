CREATE TABLE "bugs" (
	"id" serial PRIMARY KEY NOT NULL,
	"project_id" integer NOT NULL,
	"file_path" text NOT NULL,
	"bug_type" text NOT NULL,
	"line_number" integer,
	"error_message" text,
	"fix_applied" text,
	"status" text DEFAULT 'pending',
	"created_at" timestamp DEFAULT now()
);
--> statement-breakpoint
CREATE TABLE "projects" (
	"id" serial PRIMARY KEY NOT NULL,
	"repo_url" text NOT NULL,
	"team_name" text NOT NULL,
	"leader_name" text NOT NULL,
	"branch_name" text,
	"created_at" timestamp DEFAULT now(),
	"completed_at" timestamp,
	"status" text DEFAULT 'pending',
	"commit_count" integer DEFAULT 0,
	"summary" jsonb
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" varchar PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"username" text NOT NULL,
	"password" text NOT NULL,
	CONSTRAINT "users_username_unique" UNIQUE("username")
);

import { Pool } from "pg";

async function main() {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    console.error("DATABASE_URL not set");
    process.exit(1);
  }

  const pool = new Pool({ connectionString });
  const client = await pool.connect();
  try {
    console.log("Applying missing columns to projects table...");
    const sql = `
      ALTER TABLE projects ADD COLUMN IF NOT EXISTS retry_count integer DEFAULT 0;
      ALTER TABLE projects ADD COLUMN IF NOT EXISTS max_retries integer DEFAULT 5;
      ALTER TABLE projects ADD COLUMN IF NOT EXISTS timeline jsonb DEFAULT '[]'::jsonb;
      ALTER TABLE projects ADD COLUMN IF NOT EXISTS commit_count integer DEFAULT 0;
    `;
    await client.query(sql);
    console.log("Columns applied successfully");
  } catch (err) {
    console.error("Failed to apply columns:", err);
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

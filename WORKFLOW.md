# 🚀 User Workflow Guide

## How to Use the Code Fix Agent Dashboard

### Step-by-Step Process

#### Step 1: Access the Dashboard

- Open your browser and navigate to: **http://localhost:5000**
- You should see the "AI Code Analysis Agent" dashboard

#### Step 2: Fill Out the Form

The dashboard has a form with three fields:

**1. GitHub Repository URL**

- Example: `https://github.com/KRSaiVarun/FlaskBlog.git`
- This is the repository you want to analyze
- Must be a valid GitHub URL

**2. Team Name**

- Example: `Team Alpha` or `Backend Squad`
- This identifies your team
- Can be any name you choose

**3. Leader Name**

- Example: `Alice Johnson` or `John Smith`
- Name of the team leader
- Will be displayed in project details

#### Step 3: Submit for Analysis

- Click the **"Run Analysis"** button
- You'll see a loading state while the project is being created
- Once created, the dashboard updates and you'll see your project in the list

#### Step 4: View Project Details

After submission, you can:

1. Click on your project in the list, OR
2. Get a direct link shown in a notification/card

Click to navigate to: **http://localhost:5000/project/{PROJECT_ID}**

#### Step 5: Monitor Analysis Progress

On the Project Details page, you'll see:

**Real-time Updates:**

- Yellow "Agent Active..." indicator while running
- Status badge showing: `PENDING`, `RUNNING`, `COMPLETED`, or `FAILED`
- Live agent activity logs on the right side

**Displayed Information:**

- **Header**: Shows YOUR team name and leader name (not demo data!)
- **Repository URL**: The repo you submitted
- **Branch Name**: Auto-created fix branch (when completed)
- **Statistics**: Total issues, fixed count, success rate

#### Step 6: View Results

Once analysis completes (status = `COMPLETED`), you'll see:

**Score Breakdown Panel:**

- Base score: 100 points
- Speed bonus: +10 if < 5 minutes
- Commit penalty: -2 per commit over 20
- Quality bonus: Based on fix success rate
- Interactive breakdown chart

**Fixes Applied Table:**

- All detected bugs listed in table format
- Columns: File | Bug Type | Line Number | Commit Message | Status
- Color-coded by status:
  - 🟢 Green = Fixed
  - 🔴 Red = Failed
  - 🟡 Yellow = Pending

**Agent Activity Logs:**

- Real-time logs showing what the agent did
- Timeline of events from start to finish
- Error messages if any failed steps

### Example Workflow

```
1. Dashboard (http://localhost:5000)
   ├─ Fill form:
   │  ├─ Repo: https://github.com/user/project
   │  ├─ Team: My Development Team
   │  └─ Leader: Sarah Chen
   └─ Click "Run Analysis"
        ↓
2. Project Created
   ├─ Project ID: 5
   ├─ Status: RUNNING
   └─ Agent starts analyzing...
        ↓
3. Agent Working (2-5 minutes)
   ├─ Cloning repo
   ├─ Scanning files
   ├─ Running tests
   ├─ Detecting bugs
   └─ Applying fixes
        ↓
4. Analysis Complete
   ├─ Status: COMPLETED
   ├─ Shows: "My Development Team / Sarah Chen"
   ├─ Score: 111 points
   │  ├─ Base: 100
   │  ├─ Speed: +10 (3 min)
   │  └─ Quality: +1 (90% success)
   ├─ Bugs: 10 detected
   │  ├─ Fixed: 9 ✓
   │  └─ Failed: 1 ✗
   └─ View all fixes in table
```

### Key Points

✅ **Real Data is Shown:**

- Project Details displays YOUR submitted team name and leader name
- NOT "Demo Team / John Doe" (that's only in the demo seed data)
- All data comes from the database when you submit the form

✅ **Dynamic Project Updates:**

- Dashboard polls for updates every 3 seconds
- Status updates in real-time
- Projects list refreshes automatically

✅ **Responsive Design:**

- Works on desktop, tablet, and mobile
- Optimized for all screen sizes
- Touch-friendly on tablets

### Troubleshooting

**Q: I see "Demo Team / John Doe" instead of my data**

- A: Make sure you're not looking at Project ID 3 (the demo project)
- A: Create a new project by submitting the form on the dashboard
- A: Your new project will show YOUR data

**Q: The analysis is taking a long time**

- A: First analyses can take 2-5 minutes depending on repo size
- A: Check the Agent Activity logs to see what's happening
- A: Some repos may have many files to scan

**Q: Status shows "FAILED"**

- A: Check the Agent Activity logs for error messages
- A: Ensure the GitHub URL is correct
- A: Some repos may have encoding issues or be too large

**Q: Connection refused error?**

- A: Make sure PostgreSQL database is running
- A: Ensure the server is running on port 5000
- A: Check DATABASE_URL is set correctly

### Demo vs Real Usage

#### Demo Data (for testing)

```bash
npm run seed    # Creates demo project ID 3
Visit: http://localhost:5000/project/3
Team: "Demo Team"
Leader: "John Doe"
```

#### Real Usage (what users should do)

```
1. Go to http://localhost:5000
2. Fill out the form with real data
3. Click "Run Analysis"
4. View project with your real data!
```

---

**Remember:** The form input is what matters! Whatever you enter in Team Name and Leader Name will be displayed on the Project Details page.

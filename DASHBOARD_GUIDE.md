# Dashboard Workflow Summary

## 🎯 How the System Works

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER DASHBOARD                       │
│   http://localhost:5000                                 │
├─────────────────────────────────────────────────────────┤
│  User fills form:                                        │
│  ├─ Repo URL: https://github.com/user/repo              │
│  ├─ Team Name: [YOUR TEAM NAME]                         │
│  └─ Leader Name: [YOUR NAME]                            │
└──────────────┬──────────────────────────────────────────┘
               │ Form Submit
               ▼
       ┌──────────────────┐
       │   POST API       │
       │  /api/projects   │
       └──────┬───────────┘
              │
              ▼
    ┌─────────────────────┐
    │   Project Created   │
    │   in Database       │
    │ ──────────────────  │
    │ ID: 5               │
    │ Team: [YOUR DATA]   │
    │ Leader: [YOUR DATA] │
    │ Repo: [YOUR DATA]   │
    │ Status: RUNNING     │
    └────────┬────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │   Python Agent Starts       │
    │   (Background Process)      │
    │ ─────────────────────────── │
    │ 1. Clones repo              │
    │ 2. Scans all files          │
    │ 3. Detects bugs             │
    │ 4. Applies fixes            │
    │ 5. Stores results           │
    └────────┬────────────────────┘
             │
             ▼
    ┌─────────────────────────────┐
    │   Project Details Page      │
    │   /project/5                │
    │ ─────────────────────────── │
    │ Header shows:               │
    │ "[YOUR TEAM] / [YOUR NAME]" │
    │ Repo: [YOUR REPO]           │
    │                             │
    │ Score Panel:                │
    │ ├─ Base: 100                │
    │ ├─ Speed Bonus: +10         │
    │ ├─ Commits: -0              │
    │ └─ Quality: +5              │
    │ ───────────────             │
    │ Total: 115                  │
    │                             │
    │ Fixes Table:                │
    │ ├─ Bug 1: FIXED ✓           │
    │ ├─ Bug 2: FIXED ✓           │
    │ ├─ Bug 3: FAILED ✗          │
    │ └─ Bug 4: PENDING ⚠️        │
    └─────────────────────────────┘
```

---

## 📋 Step-by-Step Comparison

### ❌ WRONG: Using Demo Data

```
1. Navigate to: http://localhost:5000/project/3
2. See: "Demo Team / John Doe"
3. This is just the DEMO - not your real project!
```

### ✅ CORRECT: Real Workflow

```
1. Go to: http://localhost:5000
2. Fill form:
   └─ Team Name: "My Team"
   └─ Leader Name: "Sarah Chen"
   └─ Repo URL: "https://github.com/..."
3. Click "Run Analysis"
4. Go to: http://localhost:5000/project/{YOUR_PROJECT_ID}
5. See: "My Team / Sarah Chen"
   ← THIS IS YOUR DATA!
```

---

## 🔄 Real-Time Updates

The system updates in real-time:

1. **Dashboard** refreshes project list every 3 seconds
2. **Status Updates** from PENDING → RUNNING → COMPLETED
3. **Bugs Table** populates as bugs are detected
4. **Agent Logs** show real-time activity

---

## 📊 What Gets Displayed Where

### On Dashboard (List View)

- Project ID
- Repository URL (truncated)
- Team Name
- Leader Name ← **USER INPUT**
- Status Badge
- Created timestamp
- Summary (if completed)

### On Project Details Page

```
HEADER:
┌───────────────────────────────────────────┐
│ Back | Team Name / Leader Name            │
│      | https://github.com/user/repo       │
│      |                          COMPLETED │
└───────────────────────────────────────────┘
       ↑ ALL FROM USER INPUT!
```

### Statistics Cards

```
┌──────────────┬──────────────┬──────────────┐
│ Branch Name  │ Total Issues │ Auto-Fixed   │
│ (generated)  │ (detected)   │ (counted)    │
└──────────────┴──────────────┴──────────────┘
```

### Score Breakdown Panel

```
Uses these factors to calculate score:
├─ Base Score: 100 (fixed)
├─ Speed Bonus: +10 if < 5 minutes
├─ Commit Penalty: -2 per commit over 20
└─ Quality Bonus: up to +5 based on fix success
```

### Fixes Applied Table

```
File | Bug Type | Line | Message | Status
─────┼──────────┼──────┼─────────┼────────
src/app.ts | SYNTAX | 42 | [fix message] | ✓ Fixed
src/utils.ts | LINTING | 18 | [fix message] | ✗ Failed
src/index.ts | LOGIC | 5 | [fix message] | ⚠️ Pending
```

---

## 🎨 Key Principle

**Form Input → Database → Display**

Whatever you type in the dashboard form fields:

- ✍️ **Team Name** field → Shows in project header
- ✍️ **Leader Name** field → Shows in project header
- ✍️ **Repo URL** field → Shows in project header

This is **NOT** hardcoded. It's **YOUR DATA**.

---

## 🧪 Testing

### To Test Real Workflow:

```bash
1. npm run dev              # Start server
2. Open http://localhost:5000
3. Fill out form with YOUR data
4. Click "Run Analysis"
5. Check project details shows YOUR data
```

### To See Demo:

```bash
1. npm run seed             # Create demo project ID 3
2. Open http://localhost:5000/project/3
3. This shows demo data for testing UI components
```

---

## ✅ Verification Checklist

Before submitting your project:

- [ ] You're on the dashboard (http://localhost:5000)
- [ ] You've filled all three form fields
- [ ] Team Name and Leader Name are YOUR data (not demo)
- [ ] You can see the form field values before clicking submit
- [ ] After submit, you're redirected to project details
- [ ] The project details show YOUR team name and leader name
- [ ] The repository URL matches what you entered

---

## 🚀 Success Indicators

✅ **Your project is working correctly when:**

1. Dashboard shows your submitted data in the projects list
2. Project Details page header shows: "[YOUR TEAM] / [YOUR NAME]"
3. Status updates in real-time (PENDING → RUNNING → COMPLETED)
4. Score panel appears when analysis is completed
5. Fixes table shows all detected bugs with colors
6. Agent activity logs show what the agent is doing

❌ **Something is wrong if:**

1. You see "Demo Team / John Doe" on a new project
2. Status stays "PENDING" for more than 2 minutes
3. No bugs are shown in the table
4. Score panel is missing after completion
5. The data doesn't match what you entered in the form

---

## 📞 Troubleshooting

**Q: Where's my project data?**

- Submitted form data is in database
- ProjectDetails page queries database for your data
- Make sure you're viewing the correct project ID

**Q: Why the demo data?**

- Demo data (Project 3) only appears when using `npm run seed`
- Real projects from the form show YOUR data

**Q: Data not updating?**

- Dashboard polls every 3 seconds
- Manual refresh (F5) updates immediately
- Check browser console for errors

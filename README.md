# 🤖 TEAM_KARTHIK_SAI_VARUN_AI_Fix

<div align="center">

![React](https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

**🏆 AI-Powered Intelligent CI Assistant**  
*Automatically analyze GitHub repositories, detect issues, and apply fixes with real-time analytics*

[Features](#✨-key-features) • [Quick Start](#🚀-quick-start) • [Architecture](#🏗️-architecture) • [API](#🔌-api-reference) • [Demo](#🎮-live-demo)

</div>


# 🤖 AI Code Fix Agent

An AI-powered tool that detects and fixes code issues automatically.

## 🚀 Live Deployment
👉 https://code-fix-agent--srchmydj.replit.app/

## 🛠 Tech Stack
- Node.js
- Express
- OpenAI API
- HTML/CSS
---

## 📸 Dashboard Preview

### Main Dashboard
![Dashboard Overview](./assets/dashboard-overview.png)
*Real-time analytics and project monitoring dashboard*

### Analysis Results
![Analysis Results](./assets/analysis-results.png)
*Detailed issue detection and performance metrics*

---

## ✨ Key Features

### 🔍 Smart Repository Analysis
- **Auto-clones** any public GitHub repository
- **Multi-language scanning** (Python, JavaScript, TypeScript, etc.)
- **Comprehensive issue detection**:
  - 🚨 Linting violations
  - 🔴 Syntax errors
  - 🧠 Logic problems
  - 🔒 Security vulnerabilities

### 🤖 Automated Fix Engine
- **Rule-based auto-fixing** for common issues
- **Intelligent suggestions** for complex problems
- **CI-style workflow** - automatically creates fix branches
- **Commit tracking** with success/failure reporting

### 📊 Intelligent Analytics Dashboard
| Metric | Description |
|--------|-------------|
| ⏱️ Time Saved | Automated fix duration tracking |
| 📈 Performance Score | Algorithmic code quality assessment |
| 📊 Issue Breakdown | Categorization by type and severity |
| 📉 Quality Trends | Before/after improvement metrics |
| 🧮 Success Rate | Fix effectiveness percentage |

### 🎯 Performance Scoring System
Each repository receives a comprehensive **Performance Score** based on:
- Total issues detected
- Fix success percentage
- Code quality improvements
- Security risk reduction

### 📋 Issue Explorer
- File-by-file issue breakdown
- Severity levels (Critical/High/Medium/Low)
- Resolution status tracking
- Historical fix records

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- PostgreSQL 14+
- Git

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/TEAM_KARTHIK_SAI_VARUN_AI_Fix.git
cd TEAM_KARTHIK_SAI_VARUN_AI_Fix
Install Node dependencies

bash
npm install
Install Python dependencies

bash
pip install fastapi uvicorn pydantic gitpython pytest psycopg2-binary
Configure environment

bash
# Create .env file
DATABASE_URL=postgresql://user:password@localhost:5432/ci_agent_db
Setup database

bash
npm run db:push
Launch the application

bash
npm run dev
Access the dashboard at: http://localhost:5000

📦 Optional: Seed Demo Data
bash
npm run seed
Creates sample projects and analytics for testing.

🎮 Using the Dashboard
1. Submit a Repository
Enter GitHub URL: https://github.com/username/repo

Provide team details

Click "Run Analysis"

2. Monitor Progress
Real-time status updates: PENDING → RUNNING → COMPLETED

Live agent activity logs

Processing timeline

3. Review Results
Performance score calculation

Detected issues list

Applied fixes summary

Commit history

🏗️ Architecture
text
TEAM_KARTHIK_SAI_VARUN_AI_Fix/
├── 📁 client/                 # React Frontend
│   ├── components/            # Reusable UI components
│   │   ├── ScoreBreakdownPanel.tsx
│   │   ├── EnhancedFixesAppliedTable.tsx
│   │   └── CICDTimeline.tsx
│   ├── pages/                 # Route pages
│   └── App.tsx                # Main app component
│
├── 📁 server/                  # Node.js Backend
│   ├── index.ts               # Express server
│   ├── routes.ts              # API routes
│   ├── storage.ts             # Data layer
│   └── db.ts                  # Database connection
│
├── 📁 backend/                 # Python Analysis Agent
│   └── agent.py               # Core analysis engine
│
├── 📁 shared/                  # Shared types/schemas
│   ├── schema.ts              # Database schema
│   └── routes.ts              # API type definitions
│
├── 📁 workspace/               # Repository storage
│   ├── project_1/
│   └── project_2/
│
└── 📁 migrations/              # Database migrations
🔌 API Reference
Projects
Method	Endpoint	Description
POST	/api/projects	Submit new repository
GET	/api/projects	List all projects
GET	/api/projects/:id	Get project details
Issues
Method	Endpoint	Description
GET	/api/projects/:id/bugs	Get detected issues
GET	/api/projects/:id/fixes	Get applied fixes
🧪 Testing
Run the test suite:

bash
# Backend tests
pytest backend/tests/

# Frontend tests
npm test
🛣️ Roadmap
Basic repository analysis

Automated fix application

Performance scoring

Real-time dashboard

ML-based issue prioritization

Predictive CI failure detection

Multi-repository analysis

GitHub webhook integration

Docker containerization

Kubernetes deployment

📈 Performance Metrics
The system tracks:

Average analysis time: 30-60 seconds

Fix success rate: ~85% for common issues

Supported languages: 5+ (Python, JS, TS, Java, Go)

Issue categories: 20+ detection rules

🤝 Contributing
Fork the repository

Create feature branch (git checkout -b feature/AmazingFeature)

Commit changes (git commit -m 'Add AmazingFeature')

Push to branch (git push origin feature/AmazingFeature)

Open a Pull Request

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

👨‍💻 Authors
Team Karthik Sai Varun

GitHub

LinkedIn

🙏 Acknowledgments
Hackathon organizers and sponsors

Open source community

All contributors and testers

<div align="center">
⭐ Star us on GitHub — it motivates us! ⭐

</div> ```

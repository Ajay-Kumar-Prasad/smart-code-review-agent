# 🤖 Smart Code Review Agent
### GenAI Academy APAC Edition 2026 — Track 1 Project
*Built with Google ADK + Gemini 2.5 Flash, deployed on Google Cloud Run*

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Google ADK](https://img.shields.io/badge/Google%20ADK-1.14.0-4285F4?logo=google)
![Gemini](https://img.shields.io/badge/Gemini-2.5%20Flash-8E75B2?logo=google)
![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Deployed-34A853?logo=googlecloud)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 📌 Overview

The **Smart Code Review Agent** is an AI-powered code review system built as a multi-agent pipeline using Google's Agent Development Kit (ADK). It accepts any code snippet via a live web UI or HTTP API and returns a structured, developer-friendly review — covering bugs, security vulnerabilities, code quality, performance issues, and best practices — along with a quality score out of 100.

🌐 **Live Demo:** https://code-review-agent-692228693579.us-central1.run.app

---

## 🎯 What It Does

Submit any code snippet and get back a full review:

| Category | What's Checked |
|---|---|
| 🐛 **Bugs & Logic Errors** | Off-by-one, null dereference, wrong conditions, infinite loops |
| 🔒 **Security Vulnerabilities** | Hardcoded secrets, SQL injection, eval() misuse, unvalidated input |
| 🧹 **Code Quality** | Magic numbers, SRP violations, poor naming, dead code |
| ⚡ **Performance** | Nested loops, repeated calls, hot-path allocations |
| ✅ **Best Practices** | Missing docstrings, error handling, unused imports |
| 📊 **Quality Score** | 0–100 rating with rationale and top 3 recommendations |

---

## 🏗️ Architecture

Follows the **SequentialAgent** pattern from the GenAI Academy lab:

```
root_agent (code_review_greeter)
    │
    ├── Tool: save_code_to_state      ← captures code + language into shared state
    │
    └── review_workflow (SequentialAgent)
            │
            ├── Step 1: code_analyser
            │       └── Tool: run_static_checks  ← deterministic line-level checks
            │           + Gemini LLM deep analysis
            │           → writes findings to state["analysis_data"]
            │
            └── Step 2: report_writer
                    → reads state["analysis_data"]
                    → outputs final formatted review
```

### Agent Roles

| Agent | Role |
|---|---|
| `code_review_greeter` | Entry point — greets user, collects code snippet, saves to state |
| `code_analyser` | Runs static checks + LLM deep analysis across all categories |
| `report_writer` | Formats raw analysis into a clean, developer-friendly report |

### How It Maps to the Zoo Agent (Lab Pattern)

| Zoo Guide Agent | Smart Code Review Agent |
|---|---|
| `greeter` | `code_review_greeter` |
| `add_prompt_to_state` | `save_code_to_state` |
| `tour_guide_workflow` | `review_workflow` |
| `comprehensive_researcher` | `code_analyser` |
| `wikipedia_tool` | `run_static_checks` |
| `response_formatter` | `report_writer` |

---

## 📁 Project Structure

```
smart-code-review-agent/
├── main.py                     ← FastAPI server (serves UI + ADK routes)
├── index.html                  ← Frontend web UI
├── Dockerfile                  ← Container definition for Cloud Run
├── requirements.txt            ← Python dependencies
├── .gitignore                  ← Excludes .env and .venv
├── README.md                   ← This file
└── code_review_agent/          ← Agent package
    ├── __init__.py             ← Package entry point
    ├── agent.py                ← All agent logic
    └── .env.example            ← Environment variable template
```

---

## 🛠️ Tech Stack

- **[Google ADK](https://google.github.io/adk-docs/)** — Agent Development Kit for building multi-agent workflows
- **[Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/)** — Google's fast, capable LLM for code analysis
- **[Google Cloud Run](https://cloud.google.com/run)** — Serverless container deployment
- **[FastAPI](https://fastapi.tiangolo.com/)** — Web framework serving the UI and ADK routes
- **[Cloud Build](https://cloud.google.com/build)** — Automated container image building
- **Python 3.11+** — Core language

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Google Cloud project with billing enabled
- Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
- `gcloud` CLI installed and authenticated

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/Ajay-Kumar-Prasad/smart-code-review-agent.git
cd smart-code-review-agent

# 2. Create virtual environment
uv venv
source .venv/bin/activate

# 3. Install dependencies
uv pip install -r requirements.txt
pip install fastapi uvicorn

# 4. Set up environment variables
cp code_review_agent/.env.example code_review_agent/.env
# Edit .env and add your GOOGLE_API_KEY

# 5. Run locally
python main.py
```

Open http://127.0.0.1:8080 in your browser to use the web UI.

---

## ☁️ Cloud Run Deployment

### Step 1 — Enable APIs
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  compute.googleapis.com
```

### Step 2 — Create Service Account
```bash
PROJECT_ID=$(gcloud config get-value project)
SA_NAME=code-review-cr-service
SERVICE_ACCOUNT=${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com

gcloud iam service-accounts create ${SA_NAME} \
  --display-name="Service Account for Code Review Agent"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/aiplatform.user"
```

### Step 3 — Deploy
```bash
gcloud run deploy code-review-agent \
  --source . \
  --region=us-central1 \
  --service-account=${SERVICE_ACCOUNT} \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --set-env-vars="GOOGLE_API_KEY=your_api_key_here"
```

---

## 🧪 Testing the Live Endpoint

### Via Web UI
Open https://code-review-agent-692228693579.us-central1.run.app in your browser, paste any code snippet and click **Review Code**.

### Via API (one-liner)
```bash
SESSION_ID=$(curl -s -X POST \
  https://code-review-agent-692228693579.us-central1.run.app/apps/code_review_agent/users/test/sessions \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X POST https://code-review-agent-692228693579.us-central1.run.app/run \
  -H "Content-Type: application/json" \
  -d "{
    \"app_name\": \"code_review_agent\",
    \"user_id\": \"test\",
    \"session_id\": \"$SESSION_ID\",
    \"new_message\": {
      \"role\": \"user\",
      \"parts\": [{\"text\": \"def divide(a, b):\n    return a / b\"}]
    }
  }"
```

> ⚠️ **Note:** Cloud Run scales to zero when idle. The first request may take 5–10 seconds (cold start).

---

## 💡 Sample Review Output

**Input:**
```python
def get_user(id):
    conn = psycopg2.connect("postgresql://admin:password123@db/prod")
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE id = {id}")
    return cur.fetchone()
```

**Output:**
```
## 📊 Quality Score
████░░░░░░ 35/100
Critical security vulnerabilities present.

## 🔒 Security Issues
Line 2 | 🔴 HIGH | Hardcoded database credentials in connection string.
        Fix: Use environment variables or Secret Manager.
Line 4 | 🔴 HIGH | SQL injection via f-string interpolation.
        Fix: Use parameterised query: cur.execute("SELECT * FROM users
        WHERE id = %s", (id,))

## 💡 Top 3 Recommendations
1. Remove hardcoded credentials — use os.getenv() or Secret Manager
2. Use parameterised queries to prevent SQL injection
3. Add error handling with try/except for database operations
```

---

## 🧹 Clean Up

```bash
# Delete Cloud Run service
gcloud run services delete code-review-agent --region=us-central1 --quiet

# Delete Artifact Registry images
gcloud artifacts repositories delete cloud-run-source-deploy \
  --location=us-central1 --quiet
```

---

## 📚 Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GenAI Academy APAC 2026](https://hack2skill.com)

---

## 👤 Author

**Ajay Kumar Prasad**
- GitHub: [@Ajay-Kumar-Prasad](https://github.com/Ajay-Kumar-Prasad)
- Built for: GenAI Academy APAC Edition 2026 by Google & Hack2Skill

---

## 📄 License

This project is licensed under the MIT License.

---

*Built with ❤️ as part of GenAI Academy APAC Edition 2026 — Track 1: Single Agent Deployment*
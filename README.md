# HCPulse AI CRM — AI-First HCP Interaction Module

HCPulse is a demo AI-first CRM module for life-sciences field representatives. It provides two ways to log Healthcare Professional (HCP) interactions:

1. A structured React form.
2. A conversational AI assistant powered by Groq and orchestrated with LangGraph.

## Mandatory stack implemented

- React + Vite
- Redux Toolkit
- FastAPI
- LangGraph
- Groq LLM
- PostgreSQL
- SQLAlchemy
- Google Inter

## LangGraph agent role

The LangGraph workflow receives a field representative's natural-language message, sends it to the Groq LLM for structured intent/entity extraction, routes the request to a CRM tool, executes that tool against PostgreSQL, and generates a user-friendly response.

Graph flow:

`START -> understand -> route -> tool node -> respond -> END`

The AI is the reasoning layer; the CRM tools are the controlled action layer.

## Five sales tools

### 1. Log Interaction
Captures an HCP meeting from natural language. The LLM extracts HCP, interaction type, date/time, attendees, topics, product/material context, sentiment and follow-up intent. The tool saves structured data to PostgreSQL.

### 2. Edit Interaction
Finds the latest interaction for an HCP and modifies a supported field such as sentiment, topics, interaction type or follow-up requirement.

### 3. Get HCP Interaction History
Returns recent interactions for an HCP so a representative can prepare before a visit.

### 4. Schedule Follow-Up
Creates a follow-up activity linked to an HCP with a date and purpose.

### 5. Generate HCP Insights
Retrieves HCP interaction history and asks the LLM to generate engagement, interest and next-action insights.

## Project structure

```text
frontend/                  React + Redux UI
backend/app/main.py        FastAPI application
backend/app/agent.py       LangGraph workflow and Groq reasoning
backend/app/tools.py       Five CRM tools
backend/app/models.py      SQLAlchemy models
backend/app/schemas.py     API schemas
backend/app/database.py    PostgreSQL connection
```

## Run PostgreSQL

Install Docker Desktop, then from the project root:

```bash
docker compose up -d
```

## Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env
```

Add your Groq API key to `.env`.

```bash
uvicorn app.main:app --reload --port 8000
```

Open API docs at `http://localhost:8000/docs`.

## Run frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Demo prompts

Use these in order during the recording:

1. `Log a meeting with Dr. Ananya Sharma today. We discussed CardioPlus efficacy and patient outcomes. She was interested and requested the clinical brochure. Follow-up is required.`
2. `Edit my latest interaction with Dr. Ananya Sharma and change the sentiment to very interested.`
3. `Show interaction history for Dr. Ananya Sharma.`
4. `Schedule a follow-up with Dr. Ananya Sharma on 2026-07-21 to share clinical efficacy data.`
5. `Generate insights for Dr. Ananya Sharma.`

## Model note

The assignment references `gemma2-9b-it`. Model availability can change on hosted inference platforms. The model is configured through `GROQ_MODEL`; this submission defaults to `llama-3.3-70b-versatile`, which can be changed without code modifications.

## Design decisions

- AI requests are routed through LangGraph rather than directly calling CRUD endpoints.
- The LLM produces structured intent and arguments.
- Database mutation is restricted to explicit CRM tools.
- Structured form logging remains available when a rep prefers manual entry.
- The UI uses Inter and mirrors a two-pane Log Interaction / AI Assistant workflow.

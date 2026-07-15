from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from sqlalchemy import select
from sqlalchemy.orm import Session
from .database import Base, engine, get_db, settings
from .models import HCP, Interaction
from .schemas import InteractionCreate, ChatRequest
from .agent import run_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with next(get_db()) as db:
        if not db.scalar(select(HCP).limit(1)):
            db.add_all([
                HCP(name="Dr. Ananya Sharma", specialty="Cardiology", hospital="Apollo Heart Centre"),
                HCP(name="Dr. Rahul Mehta", specialty="General Medicine", hospital="City Care Hospital"),
                HCP(name="Dr. Priya Nair", specialty="Endocrinology", hospital="Green Valley Clinic"),
            ])
            db.commit()
    yield

app = FastAPI(title="HCPulse AI CRM API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "service": "HCPulse AI CRM"}

@app.get("/api/hcps")
def list_hcps(db: Session = Depends(get_db)):
    return [
        {"id": h.id, "name": h.name, "specialty": h.specialty, "hospital": h.hospital}
        for h in db.scalars(select(HCP).order_by(HCP.name)).all()
    ]

@app.get("/api/interactions")
def list_interactions(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Interaction, HCP).join(HCP).order_by(Interaction.created_at.desc()).limit(20)
    ).all()
    return [
        {
            "id": i.id, "hcp_name": h.name, "interaction_type": i.interaction_type,
            "interaction_date": i.interaction_date, "topics": i.topics,
            "sentiment": i.sentiment, "follow_up_required": i.follow_up_required,
            "outcomes": i.outcomes, "samples_distributed": i.samples_distributed,
        }
        for i, h in rows
    ]

@app.post("/api/interactions")
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    hcp = db.scalar(select(HCP).where(HCP.name == payload.hcp_name))
    if not hcp:
        hcp = HCP(name=payload.hcp_name)
        db.add(hcp)
        db.flush()
    item = Interaction(
        hcp_id=hcp.id,
        interaction_type=payload.interaction_type,
        interaction_date=payload.interaction_date,
        attendees=payload.attendees,
        topics=payload.topics,
        materials_shared=payload.materials_shared,
        sentiment=payload.sentiment,
        follow_up_required=payload.follow_up_required,
        outcomes=payload.outcomes,
        samples_distributed=payload.samples_distributed,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": f"Interaction #{item.id} logged successfully.", "id": item.id}

@app.post("/api/agent/chat")
def agent_chat(payload: ChatRequest):
    try:
        return run_agent(payload.message, payload.current_form)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

@app.post("/api/transcribe-summary")
async def transcribe_summary(file: UploadFile = File(...)):
    if not settings.groq_api_key:
        raise HTTPException(status_code=400, detail="GROQ_API_KEY is missing in backend .env file.")
    try:
        content = await file.read()
        client = Groq(api_key=settings.groq_api_key)
        transcription = client.audio.transcriptions.create(
            file=(file.filename, content),
            model="whisper-large-v3",
            response_format="json",
        )
        raw_text = transcription.text
        if not raw_text.strip():
            return {"transcript": "", "summary": ""}
        
        prompt = f"""
You are an expert CRM assistant for life sciences.
The user has provided a voice recording of their recent HCP interaction. 
Here is the raw transcription of the voice note:
---
{raw_text}
---

Summarize this transcription into a single concise, professional paragraph (2-4 sentences max) suitable for a "Topics Discussed" field in a CRM. Keep it structured and objective. Do not add any conversational filler, introductory phrases (like "Here is a summary:"), or bullet points. Just output the clean professional summary paragraph.
"""
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": "You are a professional life-sciences CRM summarization assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )
        summary = completion.choices[0].message.content.strip()
        return {"transcript": raw_text, "summary": summary}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

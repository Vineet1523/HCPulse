from datetime import datetime, date
from langchain_core.tools import tool
from sqlalchemy import select
from .database import SessionLocal
from .models import HCP, Interaction, FollowUp

def get_or_create_hcp(db, name: str):
    hcp = db.scalar(select(HCP).where(HCP.name.ilike(name.strip())))
    if not hcp:
        hcp = HCP(name=name.strip())
        db.add(hcp)
        db.flush()
    return hcp

@tool
def log_interaction(
    hcp_name: str,
    topics: str,
    interaction_type: str = "Meeting",
    interaction_date: str = "",
    attendees: str = "",
    materials_shared: str = "",
    sentiment: str = "Neutral",
    follow_up_required: bool = False,
    outcomes: str = "",
    samples_distributed: str = "",
) -> str:
    """Log a new structured HCP sales interaction in the CRM."""
    with SessionLocal() as db:
        hcp = get_or_create_hcp(db, hcp_name)
        try:
            dt = datetime.fromisoformat(interaction_date) if interaction_date else datetime.now()
        except ValueError:
            dt = datetime.now()
        item = Interaction(
            hcp_id=hcp.id, interaction_type=interaction_type, interaction_date=dt,
            attendees=attendees, topics=topics, materials_shared=materials_shared,
            sentiment=sentiment, follow_up_required=follow_up_required,
            outcomes=outcomes, samples_distributed=samples_distributed,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return f"Interaction #{item.id} logged for {hcp.name}. Sentiment: {sentiment}. Follow-up required: {follow_up_required}."

@tool
def edit_interaction(hcp_name: str, field: str, new_value: str) -> str:
    """Edit a supported field on the latest interaction for an HCP."""
    allowed = {"sentiment", "topics", "interaction_type", "materials_shared", "attendees", "follow_up_required"}
    if field not in allowed:
        return f"Cannot edit '{field}'. Supported fields: {', '.join(sorted(allowed))}."
    with SessionLocal() as db:
        hcp = db.scalar(select(HCP).where(HCP.name.ilike(hcp_name.strip())))
        if not hcp:
            return f"No HCP found named {hcp_name}."
        item = db.scalar(
            select(Interaction).where(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.interaction_date.desc())
        )
        if not item:
            return f"No interaction found for {hcp.name}."
        value = new_value.lower() in {"true", "yes", "1", "required"} if field == "follow_up_required" else new_value
        setattr(item, field, value)
        db.commit()
        return f"Interaction #{item.id} updated: {field} = {value}."

@tool
def get_hcp_history(hcp_name: str) -> str:
    """Retrieve recent interaction history for an HCP."""
    with SessionLocal() as db:
        hcp = db.scalar(select(HCP).where(HCP.name.ilike(hcp_name.strip())))
        if not hcp:
            return f"No HCP found named {hcp_name}."
        items = db.scalars(
            select(Interaction).where(Interaction.hcp_id == hcp.id)
            .order_by(Interaction.interaction_date.desc()).limit(10)
        ).all()
        if not items:
            return f"No interactions found for {hcp.name}."
        lines = [f"History for {hcp.name} ({hcp.specialty}):"]
        for x in items:
            lines.append(
                f"#{x.id} | {x.interaction_date:%Y-%m-%d} | {x.interaction_type} | "
                f"Sentiment: {x.sentiment} | Topics: {x.topics} | Materials: {x.materials_shared or 'None'} | "
                f"Samples: {x.samples_distributed or 'None'} | Outcomes: {x.outcomes or 'None'}"
            )
        return "\n".join(lines)

@tool
def schedule_follow_up(hcp_name: str, follow_up_date: str, purpose: str) -> str:
    """Schedule a sales follow-up activity for an HCP."""
    with SessionLocal() as db:
        hcp = get_or_create_hcp(db, hcp_name)
        try:
            due = date.fromisoformat(follow_up_date)
        except ValueError:
            return "Please provide the follow-up date in YYYY-MM-DD format."
        item = FollowUp(hcp_id=hcp.id, follow_up_date=due, purpose=purpose)
        db.add(item)
        db.commit()
        db.refresh(item)
        return f"Follow-up #{item.id} scheduled with {hcp.name} on {due.isoformat()} for: {purpose}."

@tool
def generate_hcp_insights(hcp_name: str) -> str:
    """Retrieve HCP CRM context for AI insight generation."""
    return get_hcp_history.invoke({"hcp_name": hcp_name})

TOOLS = {
    "log_interaction": log_interaction,
    "edit_interaction": edit_interaction,
    "get_hcp_history": get_hcp_history,
    "schedule_follow_up": schedule_follow_up,
    "generate_hcp_insights": generate_hcp_insights,
}

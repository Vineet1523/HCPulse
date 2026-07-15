from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: str = "Meeting"
    interaction_date: datetime
    attendees: str = ""
    topics: str
    materials_shared: str = ""
    sentiment: str = "Neutral"
    follow_up_required: bool = False
    outcomes: str = ""
    samples_distributed: str = ""

class ChatRequest(BaseModel):
    message: str = Field(min_length=2)
    current_form: dict | None = None

class AgentDecision(BaseModel):
    tool: Literal[
        "log_interaction",
        "edit_interaction",
        "get_hcp_history",
        "schedule_follow_up",
        "generate_hcp_insights",
    ]
    is_commit: bool = False
    hcp_name: str
    interaction_type: str | None = None
    interaction_date: str | None = None
    attendees: str | None = None
    topics: str | None = None
    materials_shared: str | None = None
    sentiment: str | None = None
    follow_up_required: bool | None = None
    outcomes: str | None = None
    samples_distributed: str | None = None
    field: str | None = None
    new_value: str | None = None
    follow_up_date: str | None = None
    purpose: str | None = None

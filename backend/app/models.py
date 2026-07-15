from datetime import datetime, date
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class HCP(Base):
    __tablename__ = "hcps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    specialty: Mapped[str] = mapped_column(String(100), default="General Medicine")
    hospital: Mapped[str] = mapped_column(String(150), default="City Care Hospital")
    interactions = relationship("Interaction", back_populates="hcp")

class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"))
    interaction_type: Mapped[str] = mapped_column(String(50), default="Meeting")
    interaction_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    attendees: Mapped[str] = mapped_column(Text, default="")
    topics: Mapped[str] = mapped_column(Text)
    materials_shared: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str] = mapped_column(String(50), default="Neutral")
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False)
    outcomes: Mapped[str] = mapped_column(Text, default="")
    samples_distributed: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    hcp = relationship("HCP", back_populates="interactions")

class FollowUp(Base):
    __tablename__ = "follow_ups"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hcp_id: Mapped[int] = mapped_column(ForeignKey("hcps.id"))
    follow_up_date: Mapped[date] = mapped_column(Date)
    purpose: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="Scheduled")

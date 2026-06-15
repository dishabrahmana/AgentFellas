from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class WorklogEntry(Base):
    __tablename__ = "worklog_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="in_progress")
    priority = Column(String, nullable=False, default="medium")
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    tags = Column(String, nullable=True, default="[]")
    stakeholder_id = Column(Integer, ForeignKey("stakeholders.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    stakeholder = relationship("Stakeholder", back_populates="worklogs")

    def __repr__(self) -> str:
        return f"<WorklogEntry #{self.id} '{self.title}' [{self.status}]>"


class Stakeholder(Base):
    __tablename__ = "stakeholders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=True)
    company = Column(String, nullable=True)
    contact_info = Column(String, nullable=True, default="{}")
    notes = Column(Text, nullable=True)
    priority = Column(String, nullable=False, default="medium")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    worklogs = relationship("WorklogEntry", back_populates="stakeholder")
    interactions = relationship("Interaction", back_populates="stakeholder")

    def __repr__(self) -> str:
        return f"<Stakeholder #{self.id} '{self.name}' [{self.role}]>"


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stakeholder_id = Column(Integer, ForeignKey("stakeholders.id"), nullable=False, index=True)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    action_items = Column(String, nullable=True, default="[]")
    date = Column(DateTime, nullable=False)
    next_action_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    stakeholder = relationship("Stakeholder", back_populates="interactions")

    def __repr__(self) -> str:
        return f"<Interaction #{self.id} '{self.title}' [{self.type}]>"


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False, index=True)
    is_done = Column(Boolean, nullable=False, default=False)
    related_type = Column(String, nullable=True)
    related_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self) -> str:
        return f"<Reminder #{self.id} '{self.title}' due={self.due_date}>"


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    chat_id = Column(String, nullable=False)
    context = Column(String, nullable=True, default="{}")
    last_intent = Column(String, nullable=True)
    last_entity = Column(String, nullable=True, default="{}")
    conversation_history = Column(String, nullable=True, default="[]")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    def __repr__(self) -> str:
        return f"<Session #{self.id} user={self.user_id}>"

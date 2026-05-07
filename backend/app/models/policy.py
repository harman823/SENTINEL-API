from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.app.core.database import Base


class ApiPolicy(Base):
    __tablename__ = "api_policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), unique=True, index=True, nullable=False)
    category = Column(String(80), nullable=False, default="custom")
    rule_type = Column(String(80), nullable=False, default="custom")
    severity = Column(String(20), nullable=False, default="warning")
    description = Column(Text, nullable=False, default="")
    config_json = Column(Text, nullable=False, default="{}")
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

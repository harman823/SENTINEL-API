from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Text
from backend.app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # We can store raw JSON reports as string/text since this is sqlite
    reports = Column(Text, nullable=True, default="[]") 
    timecreated_reports = Column(Text, nullable=True, default="{}")
    
    created_at = Column(DateTime, default=datetime.utcnow)

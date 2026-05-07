from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ApiPolicyBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = "custom"
    rule_type: str = "custom"
    severity: str = "warning"
    description: str = ""
    config: Dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class ApiPolicyCreate(ApiPolicyBase):
    pass


class ApiPolicyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    category: Optional[str] = None
    rule_type: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class ApiPolicyResponse(ApiPolicyBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

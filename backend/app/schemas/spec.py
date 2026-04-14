from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class Operation(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    operationId: Optional[str] = None
    parameters: List[Dict[str, Any]] = Field(default_factory=list)
    requestBody: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = Field(default_factory=dict)
    # Augmented fields
    method: str
    path: str
    is_destructive: bool = False
    risk_score: Optional[float] = None
    # Enhanced intelligence fields
    security_schemes: List[str] = Field(default_factory=list)
    pii_fields: List[str] = Field(default_factory=list)
    schema_complexity: int = 0  # 0 = simple, higher = more complex
    risk_factors: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class NormalizedSpec(BaseModel):
    openapi: str
    info: Dict[str, Any]
    paths: Dict[str, Dict[str, Operation]] = Field(default_factory=dict)
    components: Dict[str, Any] = Field(default_factory=dict)
    security_schemes: Dict[str, Any] = Field(default_factory=dict)
    # List of all operations for easier iteration
    operations: List[Operation] = Field(default_factory=list)

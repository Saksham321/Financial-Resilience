"""
Pydantic v2 Schemas for Health Check Endpoints
"""

from typing import Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    app_name: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ReadinessResponse(BaseModel):
    status: str # HEALTHY, DEGRADED, UNHEALTHY
    app_name: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    database: Dict[str, Any]
    active_engines: List[str]
    gemini_scaffold: Dict[str, Any]

"""Processing event models.

These models represent persistent workflow/progress events so the UI can show
what worked, what failed, and why.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProcessingEventLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ProcessingEventStatus(str, Enum):
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ProcessingEvent(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    stage: str
    status: ProcessingEventStatus
    level: ProcessingEventLevel
    message: str
    details: Optional[Dict[str, Any]] = None
    correlation_id: Optional[str] = None
    created_at: datetime


class ProcessingEventListResponse(BaseModel):
    items: list[ProcessingEvent] = Field(default_factory=list)
    total: int
    page: int
    limit: int
    pages: int

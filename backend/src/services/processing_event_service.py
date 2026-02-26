"""Processing event persistence.

Keeps a persistent, queryable audit trail of workflow/progress events so the UI
can show what succeeded/failed.

Design note:
- We write events using an independent session so a failure/rollback in the main
  request doesn't erase the log entry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..db.database import async_session_maker
from ..db.models import ProcessingEventDB
from ..middleware.logging_middleware import get_request_id

logger = logging.getLogger(__name__)


class ProcessingEventService:
    async def emit(
        self,
        *,
        entity_type: str,
        entity_id: str,
        stage: str,
        status: str,
        message: str,
        level: str = "INFO",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        correlation = correlation_id or get_request_id() or None

        try:
            async with async_session_maker() as session:
                event = ProcessingEventDB(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    stage=stage,
                    status=status,
                    level=level,
                    message=message,
                    details=details,
                    correlation_id=correlation,
                )
                session.add(event)
                await session.commit()
        except Exception:
            # Never let event logging break business logic.
            logger.debug(
                "Failed to persist processing event",
                extra={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "stage": stage,
                    "status": status,
                },
                exc_info=True,
            )

    async def emit_error(
        self,
        *,
        entity_type: str,
        entity_id: str,
        stage: str,
        message: str,
        error: Exception,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        safe_details: Dict[str, Any] = dict(details or {})
        safe_details.update(
            {
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )

        await self.emit(
            entity_type=entity_type,
            entity_id=entity_id,
            stage=stage,
            status="failed",
            message=message,
            level="ERROR",
            details=safe_details,
            correlation_id=correlation_id,
        )

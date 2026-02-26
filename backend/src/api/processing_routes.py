"""Processing Events API.

Exposes a persistent, queryable stream of workflow/progress events.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_session
from ..db.models import ProcessingEventDB
from ..models.processing_event import (
    ProcessingEvent,
    ProcessingEventLevel,
    ProcessingEventListResponse,
    ProcessingEventStatus,
)

router = APIRouter(prefix="/api/v1", tags=["processing"])


def _to_pydantic(row: ProcessingEventDB) -> ProcessingEvent:
    return ProcessingEvent(
        id=row.id,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        stage=row.stage,
        status=ProcessingEventStatus(row.status),
        level=ProcessingEventLevel(row.level),
        message=row.message,
        details=row.details,
        correlation_id=row.correlation_id,
        created_at=row.created_at,
    )


@router.get(
    "/processing/events",
    response_model=ProcessingEventListResponse,
    summary="List processing events",
)
async def list_processing_events(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    status: Optional[ProcessingEventStatus] = Query(None),
    level: Optional[ProcessingEventLevel] = Query(None),
    correlation_id: Optional[str] = Query(None),
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    q: Optional[str] = Query(None, description="Search in message"),
) -> ProcessingEventListResponse:
    conditions = []
    if entity_type:
        conditions.append(ProcessingEventDB.entity_type == entity_type)
    if entity_id:
        conditions.append(ProcessingEventDB.entity_id == entity_id)
    if stage:
        conditions.append(ProcessingEventDB.stage == stage)
    if status:
        conditions.append(ProcessingEventDB.status == status.value)
    if level:
        conditions.append(ProcessingEventDB.level == level.value)
    if correlation_id:
        conditions.append(ProcessingEventDB.correlation_id == correlation_id)
    if since:
        conditions.append(ProcessingEventDB.created_at >= since)
    if until:
        conditions.append(ProcessingEventDB.created_at <= until)
    if q:
        conditions.append(ProcessingEventDB.message.ilike(f"%{q}%"))

    where_clause = None
    if conditions:
        from sqlalchemy import and_

        where_clause = and_(*conditions)

    count_stmt = select(func.count(ProcessingEventDB.id))
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)

    total = (await session.execute(count_stmt)).scalar() or 0
    pages = (total + limit - 1) // limit if total > 0 else 0

    stmt = select(ProcessingEventDB)
    if where_clause is not None:
        stmt = stmt.where(where_clause)

    stmt = stmt.order_by(desc(ProcessingEventDB.created_at)).offset((page - 1) * limit).limit(limit)

    rows = (await session.execute(stmt)).scalars().all()

    return ProcessingEventListResponse(
        items=[_to_pydantic(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get(
    "/processing/events/{event_id}",
    response_model=ProcessingEvent,
    summary="Get a processing event by id",
)
async def get_processing_event(
    event_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ProcessingEvent:
    row = (await session.execute(select(ProcessingEventDB).where(ProcessingEventDB.id == event_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail=f"Processing event {event_id} not found")
    return _to_pydantic(row)


@router.delete(
    "/processing/events",
    summary="Clear all processing events",
)
async def clear_processing_events(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Delete all processing events from the database."""
    result = await session.execute(delete(ProcessingEventDB))
    await session.commit()
    return {"deleted": result.rowcount}

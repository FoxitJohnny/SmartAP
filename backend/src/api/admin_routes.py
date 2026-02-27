"""
Admin API Routes

Provides administrative endpoints for database management.
These endpoints are protected by a simple secret key check.
"""

import logging
from fastapi import APIRouter, HTTPException, Header, status
from sqlalchemy import select

from ..config import get_settings
from ..db.database import async_session_maker, init_db
from ..db.seed_data import run_seed
from ..db.models import VendorDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed_database(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    """
    Seed (or re-seed) the database with demo data.

    Requires the `X-Admin-Key` header to match the app's `SECRET_KEY`.
    Safe to call multiple times — skips seeding if data already exists.

    To force a full re-seed, call DELETE /api/v1/admin/seed first (not yet implemented),
    or redeploy the service (Render's ephemeral disk wipes the DB).
    """
    settings = get_settings()

    # Simple auth: admin key must match the app secret
    if x_admin_key != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )

    try:
        # Ensure tables exist
        await init_db()

        async with async_session_maker() as session:
            # Check if already seeded
            result = await session.execute(select(VendorDB).limit(1))
            if result.scalar():
                return {
                    "status": "skipped",
                    "message": "Database already contains data. Redeploy to reset.",
                }

            await run_seed(session)

        logger.info("Database seeded via admin API")
        return {
            "status": "success",
            "message": "Database seeded with demo data.",
        }

    except Exception as e:
        logger.error(f"Seed failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seed failed: {str(e)}",
        )


@router.post("/seed/force", status_code=status.HTTP_200_OK)
async def force_seed_database(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
):
    """
    Force re-seed the database — drops all tables and recreates with fresh demo data.

    Requires the `X-Admin-Key` header to match the app's `SECRET_KEY`.
    WARNING: This destroys all existing data.
    """
    settings = get_settings()

    if x_admin_key != settings.secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin key",
        )

    try:
        from ..db.database import engine
        from ..db.models import Base

        # Drop and recreate all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_maker() as session:
            await run_seed(session)

        logger.info("Database force-reseeded via admin API")
        return {
            "status": "success",
            "message": "Database wiped and reseeded with fresh demo data.",
        }

    except Exception as e:
        logger.error(f"Force seed failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Force seed failed: {str(e)}",
        )

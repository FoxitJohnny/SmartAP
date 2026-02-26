"""Settings API Routes

Provides endpoints for configuring the invoice-to-PO matching algorithm
and the risk detection engine.
"""

from __future__ import annotations

from typing import Annotated, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_session
from ..db.models import MatchingSettingsDB, RiskSettingsDB
from ..models import MatchingSettings, MatchingSettingsUpdate
from ..models.risk_settings import RiskSettings, RiskSettingsUpdate

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


DEFAULT_MATCHING_SETTINGS: Dict[str, Any] = {
    # Vendor matching
    "vendor_fuzzy_threshold": 0.80,
    "vendor_match_weight": 0.30,
    # Amount matching
    "amount_tolerance_percent": 0.20,
    "amount_match_tolerance": 0.05,
    "amount_match_weight": 0.30,
    # Date matching
    "date_tolerance_days": 30,
    "date_match_weight": 0.10,
    # Line items matching
    "line_items_match_weight": 0.30,
    "line_item_description_threshold": 0.70,
    "line_item_amount_tolerance": 0.10,
    # Thresholds
    "exact_match_threshold": 0.95,
    "good_match_threshold": 0.85,
    "acceptable_match_threshold": 0.70,
    "review_threshold": 0.60,
    # AI
    "use_ai_for_ambiguous": True,
    "ai_confidence_threshold": 0.75,
    # Discrepancy policy
    "max_amount_discrepancy_for_auto_approve": 100.0,
    "critical_discrepancy_blocks_approval": True,
}


def _validate_threshold_order(
    exact: float,
    good: float,
    acceptable: float,
    review: float,
) -> None:
    if not (0.0 <= review <= acceptable <= good <= exact <= 1.0):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid threshold ordering. Expected 0 <= review <= acceptable <= good <= exact <= 1. "
                f"Got exact={exact}, good={good}, acceptable={acceptable}, review={review}."
            ),
        )


async def _get_or_create_active_settings(session: AsyncSession) -> MatchingSettingsDB:
    result = await session.execute(
        select(MatchingSettingsDB).where(MatchingSettingsDB.is_active == True)
    )
    settings_db = result.scalars().first()

    if settings_db:
        return settings_db

    settings_db = MatchingSettingsDB(name="active", is_active=True, **DEFAULT_MATCHING_SETTINGS)
    session.add(settings_db)
    await session.flush()
    # Ensure server-default fields (e.g. timestamps) are loaded without implicit IO later
    await session.refresh(settings_db)
    return settings_db


def _to_pydantic(settings_db: MatchingSettingsDB) -> MatchingSettings:
    return MatchingSettings(
        id=settings_db.id,
        name=settings_db.name,
        vendor_fuzzy_threshold=settings_db.vendor_fuzzy_threshold,
        vendor_match_weight=settings_db.vendor_match_weight,
        amount_tolerance_percent=settings_db.amount_tolerance_percent,
        amount_match_tolerance=getattr(settings_db, "amount_match_tolerance", 0.05),
        amount_match_weight=settings_db.amount_match_weight,
        date_tolerance_days=settings_db.date_tolerance_days,
        date_match_weight=settings_db.date_match_weight,
        line_items_match_weight=settings_db.line_items_match_weight,
        line_item_description_threshold=settings_db.line_item_description_threshold,
        line_item_amount_tolerance=settings_db.line_item_amount_tolerance,
        exact_match_threshold=settings_db.exact_match_threshold,
        good_match_threshold=getattr(settings_db, "good_match_threshold", 0.85),
        acceptable_match_threshold=settings_db.acceptable_match_threshold,
        review_threshold=settings_db.review_threshold,
        use_ai_for_ambiguous=settings_db.use_ai_for_ambiguous,
        ai_confidence_threshold=settings_db.ai_confidence_threshold,
        max_amount_discrepancy_for_auto_approve=settings_db.max_amount_discrepancy_for_auto_approve,
        critical_discrepancy_blocks_approval=settings_db.critical_discrepancy_blocks_approval,
        is_active=settings_db.is_active,
        created_at=settings_db.created_at,
        updated_at=settings_db.updated_at,
        updated_by=settings_db.updated_by,
    )


@router.get("/matching", response_model=MatchingSettings, summary="Get active matching settings")
async def get_matching_settings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MatchingSettings:
    settings_db = await _get_or_create_active_settings(session)
    return _to_pydantic(settings_db)


@router.put("/matching", response_model=MatchingSettings, summary="Update matching settings")
async def update_matching_settings(
    payload: MatchingSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MatchingSettings:
    settings_db = await _get_or_create_active_settings(session)

    update_data = payload.model_dump(exclude_unset=True)

    # Validate tolerances
    if "amount_tolerance_percent" in update_data:
        tol = float(update_data["amount_tolerance_percent"])
        if tol > 1.0:
            raise HTTPException(status_code=400, detail="amount_tolerance_percent must be between 0.0 and 1.0")

    if "amount_match_tolerance" in update_data:
        tol = float(update_data["amount_match_tolerance"])
        if tol > 1.0:
            raise HTTPException(status_code=400, detail="amount_match_tolerance must be between 0.0 and 1.0")

    if "line_item_amount_tolerance" in update_data:
        tol = float(update_data["line_item_amount_tolerance"])
        if tol > 1.0:
            raise HTTPException(status_code=400, detail="line_item_amount_tolerance must be between 0.0 and 1.0")

    # Validate threshold ordering (use merged values)
    merged = {
        "exact_match_threshold": float(update_data.get("exact_match_threshold", settings_db.exact_match_threshold)),
        "good_match_threshold": float(update_data.get("good_match_threshold", getattr(settings_db, "good_match_threshold", 0.85))),
        "acceptable_match_threshold": float(update_data.get("acceptable_match_threshold", settings_db.acceptable_match_threshold)),
        "review_threshold": float(update_data.get("review_threshold", settings_db.review_threshold)),
    }
    _validate_threshold_order(
        merged["exact_match_threshold"],
        merged["good_match_threshold"],
        merged["acceptable_match_threshold"],
        merged["review_threshold"],
    )

    for key, value in update_data.items():
        if hasattr(settings_db, key):
            setattr(settings_db, key, value)

    await session.flush()
    # Refresh to load updated server-side fields (e.g. updated_at) without lazy IO
    await session.refresh(settings_db)
    return _to_pydantic(settings_db)


@router.post("/matching/reset", response_model=MatchingSettings, summary="Restore default matching settings")
async def reset_matching_settings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MatchingSettings:
    settings_db = await _get_or_create_active_settings(session)

    for key, value in DEFAULT_MATCHING_SETTINGS.items():
        if hasattr(settings_db, key):
            setattr(settings_db, key, value)

    settings_db.updated_by = None
    await session.flush()
    await session.refresh(settings_db)
    return _to_pydantic(settings_db)


# ============================================================================
# Risk Settings
# ============================================================================

DEFAULT_RISK_SETTINGS: Dict[str, Any] = {
    # Component weights
    "weight_duplicate": 0.25,
    "weight_vendor": 0.20,
    "weight_price": 0.15,
    "weight_amount": 0.10,
    "weight_matching": 0.20,
    "weight_pattern": 0.10,
    # Price anomaly detection
    "price_std_dev_threshold": 2.0,
    "price_min_historical_invoices": 2,
    "price_significant_amount": 1000.0,
    "price_minor_increase": 0.15,
    "price_major_increase": 0.30,
    "price_critical_increase": 0.50,
    # Duplicate detection
    "duplicate_exact_days": 90,
    "duplicate_fuzzy_days": 30,
    "duplicate_amount_tolerance": 0.02,
    # Vendor risk
    "vendor_low_risk_threshold": 0.25,
    "vendor_medium_risk_threshold": 0.50,
    "vendor_high_risk_threshold": 0.75,
    "vendor_good_payment_reliability": 0.90,
    "vendor_acceptable_payment_reliability": 0.75,
    "vendor_inactive_days": 180,
    "vendor_new_vendor_days": 90,
}


async def _get_or_create_active_risk_settings(session: AsyncSession) -> RiskSettingsDB:
    result = await session.execute(
        select(RiskSettingsDB).where(RiskSettingsDB.is_active == True)
    )
    settings_db = result.scalars().first()

    if settings_db:
        return settings_db

    settings_db = RiskSettingsDB(name="active", is_active=True, **DEFAULT_RISK_SETTINGS)
    session.add(settings_db)
    await session.flush()
    await session.refresh(settings_db)
    return settings_db


def _risk_to_pydantic(settings_db: RiskSettingsDB) -> RiskSettings:
    return RiskSettings(
        id=settings_db.id,
        name=settings_db.name,
        # Weights
        weight_duplicate=settings_db.weight_duplicate,
        weight_vendor=settings_db.weight_vendor,
        weight_price=settings_db.weight_price,
        weight_amount=settings_db.weight_amount,
        weight_matching=settings_db.weight_matching,
        weight_pattern=settings_db.weight_pattern,
        # Price anomaly
        price_std_dev_threshold=settings_db.price_std_dev_threshold,
        price_min_historical_invoices=settings_db.price_min_historical_invoices,
        price_significant_amount=settings_db.price_significant_amount,
        price_minor_increase=settings_db.price_minor_increase,
        price_major_increase=settings_db.price_major_increase,
        price_critical_increase=settings_db.price_critical_increase,
        # Duplicate
        duplicate_exact_days=settings_db.duplicate_exact_days,
        duplicate_fuzzy_days=settings_db.duplicate_fuzzy_days,
        duplicate_amount_tolerance=settings_db.duplicate_amount_tolerance,
        # Vendor risk
        vendor_low_risk_threshold=settings_db.vendor_low_risk_threshold,
        vendor_medium_risk_threshold=settings_db.vendor_medium_risk_threshold,
        vendor_high_risk_threshold=settings_db.vendor_high_risk_threshold,
        vendor_good_payment_reliability=settings_db.vendor_good_payment_reliability,
        vendor_acceptable_payment_reliability=settings_db.vendor_acceptable_payment_reliability,
        vendor_inactive_days=settings_db.vendor_inactive_days,
        vendor_new_vendor_days=settings_db.vendor_new_vendor_days,
        # Meta
        is_active=settings_db.is_active,
        created_at=settings_db.created_at,
        updated_at=settings_db.updated_at,
        updated_by=settings_db.updated_by,
    )


@router.get("/risk", response_model=RiskSettings, summary="Get active risk settings")
async def get_risk_settings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RiskSettings:
    settings_db = await _get_or_create_active_risk_settings(session)
    return _risk_to_pydantic(settings_db)


@router.put("/risk", response_model=RiskSettings, summary="Update risk settings")
async def update_risk_settings(
    payload: RiskSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RiskSettings:
    settings_db = await _get_or_create_active_risk_settings(session)

    update_data = payload.model_dump(exclude_unset=True)

    # Validate vendor risk threshold ordering
    merged_low = float(update_data.get("vendor_low_risk_threshold", settings_db.vendor_low_risk_threshold))
    merged_med = float(update_data.get("vendor_medium_risk_threshold", settings_db.vendor_medium_risk_threshold))
    merged_high = float(update_data.get("vendor_high_risk_threshold", settings_db.vendor_high_risk_threshold))
    if not (0.0 <= merged_low <= merged_med <= merged_high <= 1.0):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid vendor risk threshold ordering. "
                f"Expected 0 <= low ({merged_low}) <= medium ({merged_med}) <= high ({merged_high}) <= 1."
            ),
        )

    # Validate price increase threshold ordering
    merged_minor = float(update_data.get("price_minor_increase", settings_db.price_minor_increase))
    merged_major = float(update_data.get("price_major_increase", settings_db.price_major_increase))
    merged_critical = float(update_data.get("price_critical_increase", settings_db.price_critical_increase))
    if not (0.0 <= merged_minor <= merged_major <= merged_critical):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid price increase ordering. "
                f"Expected 0 <= minor ({merged_minor}) <= major ({merged_major}) <= critical ({merged_critical})."
            ),
        )

    for key, value in update_data.items():
        if hasattr(settings_db, key):
            setattr(settings_db, key, value)

    await session.flush()
    await session.refresh(settings_db)
    return _risk_to_pydantic(settings_db)


@router.post("/risk/reset", response_model=RiskSettings, summary="Restore default risk settings")
async def reset_risk_settings(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RiskSettings:
    settings_db = await _get_or_create_active_risk_settings(session)

    for key, value in DEFAULT_RISK_SETTINGS.items():
        if hasattr(settings_db, key):
            setattr(settings_db, key, value)

    settings_db.updated_by = None
    await session.flush()
    await session.refresh(settings_db)
    return _risk_to_pydantic(settings_db)

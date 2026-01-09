"""
Pagination Utilities for SmartAP API

Provides standardized pagination for all list endpoints.
"""

from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field
from fastapi import Query


T = TypeVar("T")


class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    limit: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and limit."""
        return (self.page - 1) * self.limit


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: List[T]
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")
    
    @classmethod
    def create(cls, items: List[T], total: int, page: int, limit: int):
        """Create a paginated response."""
        pages = (total + limit - 1) // limit if limit > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )


def get_pagination_params(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """
    FastAPI dependency for pagination parameters.
    
    Usage:
        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends(get_pagination_params)):
            offset = pagination.offset
            ...
    """
    return PaginationParams(page=page, limit=limit)


# Aliases for backward compatibility
def paginate_query(query, page: int, limit: int):
    """Apply pagination to a SQLAlchemy query."""
    offset = (page - 1) * limit
    return query.offset(offset).limit(limit)

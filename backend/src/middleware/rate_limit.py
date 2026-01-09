"""
Rate Limiting Middleware for SmartAP API

Provides request throttling using Redis or in-memory storage.
"""

import time
import asyncio
from typing import Callable, Dict, Optional
from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10  # Max requests in 1 second


class InMemoryRateLimiter:
    """Simple in-memory rate limiter using sliding window."""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, client_id: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is allowed for client.
        
        Returns:
            (allowed: bool, retry_after: Optional[int])
        """
        async with self._lock:
            now = time.time()
            
            # Clean old entries
            self.requests[client_id] = [
                ts for ts in self.requests[client_id]
                if ts > now - 3600  # Keep last hour
            ]
            
            timestamps = self.requests[client_id]
            
            # Check burst limit (last second)
            recent_second = sum(1 for ts in timestamps if ts > now - 1)
            if recent_second >= self.config.burst_limit:
                return False, 1
            
            # Check per-minute limit
            recent_minute = sum(1 for ts in timestamps if ts > now - 60)
            if recent_minute >= self.config.requests_per_minute:
                return False, 60 - int(now - min(ts for ts in timestamps if ts > now - 60))
            
            # Check per-hour limit
            if len(timestamps) >= self.config.requests_per_hour:
                oldest_in_hour = min(ts for ts in timestamps if ts > now - 3600)
                return False, 3600 - int(now - oldest_in_hour)
            
            # Record this request
            self.requests[client_id].append(now)
            return True, None


class RedisRateLimiter:
    """Redis-based rate limiter for distributed deployments."""
    
    def __init__(self, config: RateLimitConfig, redis_url: str):
        self.config = config
        self.redis_url = redis_url
        self._redis = None
    
    async def _get_redis(self):
        """Lazy initialize Redis connection."""
        if self._redis is None:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    async def is_allowed(self, client_id: str) -> tuple[bool, Optional[int]]:
        """Check if request is allowed using Redis sliding window."""
        try:
            r = await self._get_redis()
            now = time.time()
            
            # Keys for different windows
            minute_key = f"ratelimit:{client_id}:minute"
            hour_key = f"ratelimit:{client_id}:hour"
            
            # Use pipeline for atomic operations
            pipe = r.pipeline()
            
            # Remove old entries and count
            pipe.zremrangebyscore(minute_key, 0, now - 60)
            pipe.zremrangebyscore(hour_key, 0, now - 3600)
            pipe.zcard(minute_key)
            pipe.zcard(hour_key)
            
            results = await pipe.execute()
            minute_count = results[2]
            hour_count = results[3]
            
            # Check limits
            if minute_count >= self.config.requests_per_minute:
                return False, 60
            
            if hour_count >= self.config.requests_per_hour:
                return False, 3600
            
            # Add current request
            pipe = r.pipeline()
            pipe.zadd(minute_key, {str(now): now})
            pipe.zadd(hour_key, {str(now): now})
            pipe.expire(minute_key, 60)
            pipe.expire(hour_key, 3600)
            await pipe.execute()
            
            return True, None
            
        except Exception as e:
            # If Redis fails, allow the request (fail open)
            print(f"Rate limit Redis error: {e}")
            return True, None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Uses Redis if available, falls back to in-memory.
    """
    
    # Paths to exclude from rate limiting
    EXCLUDED_PATHS = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/health/detailed",
    }
    
    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        super().__init__(app)
        self.config = config or RateLimitConfig()
        settings = get_settings()
        
        # Use Redis if enabled, otherwise in-memory
        if settings.redis_enabled:
            self.limiter = RedisRateLimiter(self.config, settings.redis_url)
        else:
            self.limiter = InMemoryRateLimiter(self.config)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use X-Forwarded-For if behind proxy, otherwise client host
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        # Skip rate limiting for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        client_id = self._get_client_id(request)
        allowed, retry_after = await self.limiter.is_allowed(client_id)
        
        if not allowed:
            return Response(
                content='{"detail": "Rate limit exceeded. Please slow down."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Retry-After": str(retry_after or 60),
                    "X-RateLimit-Limit": str(self.config.requests_per_minute),
                    "Content-Type": "application/json",
                },
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.config.requests_per_minute)
        
        return response

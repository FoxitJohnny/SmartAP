"""
Logging Middleware

Provides structured logging for HTTP requests with performance metrics.
"""

import logging
import time
import uuid
from typing import Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variable for request ID (available throughout request lifecycle)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests with structured data.
    
    Logs include:
    - Request ID (for tracing)
    - HTTP method and path
    - Response status code
    - Request duration
    - Client IP
    - User agent
    - Error details (if any)
    """
    
    # Paths to exclude from logging (health checks, etc.)
    EXCLUDED_PATHS = {"/health", "/health/detailed", "/metrics", "/docs", "/redoc", "/openapi.json"}
    
    def __init__(self, app, enable_metrics: bool = True, log_body: bool = False):
        """
        Initialize the logging middleware.
        
        Args:
            app: The ASGI application
            enable_metrics: Whether to record metrics to the collector
            log_body: Whether to log request/response bodies (for debugging)
        """
        super().__init__(app)
        self.enable_metrics = enable_metrics
        self.log_body = log_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details."""
        # Skip logging for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request_id_var.set(request_id)
        
        # Extract request info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "unknown")[:100]
        
        # Start timing
        start_time = time.perf_counter()
        
        # Log request start
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "client_ip": client_ip,
                "user_agent": user_agent,
            }
        )
        
        # Process request
        error_detail = None
        status_code = 500
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            
            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            error_detail = str(e)
            logger.exception(
                "Request error",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": error_detail,
                }
            )
            raise
            
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request completion
            log_level = logging.WARNING if status_code >= 400 else logging.INFO
            logger.log(
                log_level,
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": client_ip,
                    "error": error_detail,
                }
            )
            
            # Record metrics
            if self.enable_metrics:
                try:
                    from ..utils.monitoring import get_metrics_collector
                    collector = get_metrics_collector()
                    collector.record_request(
                        method=request.method,
                        path=request.url.path,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        error=error_detail,
                    )
                except ImportError:
                    pass  # Monitoring module not available
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header (from reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


class StructuredLogFormatter(logging.Formatter):
    """
    Custom log formatter that ensures structured output.
    
    In JSON mode, adds extra fields to the log record.
    In text mode, formats extra fields in a readable way.
    """
    
    def __init__(self, json_mode: bool = False):
        if json_mode:
            super().__init__()
        else:
            super().__init__(
                fmt="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        self.json_mode = json_mode
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        if self.json_mode:
            # Use python-json-logger for JSON output
            try:
                from pythonjsonlogger import jsonlogger
                json_formatter = jsonlogger.JsonFormatter(
                    fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                    rename_fields={
                        "asctime": "timestamp",
                        "name": "logger",
                        "levelname": "level",
                    },
                )
                return json_formatter.format(record)
            except ImportError:
                pass
        
        # Text mode - append extra fields
        base_msg = super().format(record)
        
        # Collect extra fields
        extras = []
        skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'message', 'asctime',
        }
        
        for key, value in record.__dict__.items():
            if key not in skip_fields and value is not None:
                extras.append(f"{key}={value}")
        
        if extras:
            return f"{base_msg} | {' '.join(extras)}"
        
        return base_msg


def configure_structured_logging(log_level: str = "INFO", json_mode: bool = False):
    """
    Configure application-wide structured logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_mode: Whether to output logs in JSON format
    """
    import sys
    
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(StructuredLogFormatter(json_mode=json_mode))
    root_logger.addHandler(console_handler)
    
    # Also configure uvicorn loggers
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = [console_handler]
    
    return root_logger

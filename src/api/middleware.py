"""
API middleware for rate limiting and structured logging.
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
from fastapi import Request, Response
import time
import random
from typing import Callable

from src.config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_PER_MINUTE,
    RATE_LIMIT_PER_HOUR,
    LOG_LEVEL,
    LOG_FILE,
    LOG_ROTATION,
    LOG_RETENTION
)

# =============================================================================
# Rate Limiting
# =============================================================================

# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute", f"{RATE_LIMIT_PER_HOUR}/hour"]
)

def setup_rate_limiting(app):
    """
    Setup rate limiting for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    if not RATE_LIMIT_ENABLED:
        logger.info("Rate limiting is DISABLED")
        return
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    logger.info(f"Rate limiting enabled: {RATE_LIMIT_PER_MINUTE}/min, {RATE_LIMIT_PER_HOUR}/hour")

# =============================================================================
# Structured Logging
# =============================================================================

def setup_logging():
    """
    Setup structured logging with loguru.
    Configures console and file logging with rotation.
    """
    # Remove default logger
    logger.remove()
    
    # Add console logger with colors
    logger.add(
        sink=lambda msg: print(msg, end=""),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True
    )
    
    # Add file logger with rotation
    logger.add(
        sink=LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip"
    )
    
    logger.info(f"Logging configured: level={LOG_LEVEL}, file={LOG_FILE}")

# =============================================================================
# Request Logging Middleware
# =============================================================================

async def log_requests_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to log all API requests with timing and status.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in chain
    
    Returns:
        Response from downstream handler
    """
    # Start timer
    start_time = time.time()
    
    # Log request
    logger.info(f"→ {request.method} {request.url.path} from {request.client.host}")
    
    try:
        # Call next handler
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time

        # Only log ~10% of successful 2xx requests; always log errors and slow requests
        if response.status_code >= 400 or duration > 1.0 or random.random() < 0.1:
            logger.info(
                f"← {request.method} {request.url.path} "
                f"status={response.status_code} duration={duration:.3f}s"
            )
        
        return response
    
    except Exception as e:
        # Log error
        duration = time.time() - start_time
        logger.error(
            f"✗ {request.method} {request.url.path} "
            f"error={type(e).__name__}: {str(e)} duration={duration:.3f}s"
        )
        raise

# =============================================================================
# Error Logging Helper
# =============================================================================

def log_ingestion_error(source: str, error: Exception, context: dict = None):
    """
    Log ingestion errors with structured context.
    
    Args:
        source: Source name (e.g., "telegram", "twitter")
        error: Exception that occurred
        context: Optional additional context (channel, post_id, etc.)
    """
    error_data = {
        "source": source,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    
    logger.error(f"Ingestion error: {source} | {type(error).__name__}: {str(error)}", **error_data)

def log_api_error(endpoint: str, error: Exception, user: str = None):
    """
    Log API errors with structured context.
    
    Args:
        endpoint: API endpoint path
        error: Exception that occurred
        user: Optional username who triggered the error
    """
    error_data = {
        "endpoint": endpoint,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "user": user
    }
    
    logger.error(f"API error: {endpoint} | {type(error).__name__}: {str(error)}", **error_data)

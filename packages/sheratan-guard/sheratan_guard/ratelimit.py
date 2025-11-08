"""Rate limiting middleware for FastAPI"""
import time
from typing import Dict, Optional, Callable
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        # Store: {client_id: {endpoint: [(timestamp, count)]}}
        self._requests: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
        self._cleanup_interval = 300  # Cleanup every 5 minutes
        self._last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Remove old request records to prevent memory buildup"""
        current_time = time.time()
        
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = current_time - 3600  # Keep last hour
        
        for client_id in list(self._requests.keys()):
            for endpoint in list(self._requests[client_id].keys()):
                # Filter out old requests
                self._requests[client_id][endpoint] = [
                    (ts, count) for ts, count in self._requests[client_id][endpoint]
                    if ts > cutoff_time
                ]
                
                # Remove empty endpoints
                if not self._requests[client_id][endpoint]:
                    del self._requests[client_id][endpoint]
            
            # Remove empty clients
            if not self._requests[client_id]:
                del self._requests[client_id]
        
        self._last_cleanup = current_time
        logger.debug("Cleaned up old rate limit records")
    
    def is_allowed(
        self,
        client_id: str,
        endpoint: str,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a request should be allowed
        
        Args:
            client_id: Unique identifier for the client (IP, user ID, etc.)
            endpoint: Endpoint being accessed
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            
        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        self._cleanup_old_requests()
        
        current_time = time.time()
        
        # Get request history for this client and endpoint
        history = self._requests[client_id][endpoint]
        
        # Count requests in the last minute
        minute_ago = current_time - 60
        requests_last_minute = sum(1 for ts, _ in history if ts > minute_ago)
        
        if requests_last_minute >= requests_per_minute:
            return False, f"Rate limit exceeded: {requests_per_minute} requests per minute"
        
        # Count requests in the last hour
        hour_ago = current_time - 3600
        requests_last_hour = sum(1 for ts, _ in history if ts > hour_ago)
        
        if requests_last_hour >= requests_per_hour:
            return False, f"Rate limit exceeded: {requests_per_hour} requests per hour"
        
        # Record this request
        history.append((current_time, 1))
        
        return True, None
    
    def get_usage(self, client_id: str, endpoint: str) -> Dict[str, int]:
        """
        Get current usage statistics for a client and endpoint
        
        Returns:
            Dict with requests_last_minute and requests_last_hour
        """
        current_time = time.time()
        history = self._requests[client_id].get(endpoint, [])
        
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        return {
            "requests_last_minute": sum(1 for ts, _ in history if ts > minute_ago),
            "requests_last_hour": sum(1 for ts, _ in history if ts > hour_ago)
        }


class RateLimitMiddleware:
    """FastAPI middleware for rate limiting"""
    
    def __init__(
        self,
        limiter: RateLimiter,
        get_client_id: Callable = None,
        rate_limit_config: Dict[str, Dict[str, int]] = None
    ):
        """
        Initialize rate limit middleware
        
        Args:
            limiter: RateLimiter instance
            get_client_id: Function to extract client ID from request
            rate_limit_config: Rate limit configuration per endpoint
        """
        self.limiter = limiter
        self.get_client_id = get_client_id or self._default_client_id
        self.rate_limit_config = rate_limit_config or {}
    
    def _default_client_id(self, request) -> str:
        """Default client ID extraction (use IP address)"""
        # Try to get real IP from headers (if behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def __call__(self, request, call_next):
        """Process request with rate limiting"""
        from fastapi import HTTPException, status
        
        # Get client ID
        client_id = self.get_client_id(request)
        
        # Get endpoint path
        endpoint = request.url.path
        
        # Get rate limit config for this endpoint
        endpoint_config = None
        for pattern, config in self.rate_limit_config.items():
            if endpoint.startswith(pattern):
                endpoint_config = config
                break
        
        if endpoint_config is None:
            # Use global defaults
            endpoint_config = self.rate_limit_config.get("global", {
                "requests_per_minute": 100,
                "requests_per_hour": 1000
            })
        
        # Check rate limit
        allowed, reason = self.limiter.is_allowed(
            client_id=client_id,
            endpoint=endpoint,
            requests_per_minute=endpoint_config.get("requests_per_minute", 100),
            requests_per_hour=endpoint_config.get("requests_per_hour", 1000)
        )
        
        if not allowed:
            logger.warning(f"Rate limit exceeded for {client_id} on {endpoint}: {reason}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason
            )
        
        # Get usage stats
        usage = self.limiter.get_usage(client_id, endpoint)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(endpoint_config.get("requests_per_minute", 100))
        response.headers["X-RateLimit-Limit-Hour"] = str(endpoint_config.get("requests_per_hour", 1000))
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            max(0, endpoint_config.get("requests_per_minute", 100) - usage["requests_last_minute"])
        )
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            max(0, endpoint_config.get("requests_per_hour", 1000) - usage["requests_last_hour"])
        )
        
        return response

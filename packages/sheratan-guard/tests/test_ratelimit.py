"""Tests for rate limiting functionality"""
import pytest
import time
from sheratan_guard.ratelimit import RateLimiter


class TestRateLimiter:
    """Test rate limiting"""
    
    def test_allows_first_request(self):
        """Test that first request is allowed"""
        limiter = RateLimiter()
        
        allowed, reason = limiter.is_allowed(
            client_id="test_client",
            endpoint="/test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        
        assert allowed is True
        assert reason is None
    
    def test_allows_within_limit(self):
        """Test that requests within limit are allowed"""
        limiter = RateLimiter()
        
        # Make several requests within limit
        for i in range(5):
            allowed, reason = limiter.is_allowed(
                client_id="test_client",
                endpoint="/test",
                requests_per_minute=10,
                requests_per_hour=100
            )
            assert allowed is True
    
    def test_blocks_exceeding_minute_limit(self):
        """Test that exceeding minute limit blocks requests"""
        limiter = RateLimiter()
        limit = 5
        
        # Fill up the limit
        for i in range(limit):
            allowed, _ = limiter.is_allowed(
                client_id="test_client",
                endpoint="/test",
                requests_per_minute=limit,
                requests_per_hour=100
            )
            assert allowed is True
        
        # Next request should be blocked
        allowed, reason = limiter.is_allowed(
            client_id="test_client",
            endpoint="/test",
            requests_per_minute=limit,
            requests_per_hour=100
        )
        
        assert allowed is False
        assert "per minute" in reason.lower()
    
    def test_different_clients_independent(self):
        """Test that different clients have independent limits"""
        limiter = RateLimiter()
        limit = 2
        
        # Client 1 uses up limit
        for i in range(limit):
            allowed, _ = limiter.is_allowed(
                client_id="client_1",
                endpoint="/test",
                requests_per_minute=limit,
                requests_per_hour=100
            )
            assert allowed is True
        
        # Client 1 blocked
        allowed, _ = limiter.is_allowed(
            client_id="client_1",
            endpoint="/test",
            requests_per_minute=limit,
            requests_per_hour=100
        )
        assert allowed is False
        
        # Client 2 should still be allowed
        allowed, _ = limiter.is_allowed(
            client_id="client_2",
            endpoint="/test",
            requests_per_minute=limit,
            requests_per_hour=100
        )
        assert allowed is True
    
    def test_different_endpoints_independent(self):
        """Test that different endpoints have independent limits"""
        limiter = RateLimiter()
        limit = 2
        
        # Use up limit on endpoint 1
        for i in range(limit):
            allowed, _ = limiter.is_allowed(
                client_id="test_client",
                endpoint="/endpoint1",
                requests_per_minute=limit,
                requests_per_hour=100
            )
            assert allowed is True
        
        # Endpoint 1 blocked
        allowed, _ = limiter.is_allowed(
            client_id="test_client",
            endpoint="/endpoint1",
            requests_per_minute=limit,
            requests_per_hour=100
        )
        assert allowed is False
        
        # Endpoint 2 should still be allowed
        allowed, _ = limiter.is_allowed(
            client_id="test_client",
            endpoint="/endpoint2",
            requests_per_minute=limit,
            requests_per_hour=100
        )
        assert allowed is True
    
    def test_usage_statistics(self):
        """Test getting usage statistics"""
        limiter = RateLimiter()
        
        # Make some requests
        for i in range(3):
            limiter.is_allowed(
                client_id="test_client",
                endpoint="/test",
                requests_per_minute=10,
                requests_per_hour=100
            )
        
        usage = limiter.get_usage("test_client", "/test")
        
        assert usage["requests_last_minute"] == 3
        assert usage["requests_last_hour"] == 3
    
    def test_cleanup_old_requests(self):
        """Test that old requests are cleaned up"""
        limiter = RateLimiter()
        limiter._cleanup_interval = 0  # Force cleanup on every check
        
        # Make a request
        limiter.is_allowed(
            client_id="test_client",
            endpoint="/test",
            requests_per_minute=10,
            requests_per_hour=100
        )
        
        # Manually set old timestamp
        if "test_client" in limiter._requests:
            if "/test" in limiter._requests["test_client"]:
                old_time = time.time() - 7200  # 2 hours ago
                limiter._requests["test_client"]["/test"][0] = (old_time, 1)
        
        # Trigger cleanup
        limiter._cleanup_old_requests()
        
        # Old request should be removed
        usage = limiter.get_usage("test_client", "/test")
        assert usage["requests_last_hour"] == 0
    
    def test_hour_limit(self):
        """Test hour-based rate limiting"""
        limiter = RateLimiter()
        
        # Simulate many requests (would exceed hour limit but not minute)
        # We can't actually wait an hour, so we'll just verify the logic
        allowed, reason = limiter.is_allowed(
            client_id="test_client",
            endpoint="/test",
            requests_per_minute=1000,  # High minute limit
            requests_per_hour=2  # Low hour limit
        )
        assert allowed is True
        
        allowed, reason = limiter.is_allowed(
            client_id="test_client",
            endpoint="/test",
            requests_per_minute=1000,
            requests_per_hour=2
        )
        assert allowed is True
        
        # Third request should exceed hour limit
        allowed, reason = limiter.is_allowed(
            client_id="test_client",
            endpoint="/test",
            requests_per_minute=1000,
            requests_per_hour=2
        )
        assert allowed is False
        assert "per hour" in reason.lower()

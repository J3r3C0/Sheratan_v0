"""Tests for authentication module"""
import pytest
from datetime import timedelta
from sheratan_gateway.auth import (
    create_access_token,
    verify_jwt_token,
    verify_api_key,
)


def test_create_access_token():
    """Test JWT token creation"""
    token = create_access_token(data={"sub": "testuser"})
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_with_expiry():
    """Test JWT token creation with custom expiry"""
    token = create_access_token(
        data={"sub": "testuser"},
        expires_delta=timedelta(minutes=10)
    )
    assert token is not None
    assert isinstance(token, str)


def test_verify_jwt_token_valid():
    """Test JWT token verification with valid token"""
    token = create_access_token(data={"sub": "testuser"})
    token_data = verify_jwt_token(token)
    
    assert token_data is not None
    assert token_data.sub == "testuser"
    assert token_data.exp is not None


def test_verify_jwt_token_invalid():
    """Test JWT token verification with invalid token"""
    token_data = verify_jwt_token("invalid-token")
    assert token_data is None


def test_verify_api_key_empty_list():
    """Test API key verification with no configured keys"""
    import os
    original = os.environ.get("API_KEYS")
    os.environ["API_KEYS"] = ""
    
    # Reload module to pick up env var
    from importlib import reload
    from sheratan_gateway import auth
    reload(auth)
    
    result = auth.verify_api_key("any-key")
    assert result is True  # No keys configured means allow all
    
    # Restore
    if original:
        os.environ["API_KEYS"] = original
    else:
        os.environ.pop("API_KEYS", None)


def test_verify_api_key_valid():
    """Test API key verification with valid key"""
    import os
    original = os.environ.get("API_KEYS")
    os.environ["API_KEYS"] = "test-key-1,test-key-2"
    
    # Reload module to pick up env var
    from importlib import reload
    from sheratan_gateway import auth
    reload(auth)
    
    result = auth.verify_api_key("test-key-1")
    assert result is True
    
    result = auth.verify_api_key("test-key-2")
    assert result is True
    
    # Restore
    if original:
        os.environ["API_KEYS"] = original
    else:
        os.environ.pop("API_KEYS", None)


def test_verify_api_key_invalid():
    """Test API key verification with invalid key"""
    import os
    original = os.environ.get("API_KEYS")
    os.environ["API_KEYS"] = "test-key-1,test-key-2"
    
    # Reload module to pick up env var
    from importlib import reload
    from sheratan_gateway import auth
    reload(auth)
    
    result = auth.verify_api_key("invalid-key")
    assert result is False
    
    # Restore
    if original:
        os.environ["API_KEYS"] = original
    else:
        os.environ.pop("API_KEYS", None)

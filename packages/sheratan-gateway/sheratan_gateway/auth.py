"""Authentication and authorization module"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from pydantic import BaseModel

# Environment variables for authentication
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# API Keys from environment (comma-separated)
API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    """JWT token payload data"""
    sub: str
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model"""
    username: str
    disabled: bool = False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_jwt_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token
    
    Args:
        token: JWT token to verify
    
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(sub=username, exp=payload.get("exp"))
    except JWTError:
        return None


def verify_api_key(api_key: str) -> bool:
    """
    Verify an API key
    
    Args:
        api_key: API key to verify
    
    Returns:
        True if valid, False otherwise
    """
    if not API_KEYS or api_key in API_KEYS:
        return True
    return False


async def get_current_user(
    bearer_token: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header)
) -> User:
    """
    Dependency to get the current authenticated user
    
    Supports both JWT bearer tokens and API keys.
    If no authentication is configured (no API_KEYS and JWT_SECRET_KEY is default),
    allows anonymous access.
    
    Args:
        bearer_token: Optional JWT bearer token
        api_key: Optional API key
    
    Returns:
        User object
    
    Raises:
        HTTPException: If authentication fails
    """
    # Check if authentication is required
    auth_required = bool(API_KEYS) or JWT_SECRET_KEY != "dev-secret-key-change-in-production"
    
    if not auth_required:
        # No authentication configured, allow anonymous access
        return User(username="anonymous")
    
    # Try API key authentication first
    if api_key:
        if verify_api_key(api_key):
            return User(username="api_key_user")
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Try JWT authentication
    if bearer_token:
        token_data = verify_jwt_token(bearer_token.credentials)
        if token_data:
            return User(username=token_data.sub)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to get the current active user
    
    Args:
        current_user: Current user from get_current_user
    
    Returns:
        User object
    
    Raises:
        HTTPException: If user is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

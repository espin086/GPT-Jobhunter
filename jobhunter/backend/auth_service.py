"""
JWT Authentication Service for FastAPI.

This module provides:
- JWT token creation and validation
- FastAPI authentication dependency (get_current_user)
- Password hashing wrappers
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv

from jobhunter.AuthHandler import get_user_by_id, verify_password as verify_password_hash
from passlib.context import CryptContext

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary of data to encode in the token (should include 'sub' with user_id)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"Created access token for user_id: {data.get('sub')}")

    return encoded_jwt


def verify_token(token: str) -> Optional[int]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        user_id if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")

        if user_id is None:
            logger.warning("Token missing 'sub' claim")
            return None

        return int(user_id)

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict:
    """
    FastAPI dependency to get the current authenticated user.

    This function will be used as a dependency in protected endpoints.
    It extracts the token from the Authorization header, verifies it,
    and returns the user information.

    Args:
        token: JWT token from Authorization header (Bearer token)

    Returns:
        User dictionary with all user fields

    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify the token
    user_id = verify_token(token)

    if user_id is None:
        logger.warning("Invalid token - could not extract user_id")
        raise credentials_exception

    # Get user from database
    user = get_user_by_id(user_id=user_id)

    if user is None:
        logger.warning(f"User not found for user_id: {user_id}")
        raise credentials_exception

    # Check if user is active
    if not user.get('is_active'):
        logger.warning(f"Inactive user attempted to authenticate: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    logger.info(f"Authenticated user: {user.get('username')} (ID: {user_id})")
    return user


async def get_current_active_user(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    FastAPI dependency to get current active user (additional layer).

    This is an optional extra dependency if you want double-checking.
    Most endpoints can just use get_current_user directly.

    Args:
        current_user: User dict from get_current_user dependency

    Returns:
        User dictionary

    Raises:
        HTTPException: If user is not active
    """
    if not current_user.get('is_active'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user

"""
Authentication Handler for user management and password operations.

This module handles:
- User CRUD operations
- Password hashing and verification with bcrypt
- Password reset token management
- Database table creation for users and password_reset_tokens
"""

import os
import sqlite3
import logging
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
from passlib.context import CryptContext

from jobhunter import config

logger = logging.getLogger(__name__)

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token expiration time (30 minutes for password reset)
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 30

# Default database path - use centralized config for consistency
DEFAULT_DB_PATH = config.DATABASE


def _prepare_password_for_bcrypt(password: str) -> str:
    """
    Pre-hash password with SHA-256 to support passwords longer than 72 bytes.

    Bcrypt has a 72-byte limit, but we can work around this by:
    1. Hash the password with SHA-256 (produces 32 bytes)
    2. Base64 encode it (produces ~44 characters)
    3. Pass the result to bcrypt

    This allows passwords of any length while maintaining security.

    Args:
        password: The original password (any length)

    Returns:
        Base64-encoded SHA-256 hash suitable for bcrypt
    """
    # Hash with SHA-256
    password_hash = hashlib.sha256(password.encode('utf-8')).digest()
    # Base64 encode to make it ASCII-safe for bcrypt
    return base64.b64encode(password_hash).decode('utf-8')


def _get_db_path(db_path: Optional[str] = None) -> str:
    """Get database path, allowing for test override."""
    if db_path:
        return db_path
    return os.environ.get('TEST_DATABASE', DEFAULT_DB_PATH)


def create_auth_tables(db_path: Optional[str] = None) -> None:
    """
    Create users and password_reset_tokens tables if they don't exist.

    Args:
        db_path: Optional database path (defaults to all_jobs.db or TEST_DATABASE)
    """
    db_path = _get_db_path(db_path)
    logger.info(f"Creating auth tables in database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

        # Create password_reset_tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_token
            ON password_reset_tokens(token)
        """)

        conn.commit()
        logger.info("Auth tables created successfully")

    except Exception as e:
        logger.error(f"Error creating auth tables: {e}")
        raise
    finally:
        conn.close()


def create_user(
    db_path: Optional[str] = None,
    email: str = None,
    username: str = None,
    password: str = None,
    full_name: Optional[str] = None
) -> int:
    """
    Create a new user with hashed password.

    Args:
        db_path: Optional database path
        email: User's email (must be unique)
        username: User's username (must be unique)
        password: Plain text password (will be hashed)
        full_name: Optional full name

    Returns:
        user_id: The ID of the newly created user

    Raises:
        sqlite3.IntegrityError: If email or username already exists
    """
    db_path = _get_db_path(db_path)

    # Pre-hash password to support any length, then bcrypt it
    prepared_password = _prepare_password_for_bcrypt(password)
    hashed_password = pwd_context.hash(prepared_password)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (email, username, hashed_password, full_name)
            VALUES (?, ?, ?, ?)
        """, (email, username, hashed_password, full_name))

        user_id = cursor.lastrowid
        conn.commit()

        logger.info(f"Created user: {username} (ID: {user_id})")
        return user_id

    except sqlite3.IntegrityError as e:
        logger.error(f"User creation failed - duplicate email or username: {e}")
        raise
    finally:
        conn.close()


def get_user_by_email(db_path: Optional[str] = None, email: str = None) -> Optional[Dict]:
    """
    Retrieve user by email address.

    Args:
        db_path: Optional database path
        email: Email address to search for

    Returns:
        User dict with all fields, or None if not found
    """
    db_path = _get_db_path(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    finally:
        conn.close()


def get_user_by_username(db_path: Optional[str] = None, username: str = None) -> Optional[Dict]:
    """
    Retrieve user by username.

    Args:
        db_path: Optional database path
        username: Username to search for

    Returns:
        User dict with all fields, or None if not found
    """
    db_path = _get_db_path(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    finally:
        conn.close()


def get_user_by_id(db_path: Optional[str] = None, user_id: int = None) -> Optional[Dict]:
    """
    Retrieve user by ID.

    Args:
        db_path: Optional database path
        user_id: User ID to search for

    Returns:
        User dict with all fields, or None if not found
    """
    db_path = _get_db_path(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    finally:
        conn.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    # Pre-hash the password the same way we did during creation
    prepared_password = _prepare_password_for_bcrypt(plain_password)
    return pwd_context.verify(prepared_password, hashed_password)


def update_last_login(db_path: Optional[str] = None, user_id: int = None) -> None:
    """
    Update user's last_login timestamp to current time.

    Args:
        db_path: Optional database path
        user_id: User ID to update
    """
    db_path = _get_db_path(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user_id,))

        conn.commit()
        logger.info(f"Updated last login for user ID: {user_id}")

    finally:
        conn.close()


def create_password_reset_token(db_path: Optional[str] = None, user_id: int = None) -> str:
    """
    Generate and store a password reset token for a user.

    Args:
        db_path: Optional database path
        user_id: User ID to create token for

    Returns:
        The reset token string (32-byte hex)
    """
    db_path = _get_db_path(db_path)

    # Generate a secure random token
    token = secrets.token_urlsafe(32)

    # Calculate expiration time (30 minutes from now)
    expires_at = datetime.now() + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO password_reset_tokens (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user_id, token, expires_at.isoformat()))

        conn.commit()
        logger.info(f"Created password reset token for user ID: {user_id}")

        return token

    finally:
        conn.close()


def verify_reset_token(db_path: Optional[str] = None, token: str = None) -> Optional[int]:
    """
    Verify a password reset token is valid and not expired.

    Args:
        db_path: Optional database path
        token: The reset token to verify

    Returns:
        user_id if token is valid, None otherwise
    """
    db_path = _get_db_path(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT user_id, expires_at, used
            FROM password_reset_tokens
            WHERE token = ?
        """, (token,))

        result = cursor.fetchone()

        if not result:
            logger.warning("Reset token not found")
            return None

        user_id, expires_at_str, used = result

        # Check if token has been used
        if used:
            logger.warning("Reset token already used")
            return None

        # Check if token has expired
        expires_at = datetime.fromisoformat(expires_at_str)
        if datetime.now() > expires_at:
            logger.warning("Reset token has expired")
            return None

        return user_id

    finally:
        conn.close()


def reset_password(
    db_path: Optional[str] = None,
    token: str = None,
    new_password: str = None
) -> bool:
    """
    Reset user password using a valid reset token.

    Args:
        db_path: Optional database path
        token: The password reset token
        new_password: The new password to set

    Returns:
        True if password was reset successfully, False otherwise
    """
    db_path = _get_db_path(db_path)

    # Verify the token first
    user_id = verify_reset_token(db_path=db_path, token=token)

    if not user_id:
        logger.error("Password reset failed - invalid or expired token")
        return False

    # Pre-hash the new password to support any length, then bcrypt it
    prepared_password = _prepare_password_for_bcrypt(new_password)
    hashed_password = pwd_context.hash(prepared_password)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Update user's password
        cursor.execute("""
            UPDATE users
            SET hashed_password = ?
            WHERE id = ?
        """, (hashed_password, user_id))

        # Mark token as used
        cursor.execute("""
            UPDATE password_reset_tokens
            SET used = 1
            WHERE token = ?
        """, (token,))

        conn.commit()
        logger.info(f"Password reset successful for user ID: {user_id}")

        return True

    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return False

    finally:
        conn.close()


def get_reset_token_info(db_path: Optional[str] = None, token: str = None) -> Optional[Dict]:
    """
    Get information about a reset token.

    Args:
        db_path: Optional database path
        token: The reset token

    Returns:
        Dict with token info, or None if not found
    """
    db_path = _get_db_path(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT * FROM password_reset_tokens WHERE token = ?
        """, (token,))

        row = cursor.fetchone()

        if row:
            return dict(row)
        return None

    finally:
        conn.close()

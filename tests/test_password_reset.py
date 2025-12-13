"""
Test suite for password reset functionality.

This test file follows TDD principles - write tests first, then implement to pass them.
Tests cover: reset token generation, expiration, usage tracking, and password reset flow.
"""

import os
import sqlite3
import pytest
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

# These imports will work once we implement AuthHandler
from jobhunter.AuthHandler import (
    create_auth_tables,
    create_user,
    get_user_by_id,
    verify_password,
    create_password_reset_token,
    verify_reset_token,
    reset_password,
    get_reset_token_info,
)


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_reset.db")

    os.environ['TEST_DATABASE'] = test_db_path

    yield test_db_path

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    os.rmdir(temp_dir)


def test_create_reset_token(test_db):
    """Test generating a password reset token."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="reset@example.com",
        username="resetuser",
        password="oldpassword123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 20  # Should be a reasonable length token

    # Verify token is in database
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM password_reset_tokens WHERE token = ?", (token,))
    token_record = cursor.fetchone()

    assert token_record is not None
    assert token_record[1] == user_id  # user_id
    assert token_record[2] == token  # token
    assert token_record[4] == 0  # used (not used yet)

    conn.close()


def test_reset_token_expiry(test_db):
    """Test that reset token has correct expiration (30 minutes)."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="expire@example.com",
        username="expireuser",
        password="password123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Check token expiration time
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT expires_at, created_at FROM password_reset_tokens WHERE token = ?",
        (token,)
    )
    result = cursor.fetchone()
    expires_at_str = result[0]
    created_at_str = result[1]

    # Parse timestamps
    expires_at = datetime.fromisoformat(expires_at_str)
    created_at = datetime.fromisoformat(created_at_str)

    # Expiration should be approximately 30 minutes from creation
    time_diff = expires_at - created_at
    assert 29 <= time_diff.total_seconds() / 60 <= 31  # 30 minutes ± 1 minute

    conn.close()


def test_verify_reset_token_valid(test_db):
    """Test verifying a valid, non-expired reset token."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="verify@example.com",
        username="verifyuser",
        password="password123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Verify token
    verified_user_id = verify_reset_token(db_path=test_db, token=token)

    assert verified_user_id is not None
    assert verified_user_id == user_id


def test_verify_reset_token_invalid(test_db):
    """Test verifying an invalid token."""
    create_auth_tables(test_db)

    # Try to verify non-existent token
    verified_user_id = verify_reset_token(
        db_path=test_db,
        token="nonexistent-token-12345"
    )

    assert verified_user_id is None


def test_verify_reset_token_expired(test_db):
    """Test that expired tokens are rejected."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="expired@example.com",
        username="expireduser",
        password="password123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Manually expire the token by setting expires_at to the past
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    past_time = (datetime.now() - timedelta(hours=1)).isoformat()
    cursor.execute(
        "UPDATE password_reset_tokens SET expires_at = ? WHERE token = ?",
        (past_time, token)
    )
    conn.commit()
    conn.close()

    # Try to verify expired token
    verified_user_id = verify_reset_token(db_path=test_db, token=token)

    assert verified_user_id is None


def test_verify_reset_token_already_used(test_db):
    """Test that already-used tokens are rejected."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="used@example.com",
        username="useduser",
        password="password123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Mark token as used
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
        (token,)
    )
    conn.commit()
    conn.close()

    # Try to verify used token
    verified_user_id = verify_reset_token(db_path=test_db, token=token)

    assert verified_user_id is None


def test_reset_password_success(test_db):
    """Test complete password reset flow."""
    create_auth_tables(test_db)

    # Create a user with known password
    old_password = "oldpassword123"
    user_id = create_user(
        db_path=test_db,
        email="complete@example.com",
        username="completeuser",
        password=old_password
    )

    # Get original hashed password
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    old_hashed = user['hashed_password']

    # Verify old password works
    assert verify_password(old_password, old_hashed) is True

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Reset password
    new_password = "newpassword456"
    success = reset_password(db_path=test_db, token=token, new_password=new_password)

    assert success is True

    # Get updated user
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    new_hashed = user['hashed_password']

    # Verify password was changed
    assert new_hashed != old_hashed
    assert verify_password(new_password, new_hashed) is True
    assert verify_password(old_password, new_hashed) is False

    # Verify token is marked as used
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT used FROM password_reset_tokens WHERE token = ?", (token,))
    used = cursor.fetchone()[0]
    assert used == 1
    conn.close()


def test_reset_password_invalid_token(test_db):
    """Test password reset with invalid token fails."""
    create_auth_tables(test_db)

    # Try to reset password with invalid token
    success = reset_password(
        db_path=test_db,
        token="invalid-token-12345",
        new_password="newpassword123"
    )

    assert success is False


def test_reset_password_expired_token(test_db):
    """Test password reset with expired token fails."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="expiredreset@example.com",
        username="expiredresetuser",
        password="password123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Expire the token
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    past_time = (datetime.now() - timedelta(hours=1)).isoformat()
    cursor.execute(
        "UPDATE password_reset_tokens SET expires_at = ? WHERE token = ?",
        (past_time, token)
    )
    conn.commit()
    conn.close()

    # Try to reset password with expired token
    success = reset_password(
        db_path=test_db,
        token=token,
        new_password="newpassword456"
    )

    assert success is False


def test_reset_password_used_token(test_db):
    """Test that token cannot be reused after successful reset."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="reuse@example.com",
        username="reuseuser",
        password="oldpassword123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Reset password first time
    success1 = reset_password(
        db_path=test_db,
        token=token,
        new_password="newpassword456"
    )
    assert success1 is True

    # Try to reuse the same token
    success2 = reset_password(
        db_path=test_db,
        token=token,
        new_password="anotherpassword789"
    )
    assert success2 is False

    # Verify password is still the first new password
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    assert verify_password("newpassword456", user['hashed_password']) is True
    assert verify_password("anotherpassword789", user['hashed_password']) is False


def test_multiple_reset_tokens_same_user(test_db):
    """Test that multiple reset tokens can be generated for same user."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="multiple@example.com",
        username="multipleuser",
        password="password123"
    )

    # Generate first token
    token1 = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Generate second token
    token2 = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Tokens should be different
    assert token1 != token2

    # Both tokens should be valid
    assert verify_reset_token(db_path=test_db, token=token1) == user_id
    assert verify_reset_token(db_path=test_db, token=token2) == user_id

    # Use the second token
    success = reset_password(
        db_path=test_db,
        token=token2,
        new_password="newpassword456"
    )
    assert success is True

    # First token should still be valid (but unused)
    assert verify_reset_token(db_path=test_db, token=token1) == user_id


def test_get_reset_token_info(test_db):
    """Test retrieving reset token information."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="tokeninfo@example.com",
        username="tokeninfouser",
        password="password123"
    )

    # Generate reset token
    token = create_password_reset_token(db_path=test_db, user_id=user_id)

    # Get token info
    token_info = get_reset_token_info(db_path=test_db, token=token)

    assert token_info is not None
    assert token_info['user_id'] == user_id
    assert token_info['token'] == token
    assert token_info['used'] == 0
    assert 'expires_at' in token_info
    assert 'created_at' in token_info

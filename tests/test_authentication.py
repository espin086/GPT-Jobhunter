"""
Test suite for user authentication functionality.

This test file follows TDD principles - write tests first, then implement to pass them.
Tests cover: user CRUD operations, password hashing, and token generation.
"""

import os
import sqlite3
import pytest
from pathlib import Path
import tempfile

# These imports will work once we implement AuthHandler
from jobhunter.AuthHandler import (
    create_auth_tables,
    create_user,
    get_user_by_email,
    get_user_by_username,
    get_user_by_id,
    verify_password,
    update_last_login,
)


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create a temporary directory for test database
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test_auth.db")

    # Store original DATABASE path
    original_db = os.environ.get('TEST_DATABASE', 'all_jobs.db')
    os.environ['TEST_DATABASE'] = test_db_path

    yield test_db_path

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    os.rmdir(temp_dir)
    os.environ['TEST_DATABASE'] = original_db


def test_create_auth_tables(test_db):
    """Test creating users and password_reset_tokens tables with correct schema."""
    # Create the auth tables
    create_auth_tables(test_db)

    # Verify users table exists with correct schema
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()

    # Check users table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    assert cursor.fetchone() is not None, "users table should exist"

    # Check users table schema
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    assert 'id' in columns
    assert 'email' in columns
    assert 'username' in columns
    assert 'hashed_password' in columns
    assert 'full_name' in columns
    assert 'is_active' in columns
    assert 'created_at' in columns
    assert 'last_login' in columns

    # Check password_reset_tokens table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='password_reset_tokens'")
    assert cursor.fetchone() is not None, "password_reset_tokens table should exist"

    conn.close()


def test_create_user(test_db):
    """Test creating a new user with hashed password."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="test@example.com",
        username="testuser",
        password="securepassword123",
        full_name="Test User"
    )

    assert user_id is not None
    assert isinstance(user_id, int)
    assert user_id > 0

    # Verify user was created
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    assert user is not None
    assert user[1] == "test@example.com"  # email
    assert user[2] == "testuser"  # username
    assert user[3] != "securepassword123"  # hashed_password (should be hashed)
    assert user[3].startswith("$2b$")  # bcrypt hash prefix
    assert user[4] == "Test User"  # full_name
    assert user[5] == 1  # is_active (default true)

    conn.close()


def test_user_unique_email(test_db):
    """Test that email must be unique."""
    create_auth_tables(test_db)

    # Create first user
    user_id1 = create_user(
        db_path=test_db,
        email="test@example.com",
        username="testuser1",
        password="password123"
    )
    assert user_id1 is not None

    # Try to create another user with same email
    with pytest.raises(sqlite3.IntegrityError):
        create_user(
            db_path=test_db,
            email="test@example.com",
            username="testuser2",
            password="password456"
        )


def test_user_unique_username(test_db):
    """Test that username must be unique."""
    create_auth_tables(test_db)

    # Create first user
    user_id1 = create_user(
        db_path=test_db,
        email="test1@example.com",
        username="testuser",
        password="password123"
    )
    assert user_id1 is not None

    # Try to create another user with same username
    with pytest.raises(sqlite3.IntegrityError):
        create_user(
            db_path=test_db,
            email="test2@example.com",
            username="testuser",
            password="password456"
        )


def test_get_user_by_email(test_db):
    """Test retrieving user by email."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="lookup@example.com",
        username="lookupuser",
        password="password123",
        full_name="Lookup User"
    )

    # Retrieve user by email
    user = get_user_by_email(db_path=test_db, email="lookup@example.com")

    assert user is not None
    assert user['id'] == user_id
    assert user['email'] == "lookup@example.com"
    assert user['username'] == "lookupuser"
    assert user['full_name'] == "Lookup User"
    assert 'hashed_password' in user
    assert user['is_active'] == 1

    # Test non-existent email
    user_none = get_user_by_email(db_path=test_db, email="nonexistent@example.com")
    assert user_none is None


def test_get_user_by_username(test_db):
    """Test retrieving user by username."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="username@example.com",
        username="findme",
        password="password123"
    )

    # Retrieve user by username
    user = get_user_by_username(db_path=test_db, username="findme")

    assert user is not None
    assert user['id'] == user_id
    assert user['username'] == "findme"
    assert user['email'] == "username@example.com"

    # Test non-existent username
    user_none = get_user_by_username(db_path=test_db, username="nonexistent")
    assert user_none is None


def test_get_user_by_id(test_db):
    """Test retrieving user by ID."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="idtest@example.com",
        username="iduser",
        password="password123"
    )

    # Retrieve user by ID
    user = get_user_by_id(db_path=test_db, user_id=user_id)

    assert user is not None
    assert user['id'] == user_id
    assert user['email'] == "idtest@example.com"

    # Test non-existent ID
    user_none = get_user_by_id(db_path=test_db, user_id=99999)
    assert user_none is None


def test_verify_password(test_db):
    """Test password verification with bcrypt."""
    create_auth_tables(test_db)

    # Create a user with known password
    password = "mySecurePassword123!"
    user_id = create_user(
        db_path=test_db,
        email="pass@example.com",
        username="passuser",
        password=password
    )

    # Get the user to retrieve hashed password
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    hashed_password = user['hashed_password']

    # Verify correct password
    assert verify_password(password, hashed_password) is True

    # Verify incorrect password
    assert verify_password("wrongpassword", hashed_password) is False
    assert verify_password("", hashed_password) is False
    assert verify_password("mySecurePassword", hashed_password) is False


def test_update_last_login(test_db):
    """Test updating user's last_login timestamp."""
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="login@example.com",
        username="loginuser",
        password="password123"
    )

    # Initially last_login should be NULL
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    assert user['last_login'] is None

    # Update last login
    update_last_login(db_path=test_db, user_id=user_id)

    # Verify last_login is now set
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    assert user['last_login'] is not None

    # Store first login time
    first_login = user['last_login']

    # Wait a moment and update again
    import time
    time.sleep(0.1)
    update_last_login(db_path=test_db, user_id=user_id)

    # Verify last_login was updated
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    assert user['last_login'] != first_login


def test_deactivate_user(test_db):
    """Test setting user as inactive."""
    # This will be implemented in AuthHandler
    # For now, we'll test manually
    create_auth_tables(test_db)

    # Create a user
    user_id = create_user(
        db_path=test_db,
        email="deactivate@example.com",
        username="deactiveuser",
        password="password123"
    )

    # User should be active by default
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    assert user['is_active'] == 1

    # Deactivate user manually for now
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    # Verify user is inactive
    user = get_user_by_id(db_path=test_db, user_id=user_id)
    assert user['is_active'] == 0


def test_password_complexity():
    """Test that password hashing works with various password complexities."""
    create_auth_tables(tempfile.mktemp())

    test_passwords = [
        "simple",
        "with spaces",
        "WithNumbers123",
        "Special!@#$%^&*()",
        "Very_Long_Password_With_Many_Characters_123456789!@#$",
        "🔒emoji🔑password",
    ]

    # Import the password hashing function directly
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    for password in test_passwords:
        hashed = pwd_context.hash(password)
        assert pwd_context.verify(password, hashed)
        assert hashed != password
        assert hashed.startswith("$2b$")

"""
Proper pytest unit tests for JWT auth, API key, and admin permission.

These tests run without a live server or MongoDB connection — all DB calls
are mocked via unittest.mock.patch.
"""
from __future__ import annotations
import asyncio
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.api.auth import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_current_admin_user,
    get_current_user,
    get_password_hash,
    verify_password,
    TokenData,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run a coroutine synchronously (no pytest-asyncio dependency needed)."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

class TestPasswordUtils:
    def test_hash_and_verify_success(self):
        hashed = get_password_hash("secret123")
        assert verify_password("secret123", hashed)

    def test_wrong_password_rejected(self):
        hashed = get_password_hash("secret123")
        assert not verify_password("wrongpass", hashed)

    def test_empty_password_hashes_independently(self):
        h1 = get_password_hash("a")
        h2 = get_password_hash("a")
        # bcrypt produces different salts each time
        assert h1 != h2
        assert verify_password("a", h1) and verify_password("a", h2)


# ---------------------------------------------------------------------------
# JWT create / decode
# ---------------------------------------------------------------------------

class TestJWTCreateDecode:
    def test_roundtrip(self):
        token = create_access_token({"sub": "alice", "role": "user"})
        data = decode_access_token(token)
        assert data.username == "alice"
        assert data.role == "user"

    def test_expired_token_raises_401(self):
        token = create_access_token({"sub": "bob"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(HTTPException) as exc:
            decode_access_token(token)
        assert exc.value.status_code == 401

    def test_garbage_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            decode_access_token("not.a.jwt.at.all")
        assert exc.value.status_code == 401

    def test_token_without_sub_raises_401(self):
        # Token has no 'sub' field
        token = create_access_token({"role": "admin"})
        with pytest.raises(HTTPException) as exc:
            decode_access_token(token)
        assert exc.value.status_code == 401

    def test_default_role_is_user(self):
        # Token has sub but no explicit role
        token = create_access_token({"sub": "charlie"})
        data = decode_access_token(token)
        assert data.username == "charlie"
        assert data.role == "user"


# ---------------------------------------------------------------------------
# get_current_user — JWT Bearer path
# ---------------------------------------------------------------------------

class TestGetCurrentUserJWT:
    def test_valid_bearer_token(self):
        token = create_access_token({"sub": "dave", "role": "user"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = run(get_current_user(credentials=creds, api_key=None))
        assert result == "dave"

    def test_invalid_bearer_token_raises_401(self):
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad")
        with pytest.raises(HTTPException) as exc:
            run(get_current_user(credentials=creds, api_key=None))
        assert exc.value.status_code == 401

    def test_expired_bearer_token_raises_401(self):
        token = create_access_token({"sub": "eve"}, expires_delta=timedelta(seconds=-1))
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc:
            run(get_current_user(credentials=creds, api_key=None))
        assert exc.value.status_code == 401

    def test_no_credentials_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            run(get_current_user(credentials=None, api_key=None))
        assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user — API key path
# ---------------------------------------------------------------------------

class TestGetCurrentUserAPIKey:
    def test_valid_api_key_accepted(self):
        with patch("src.api.auth.CONFIGURED_API_KEY", "test-secret-key"):
            result = run(get_current_user(credentials=None, api_key="test-secret-key"))
        assert result == "api_key_user"

    def test_wrong_api_key_falls_through_to_401(self):
        with patch("src.api.auth.CONFIGURED_API_KEY", "test-secret-key"):
            with pytest.raises(HTTPException) as exc:
                run(get_current_user(credentials=None, api_key="wrong-key"))
        assert exc.value.status_code == 401

    def test_api_key_unconfigured_does_not_accept_anything(self):
        # When API_KEY is not set, no api_key value should bypass auth
        with patch("src.api.auth.CONFIGURED_API_KEY", None):
            with pytest.raises(HTTPException) as exc:
                run(get_current_user(credentials=None, api_key="anything"))
        assert exc.value.status_code == 401

    def test_jwt_still_works_when_api_key_present(self):
        """JWT bearer takes precedence correctly when api_key is also sent."""
        token = create_access_token({"sub": "frank", "role": "user"})
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with patch("src.api.auth.CONFIGURED_API_KEY", "other-key"):
            result = run(get_current_user(credentials=creds, api_key="wrong-key"))
        # API key didn't match but JWT is valid → should succeed
        assert result == "frank"


# ---------------------------------------------------------------------------
# get_current_admin_user — role enforcement
# ---------------------------------------------------------------------------

class TestAdminPermission:
    def test_admin_role_allowed(self):
        td = TokenData(username="admin", role="admin")
        result = run(get_current_admin_user(token_data=td))
        assert result == "admin"

    def test_user_role_blocked(self):
        td = TokenData(username="alice", role="user")
        with pytest.raises(HTTPException) as exc:
            run(get_current_admin_user(token_data=td))
        assert exc.value.status_code == 403

    def test_api_key_user_allowed(self):
        # api_key_user is treated as admin regardless of role field
        td = TokenData(username="api_key_user", role="admin")
        result = run(get_current_admin_user(token_data=td))
        assert result == "api_key_user"

    def test_moderator_role_blocked(self):
        td = TokenData(username="mod", role="moderator")
        with pytest.raises(HTTPException) as exc:
            run(get_current_admin_user(token_data=td))
        assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    def test_hardcoded_admin_credentials(self):
        from src.config import ADMIN_USERNAME, ADMIN_PASSWORD
        result = authenticate_user(ADMIN_USERNAME, ADMIN_PASSWORD)
        assert result is not None
        assert result["role"] == "admin"

    def test_wrong_password_returns_none(self):
        from src.config import ADMIN_USERNAME
        result = authenticate_user(ADMIN_USERNAME, "totallyWrong!")
        assert result is None

    def test_unknown_user_returns_none(self):
        mock_col = MagicMock()
        mock_col.find_one.return_value = None
        with patch("src.api.auth.get_users_collection", return_value=mock_col):
            result = authenticate_user("ghost", "pass")
        assert result is None

    def test_db_user_correct_password(self):
        hashed = get_password_hash("userpass")
        mock_doc = {
            "username": "dbuser",
            "password_hash": hashed,
            "role": "user",
            "status": "active",
            "full_name": "DB User",
        }
        mock_col = MagicMock()
        mock_col.find_one.return_value = mock_doc
        with patch("src.api.auth.get_users_collection", return_value=mock_col):
            result = authenticate_user("dbuser", "userpass")
        assert result is not None
        assert result["username"] == "dbuser"
        assert result["role"] == "user"

    def test_db_user_wrong_password(self):
        hashed = get_password_hash("correct")
        mock_doc = {
            "username": "dbuser",
            "password_hash": hashed,
            "role": "user",
            "status": "active",
        }
        mock_col = MagicMock()
        mock_col.find_one.return_value = mock_doc
        with patch("src.api.auth.get_users_collection", return_value=mock_col):
            result = authenticate_user("dbuser", "wrong")
        assert result is None

    def test_banned_user_raises_403(self):
        hashed = get_password_hash("pass")
        mock_doc = {
            "username": "banned",
            "password_hash": hashed,
            "role": "user",
            "status": "banned",
        }
        mock_col = MagicMock()
        mock_col.find_one.return_value = mock_doc
        with patch("src.api.auth.get_users_collection", return_value=mock_col):
            with pytest.raises(HTTPException) as exc:
                authenticate_user("banned", "pass")
        assert exc.value.status_code == 403

    def test_pending_user_raises_403(self):
        hashed = get_password_hash("pass")
        mock_doc = {
            "username": "pending_user",
            "password_hash": hashed,
            "role": "user",
            "status": "pending",
        }
        mock_col = MagicMock()
        mock_col.find_one.return_value = mock_doc
        with patch("src.api.auth.get_users_collection", return_value=mock_col):
            with pytest.raises(HTTPException) as exc:
                authenticate_user("pending_user", "pass")
        assert exc.value.status_code == 403

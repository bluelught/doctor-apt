import pytest
from datetime import timedelta
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token
)


class TestSecurity:
    """Test security functions"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "mysecretpassword123"
        hashed = get_password_hash(password)

        # Hash should be different from original
        assert hashed != password

        # Should verify correctly
        assert verify_password(password, hashed) is True

        # Wrong password should not verify
        assert verify_password("wrongpassword", hashed) is False

    def test_password_hash_uniqueness(self):
        """Test that same password generates different hashes"""
        password = "samepassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

        # But both should verify with original password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_create_access_token(self):
        """Test access token creation"""
        data = {"sub": "testuser", "user_id": 123, "role": "patient"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """Test access token with custom expiry"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta)

        assert token is not None

        # Decode and verify
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_decode_valid_token(self):
        """Test decoding valid token"""
        data = {"sub": "testuser", "user_id": 123, "role": "doctor"}
        token = create_access_token(data)

        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["role"] == "doctor"

    def test_decode_invalid_token(self):
        """Test decoding invalid token"""
        invalid_token = "this.is.not.a.valid.token"
        payload = decode_access_token(invalid_token)
        assert payload is None

    def test_decode_expired_token(self):
        """Test decoding expired token"""
        from freezegun import freeze_time

        # Create token that expires in 1 minute
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=1)
        token = create_access_token(data, expires_delta)

        # Move time forward by 2 minutes
        with freeze_time("2024-01-01 12:00:00") as frozen_time:
            token = create_access_token(data, expires_delta)

            # Token should be valid initially
            payload = decode_access_token(token)
            assert payload is not None

            # Move forward 2 minutes
            frozen_time.move_to("2024-01-01 12:02:00")

            # Token should now be expired
            payload = decode_access_token(token)
            assert payload is None

    def test_token_tampering(self):
        """Test that tampered tokens are rejected"""
        data = {"sub": "testuser", "user_id": 123}
        token = create_access_token(data)

        # JWT tokens have 3 parts separated by dots: header.payload.signature
        # Tampering with any part should invalidate the token
        parts = token.split('.')
        if len(parts) == 3:
            # Tamper with the signature (last part)
            # Change multiple characters to ensure it's invalid
            tampered_signature = parts[2][:-5] + "XXXXX" if len(parts[2]) > 5 else "XXXXX"
            tampered_token = f"{parts[0]}.{parts[1]}.{tampered_signature}"
        else:
            # Fallback: just append garbage
            tampered_token = token + "TAMPERED"

        payload = decode_access_token(tampered_token)
        assert payload is None
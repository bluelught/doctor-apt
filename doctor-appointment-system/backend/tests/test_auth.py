import pytest
from fastapi.testclient import TestClient
from app.models.models import UserRole


class TestAuthentication:
    """Test authentication endpoints"""

    def test_register_patient_success(self, client: TestClient):
        """Test successful patient registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newpatient",
                "email": "newpatient@example.com",
                "full_name": "New Patient",
                "password": "strongpassword123",
                "role": "patient"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newpatient"
        assert data["email"] == "newpatient@example.com"
        assert data["role"] == "patient"
        assert "hashed_password" not in data

    def test_register_doctor_success(self, client: TestClient):
        """Test successful doctor registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newdoctor",
                "email": "newdoctor@example.com",
                "full_name": "Dr. New Doctor",
                "password": "strongpassword123",
                "role": "doctor"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "doctor"

    def test_register_duplicate_username(self, client: TestClient, test_patient):
        """Test registration with duplicate username"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": test_patient.username,
                "email": "different@example.com",
                "full_name": "Different User",
                "password": "password123",
                "role": "patient"
            }
        )
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "full_name": "Test User",
                "password": "password123",
                "role": "patient"
            }
        )
        assert response.status_code == 422

    def test_login_success(self, client: TestClient, test_patient):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_patient.username,
                "password": "password123"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == test_patient.username

        # Check cookie is set
        assert "access_token" in response.cookies

    def test_login_wrong_password(self, client: TestClient, test_patient):
        """Test login with wrong password"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_patient.username,
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123"
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_get_current_user_authenticated(self, client: TestClient, patient_headers):
        """Test getting current user when authenticated"""
        response = client.get("/api/v1/auth/me", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "patient_test"
        assert data["role"] == "patient"

    def test_get_current_user_unauthenticated(self, client: TestClient):
        """Test getting current user when not authenticated"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_logout(self, client: TestClient, patient_headers):
        """Test logout functionality"""
        response = client.post("/api/v1/auth/logout", headers=patient_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

        # Check cookie is deleted - in FastAPI TestClient, deleted cookies have value ''
        assert response.cookies.get("access_token", "") == ""

    def test_invalid_token(self, client: TestClient):
        """Test request with invalid token"""
        headers = {"Cookie": "access_token=invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert "Invalid authentication credentials" in response.json()["detail"]

    def test_inactive_user_login(self, client: TestClient, test_db, test_patient):
        """Test login with inactive user"""
        # Deactivate user
        test_patient.is_active = False
        test_db.commit()

        # Try to login - should fail immediately for inactive users
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": test_patient.username,
                "password": "password123"
            }
        )
        # Login should fail for inactive users
        assert response.status_code == 401
        assert "Inactive user" in response.json()["detail"]
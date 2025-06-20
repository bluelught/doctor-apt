import pytest
from fastapi.testclient import TestClient
from app.models.models import UserRole


class TestUsers:
    """Test user endpoints"""

    def test_get_doctors_list(self, client: TestClient, test_doctor, test_db):
        """Test getting list of all doctors"""
        # Create additional doctor
        from app.models.models import User
        from app.core.security import get_password_hash

        doctor2 = User(
            username="dr_second",
            email="dr.second@example.com",
            full_name="Dr. Second",
            hashed_password=get_password_hash("password123"),
            role=UserRole.DOCTOR
        )
        test_db.add(doctor2)
        test_db.commit()

        response = client.get("/api/v1/users/doctors")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        # Check that only doctors are returned
        assert all(user["role"] == "doctor" for user in data)

        # Check that passwords are not exposed
        assert all("hashed_password" not in user for user in data)

    def test_get_user_by_id_success(self, client: TestClient, test_patient):
        """Test getting user details by ID"""
        response = client.get(f"/api/v1/users/{test_patient.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_patient.id
        assert data["username"] == test_patient.username
        assert data["email"] == test_patient.email
        assert "hashed_password" not in data

    def test_get_user_by_id_not_found(self, client: TestClient):
        """Test getting non-existent user"""
        response = client.get("/api/v1/users/99999")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    def test_doctors_list_no_authentication_required(self, client: TestClient, test_doctor):
        """Test that doctors list doesn't require authentication"""
        # Make request without any authentication headers
        response = client.get("/api/v1/users/doctors")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(d["id"] == test_doctor.id for d in data)
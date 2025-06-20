import pytest
from fastapi.testclient import TestClient
from datetime import date, time, timedelta
from app.models.models import AppointmentStatus
from freezegun import freeze_time


class TestAppointments:
    """Test appointment endpoints"""

    def test_create_appointment_as_patient(self, client: TestClient, patient_headers, test_doctor, test_schedule):
        """Test patient creating an appointment"""
        # Calculate next Tuesday (matching the schedule)
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0:
            days_until_tuesday = 7
        next_tuesday = today + timedelta(days=days_until_tuesday)

        response = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_doctor.id,
                "appointment_date": str(next_tuesday),
                "appointment_time": "10:00:00",
                "reason": "General checkup",
                "duration": 30
            },
            headers=patient_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["doctor_id"] == test_doctor.id
        assert data["appointment_date"] == str(next_tuesday)
        assert data["appointment_time"] == "10:00:00"
        assert data["reason"] == "General checkup"
        assert data["status"] == "scheduled"

    def test_create_appointment_as_doctor_fails(self, client: TestClient, doctor_headers, test_doctor):
        """Test doctor cannot create appointments"""
        response = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_doctor.id,
                "appointment_date": str(date.today() + timedelta(days=7)),
                "appointment_time": "10:00:00",
                "reason": "General checkup"
            },
            headers=doctor_headers
        )
        assert response.status_code == 403
        assert "Only patients can book appointments" in response.json()["detail"]

    def test_create_appointment_past_date_fails(self, client: TestClient, patient_headers, test_doctor):
        """Test creating appointment for past date fails"""
        response = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_doctor.id,
                "appointment_date": str(date.today() - timedelta(days=1)),
                "appointment_time": "10:00:00",
                "reason": "General checkup"
            },
            headers=patient_headers
        )
        assert response.status_code == 422

    def test_create_appointment_no_schedule(self, client: TestClient, patient_headers, test_doctor):
        """Test creating appointment on day without schedule"""
        # Try to book on Sunday (no schedule)
        today = date.today()
        days_until_sunday = (6 - today.weekday()) % 7
        if days_until_sunday == 0:
            days_until_sunday = 7
        next_sunday = today + timedelta(days=days_until_sunday)

        response = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_doctor.id,
                "appointment_date": str(next_sunday),
                "appointment_time": "10:00:00",
                "reason": "General checkup"
            },
            headers=patient_headers
        )
        assert response.status_code == 400
        assert "This time slot is not available" in response.json()["detail"]

    def test_create_appointment_outside_hours(self, client: TestClient, patient_headers, test_doctor, test_schedule):
        """Test creating appointment outside doctor's hours"""
        # Calculate next Tuesday
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0:
            days_until_tuesday = 7
        next_tuesday = today + timedelta(days=days_until_tuesday)

        response = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_doctor.id,
                "appointment_date": str(next_tuesday),
                "appointment_time": "18:00:00",  # After 5 PM
                "reason": "General checkup"
            },
            headers=patient_headers
        )
        assert response.status_code == 400
        assert "This time slot is not available" in response.json()["detail"]

    def test_double_booking_prevention(self, client: TestClient, patient_headers, test_appointment, test_patient):
        """Test that double booking is prevented"""
        # Try to book the same slot
        response = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_appointment.doctor_id,
                "appointment_date": str(test_appointment.appointment_date),
                "appointment_time": str(test_appointment.appointment_time),
                "reason": "Another appointment"
            },
            headers=patient_headers
        )
        assert response.status_code == 400
        assert "This time slot is not available" in response.json()["detail"]

    def test_get_my_appointments_patient(self, client: TestClient, patient_headers, test_appointment):
        """Test patient getting their appointments"""
        response = client.get("/api/v1/appointments/my", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_appointment.id

    def test_get_my_appointments_doctor(self, client: TestClient, doctor_headers, test_appointment):
        """Test doctor getting their appointments"""
        response = client.get("/api/v1/appointments/my", headers=doctor_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_appointment.id

    def test_get_appointment_by_id_as_patient(self, client: TestClient, patient_headers, test_appointment):
        """Test getting specific appointment as patient"""
        response = client.get(f"/api/v1/appointments/{test_appointment.id}", headers=patient_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_appointment.id
        assert data["doctor"]["id"] == test_appointment.doctor_id
        assert data["patient"]["id"] == test_appointment.patient_id

    def test_get_appointment_unauthorized(self, client: TestClient, patient_headers, test_appointment, test_db):
        """Test patient cannot access other patient's appointments"""
        # Create another patient
        from app.models.models import User, UserRole
        from app.core.security import get_password_hash

        other_patient = User(
            username="other_patient",
            email="other@example.com",
            full_name="Other Patient",
            hashed_password=get_password_hash("password123"),
            role=UserRole.PATIENT
        )
        test_db.add(other_patient)
        test_db.commit()

        # Login as other patient
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "other_patient", "password": "password123"}
        )
        other_token = response.json()["access_token"]
        other_headers = {"Cookie": f"access_token={other_token}"}

        # Try to access first patient's appointment
        response = client.get(f"/api/v1/appointments/{test_appointment.id}", headers=other_headers)
        assert response.status_code == 403
        assert "You don't have access to this appointment" in response.json()["detail"]

    def test_update_appointment_as_patient_cancel(self, client: TestClient, patient_headers, test_appointment):
        """Test patient cancelling appointment"""
        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}",
            json={"status": "cancelled"},
            headers=patient_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_update_appointment_as_patient_complete_fails(self, client: TestClient, patient_headers, test_appointment):
        """Test patient cannot mark appointment as completed"""
        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}",
            json={"status": "completed"},
            headers=patient_headers
        )
        assert response.status_code == 403
        assert "Patients can only cancel appointments" in response.json()["detail"]

    def test_update_appointment_as_doctor_complete(self, client: TestClient, doctor_headers, test_appointment):
        """Test doctor marking appointment as completed"""
        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}",
            json={"status": "completed"},
            headers=doctor_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_update_appointment_reschedule(self, client: TestClient, doctor_headers, test_appointment, test_schedule):
        """Test rescheduling appointment"""
        # Calculate another Tuesday (schedule is on Tuesday)
        current_date = test_appointment.appointment_date
        new_date = current_date + timedelta(days=7)  # Next Tuesday

        response = client.put(
            f"/api/v1/appointments/{test_appointment.id}",
            json={
                "appointment_date": str(new_date),
                "appointment_time": "14:00:00"
            },
            headers=doctor_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["appointment_date"] == str(new_date)
        assert data["appointment_time"] == "14:00:00"

    def test_delete_appointment(self, client: TestClient, patient_headers, test_appointment):
        """Test cancelling appointment via DELETE"""
        response = client.delete(f"/api/v1/appointments/{test_appointment.id}", headers=patient_headers)
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]

        # Verify it's cancelled, not deleted
        response = client.get(f"/api/v1/appointments/{test_appointment.id}", headers=patient_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_get_doctor_appointments_with_filter(self, client: TestClient, doctor_headers, test_appointment):
        """Test getting doctor appointments with date filter"""
        response = client.get(
            f"/api/v1/appointments/doctor/{test_appointment.doctor_id}",
            params={"appointment_date": str(test_appointment.appointment_date)},
            headers=doctor_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == test_appointment.id
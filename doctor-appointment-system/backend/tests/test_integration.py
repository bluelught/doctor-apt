import pytest
from fastapi.testclient import TestClient
from datetime import date, time, timedelta


class TestAppointmentBookingFlow:
    """Test complete appointment booking workflow"""

    def test_full_booking_flow(self, client: TestClient, test_db):
        """Test complete flow from registration to appointment booking"""
        # 1. Register doctor
        doctor_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "dr_flow",
                "email": "dr.flow@example.com",
                "full_name": "Dr. Flow Test",
                "password": "password123",
                "role": "doctor"
            }
        )
        assert doctor_response.status_code == 200
        doctor_data = doctor_response.json()

        # 2. Doctor login
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "dr_flow", "password": "password123"}
        )
        assert login_response.status_code == 200
        doctor_token = login_response.json()["access_token"]
        doctor_headers = {"Cookie": f"access_token={doctor_token}"}

        # 3. Doctor sets schedule
        schedule_response = client.post(
            "/api/v1/schedules/",
            json={
                "day_of_week": 3,  # Thursday
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "slot_duration": 30
            },
            headers=doctor_headers
        )
        assert schedule_response.status_code == 200

        # 4. Register patient
        patient_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "patient_flow",
                "email": "patient.flow@example.com",
                "full_name": "Patient Flow Test",
                "password": "password123",
                "role": "patient"
            }
        )
        assert patient_response.status_code == 200

        # 5. Patient login
        patient_login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "patient_flow", "password": "password123"}
        )
        assert patient_login_response.status_code == 200
        patient_token = patient_login_response.json()["access_token"]
        patient_headers = {"Cookie": f"access_token={patient_token}"}

        # 6. Patient views available doctors
        doctors_response = client.get("/api/v1/users/doctors")
        assert doctors_response.status_code == 200
        doctors = doctors_response.json()
        flow_doctor = next(d for d in doctors if d["username"] == "dr_flow")

        # 7. Patient checks available slots
        # Find next Thursday
        today = date.today()
        days_until_thursday = (3 - today.weekday()) % 7
        if days_until_thursday == 0:
            days_until_thursday = 7
        next_thursday = today + timedelta(days=days_until_thursday)

        slots_response = client.get(
            f"/api/v1/schedules/doctor/{flow_doctor['id']}/available-slots",
            params={
                "start_date": str(next_thursday),
                "end_date": str(next_thursday)
            }
        )
        assert slots_response.status_code == 200
        slots = slots_response.json()
        assert len(slots) > 0

        # 8. Patient books appointment
        booking_response = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": flow_doctor["id"],
                "appointment_date": str(next_thursday),
                "appointment_time": "10:00:00",
                "reason": "Initial consultation"
            },
            headers=patient_headers
        )
        assert booking_response.status_code == 200
        appointment = booking_response.json()

        # 9. Verify appointment appears in both doctor and patient views
        patient_appointments = client.get("/api/v1/appointments/my", headers=patient_headers)
        assert patient_appointments.status_code == 200
        assert len(patient_appointments.json()) == 1

        doctor_appointments = client.get("/api/v1/appointments/my", headers=doctor_headers)
        assert doctor_appointments.status_code == 200
        assert len(doctor_appointments.json()) == 1

        # 10. Doctor completes appointment
        complete_response = client.put(
            f"/api/v1/appointments/{appointment['id']}",
            json={"status": "completed"},
            headers=doctor_headers
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"


class TestScheduleConflictScenarios:
    """Test various schedule conflict scenarios"""

    def test_prevent_double_booking_concurrent(self, client: TestClient, test_doctor, test_schedule, test_db):
        """Test preventing double booking in concurrent scenario"""
        # Create two patients
        patients = []
        patient_headers = []

        for i in range(2):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"concurrent_patient_{i}",
                    "email": f"concurrent{i}@example.com",
                    "full_name": f"Concurrent Patient {i}",
                    "password": "password123",
                    "role": "patient"
                }
            )
            assert response.status_code == 200

            login_response = client.post(
                "/api/v1/auth/login",
                json={"username": f"concurrent_patient_{i}", "password": "password123"}
            )
            token = login_response.json()["access_token"]
            patient_headers.append({"Cookie": f"access_token={token}"})

        # Both try to book same slot
        # Find next Tuesday (matching test_schedule)
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0:
            days_until_tuesday = 7
        next_tuesday = today + timedelta(days=days_until_tuesday)

        # First patient books successfully
        response1 = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_doctor.id,
                "appointment_date": str(next_tuesday),
                "appointment_time": "11:00:00",
                "reason": "First appointment"
            },
            headers=patient_headers[0]
        )
        assert response1.status_code == 200

        # Second patient should fail
        response2 = client.post(
            "/api/v1/appointments/",
            json={
                "doctor_id": test_doctor.id,
                "appointment_date": str(next_tuesday),
                "appointment_time": "11:00:00",
                "reason": "Second appointment"
            },
            headers=patient_headers[1]
        )
        assert response2.status_code == 400
        assert "not available" in response2.json()["detail"]

    def test_schedule_modification_with_appointments(self, client: TestClient, doctor_headers, test_schedule,
                                                     test_appointment):
        """Test that schedule modifications respect existing appointments"""
        # Try to deactivate schedule with appointment - should fail
        response = client.put(
            f"/api/v1/schedules/{test_schedule.id}",
            json={"is_active": False},
            headers=doctor_headers
        )
        assert response.status_code == 400
        assert "appointments would be affected" in response.json()["detail"]

        # Try to change schedule to exclude existing appointment time - should fail
        # Test appointment is at 10:00, try to change end time to 09:30
        response = client.put(
            f"/api/v1/schedules/{test_schedule.id}",
            json={"end_time": "09:30:00"},  # Before the 10:00 appointment
            headers=doctor_headers
        )
        assert response.status_code == 400
        assert "appointments would be outside new hours" in response.json()["detail"]


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_api_validation_errors(self, client: TestClient, patient_headers):
        """Test API validation error responses"""
        # Invalid email format
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "not-an-email",
                "full_name": "Test User",
                "password": "pass",
                "role": "patient"
            }
        )
        assert response.status_code == 422
        error = response.json()
        assert "detail" in error
        assert any("email" in str(e).lower() for e in error["detail"])

    def test_unauthorized_access_patterns(self, client: TestClient):
        """Test various unauthorized access patterns"""
        # No authentication
        response = client.get("/api/v1/appointments/my")
        assert response.status_code == 401

        # Invalid token format
        response = client.get(
            "/api/v1/appointments/my",
            headers={"Cookie": "access_token=malformed.token.here"}
        )
        assert response.status_code == 401

        # Empty token
        response = client.get(
            "/api/v1/appointments/my",
            headers={"Cookie": "access_token="}
        )
        assert response.status_code == 401

    def test_database_constraint_violations(self, client: TestClient, doctor_headers, test_schedule):
        """Test handling of database constraint violations"""
        # Try to create duplicate schedule
        response = client.post(
            "/api/v1/schedules/",
            json={
                "day_of_week": test_schedule.day_of_week,
                "start_time": str(test_schedule.start_time),
                "end_time": str(test_schedule.end_time),
                "slot_duration": test_schedule.slot_duration
            },
            headers=doctor_headers
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()
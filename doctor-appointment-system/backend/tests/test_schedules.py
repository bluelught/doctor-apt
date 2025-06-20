import pytest
from fastapi.testclient import TestClient
from datetime import date, time, timedelta


class TestSchedules:
    """Test schedule endpoints"""

    def test_create_schedule_as_doctor(self, client: TestClient, doctor_headers, test_doctor):
        """Test doctor creating a schedule"""
        response = client.post(
            "/api/v1/schedules/",
            json={
                "day_of_week": 3,  # Thursday
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "slot_duration": 30
            },
            headers=doctor_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["day_of_week"] == 3
        assert data["start_time"] == "09:00:00"
        assert data["end_time"] == "17:00:00"
        assert data["slot_duration"] == 30
        assert data["doctor_id"] == test_doctor.id

    def test_create_schedule_as_patient_fails(self, client: TestClient, patient_headers):
        """Test patient cannot create schedules"""
        response = client.post(
            "/api/v1/schedules/",
            json={
                "day_of_week": 3,
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "slot_duration": 30
            },
            headers=patient_headers
        )
        assert response.status_code == 403
        assert "Only doctors can create schedules" in response.json()["detail"]

    def test_create_schedule_invalid_day(self, client: TestClient, doctor_headers):
        """Test creating schedule with invalid day of week"""
        response = client.post(
            "/api/v1/schedules/",
            json={
                "day_of_week": 7,  # Invalid
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "slot_duration": 30
            },
            headers=doctor_headers
        )
        assert response.status_code == 422

    def test_create_schedule_invalid_times(self, client: TestClient, doctor_headers):
        """Test creating schedule with end time before start time"""
        response = client.post(
            "/api/v1/schedules/",
            json={
                "day_of_week": 3,
                "start_time": "17:00:00",
                "end_time": "09:00:00",  # Before start time
                "slot_duration": 30
            },
            headers=doctor_headers
        )
        assert response.status_code == 422

    def test_create_duplicate_schedule(self, client: TestClient, doctor_headers, test_schedule):
        """Test creating duplicate schedule fails"""
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
        assert "already exists" in response.json()["detail"]

    def test_get_my_schedules(self, client: TestClient, doctor_headers, test_schedule):
        """Test doctor getting their schedules"""
        response = client.get("/api/v1/schedules/my", headers=doctor_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["id"] == test_schedule.id for s in data)

    def test_get_my_schedules_as_patient_fails(self, client: TestClient, patient_headers):
        """Test patient cannot get 'my' schedules"""
        response = client.get("/api/v1/schedules/my", headers=patient_headers)
        assert response.status_code == 403
        assert "Only doctors have schedules" in response.json()["detail"]

    def test_get_doctor_schedules_public(self, client: TestClient, test_doctor, test_schedule):
        """Test getting doctor schedules without authentication"""
        response = client.get(f"/api/v1/schedules/doctor/{test_doctor.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(s["id"] == test_schedule.id for s in data)

    def test_get_available_slots(self, client: TestClient, test_doctor, test_schedule):
        """Test getting available slots for a doctor"""
        # Calculate next Tuesday
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0:
            days_until_tuesday = 7
        next_tuesday = today + timedelta(days=days_until_tuesday)

        response = client.get(
            f"/api/v1/schedules/doctor/{test_doctor.id}/available-slots",
            params={
                "start_date": str(next_tuesday),
                "end_date": str(next_tuesday)
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Should have slots for the day (9 AM to 5 PM with 30 min slots = 16 slots)
        assert len(data) == 16
        assert all(slot["date"] == str(next_tuesday) for slot in data)
        assert data[0]["time"] == "09:00:00"
        assert data[-1]["time"] == "16:30:00"

    def test_get_available_slots_with_appointment(self, client: TestClient, test_doctor, test_schedule,
                                                  test_appointment):
        """Test available slots excludes booked appointments"""
        response = client.get(
            f"/api/v1/schedules/doctor/{test_doctor.id}/available-slots",
            params={
                "start_date": str(test_appointment.appointment_date),
                "end_date": str(test_appointment.appointment_date)
            }
        )
        assert response.status_code == 200
        data = response.json()

        # The 10:00 slot should not be available
        times = [slot["time"] for slot in data]
        assert "10:00:00" not in times

    def test_get_available_slots_invalid_date_range(self, client: TestClient, test_doctor):
        """Test available slots with invalid date range"""
        start_date = date.today()
        end_date = start_date - timedelta(days=1)

        response = client.get(
            f"/api/v1/schedules/doctor/{test_doctor.id}/available-slots",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date)
            }
        )
        assert response.status_code == 400
        assert "End date must be after start date" in response.json()["detail"]

    def test_get_available_slots_too_long_range(self, client: TestClient, test_doctor):
        """Test available slots with too long date range"""
        start_date = date.today()
        end_date = start_date + timedelta(days=35)

        response = client.get(
            f"/api/v1/schedules/doctor/{test_doctor.id}/available-slots",
            params={
                "start_date": str(start_date),
                "end_date": str(end_date)
            }
        )
        assert response.status_code == 400
        assert "Date range cannot exceed 30 days" in response.json()["detail"]

    def test_update_schedule(self, client: TestClient, doctor_headers, test_schedule):
        """Test updating a schedule"""
        response = client.put(
            f"/api/v1/schedules/{test_schedule.id}",
            json={
                "end_time": "18:00:00",  # Extend to 6 PM
                "slot_duration": 45  # Change slot duration
            },
            headers=doctor_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["end_time"] == "18:00:00"
        assert data["slot_duration"] == 45

    def test_update_schedule_other_doctor_fails(self, client: TestClient, test_schedule, test_db):
        """Test doctor cannot update another doctor's schedule"""
        # Create another doctor
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "other_doctor",
                "email": "otherdoc@example.com",
                "full_name": "Other Doctor",
                "password": "password123",
                "role": "doctor"
            }
        )
        assert response.status_code == 200

        # Login as other doctor
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "other_doctor", "password": "password123"}
        )
        other_token = response.json()["access_token"]
        other_headers = {"Cookie": f"access_token={other_token}"}

        # Try to update first doctor's schedule
        response = client.put(
            f"/api/v1/schedules/{test_schedule.id}",
            json={"slot_duration": 60},
            headers=other_headers
        )
        assert response.status_code == 403
        assert "You can only update your own schedules" in response.json()["detail"]

    def test_deactivate_schedule_with_appointments_fails(self, client: TestClient, doctor_headers, test_schedule,
                                                         test_appointment):
        """Test deactivating schedule with future appointments fails"""
        response = client.put(
            f"/api/v1/schedules/{test_schedule.id}",
            json={"is_active": False},
            headers=doctor_headers
        )
        assert response.status_code == 400
        assert "appointments would be affected" in response.json()["detail"]

    def test_delete_schedule(self, client: TestClient, doctor_headers, test_doctor):
        """Test deleting a schedule without appointments"""
        # Create a new schedule
        response = client.post(
            "/api/v1/schedules/",
            json={
                "day_of_week": 5,  # Saturday
                "start_time": "10:00:00",
                "end_time": "14:00:00",
                "slot_duration": 30
            },
            headers=doctor_headers
        )
        schedule_id = response.json()["id"]

        # Delete it
        response = client.delete(f"/api/v1/schedules/{schedule_id}", headers=doctor_headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_schedule_with_appointments_fails(self, client: TestClient, doctor_headers, test_schedule,
                                                     test_appointment):
        """Test deleting schedule with future appointments fails"""
        response = client.delete(f"/api/v1/schedules/{test_schedule.id}", headers=doctor_headers)
        assert response.status_code == 400
        assert "appointments would be affected" in response.json()["detail"]
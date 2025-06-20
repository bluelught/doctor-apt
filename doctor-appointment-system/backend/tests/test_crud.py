import pytest
from datetime import date, time, timedelta
from app.crud.crud_user import create_user, get_user_by_username, get_user_by_id, get_all_doctors
from app.crud.crud_appointment import (
    create_appointment, get_appointment, get_appointments_by_patient,
    get_appointments_by_doctor, update_appointment, check_slot_availability
)
from app.crud.crud_schedule import (
    create_schedule, get_schedule, get_schedules_by_doctor,
    update_schedule, get_available_slots
)
from app.schemas.schemas import UserCreate, AppointmentCreate, AppointmentUpdate, ScheduleCreate, ScheduleUpdate
from app.models.models import UserRole, AppointmentStatus


class TestUserCRUD:
    """Test user CRUD operations"""

    def test_create_user(self, test_db):
        """Test creating a user via CRUD"""
        user_data = UserCreate(
            username="crud_user",
            email="crud@example.com",
            full_name="CRUD Test User",
            password="password123",
            role=UserRole.PATIENT
        )

        user = create_user(test_db, user_data)
        assert user.username == "crud_user"
        assert user.email == "crud@example.com"
        assert user.hashed_password != "password123"  # Should be hashed

    def test_get_user_by_username(self, test_db, test_patient):
        """Test getting user by username"""
        user = get_user_by_username(test_db, test_patient.username)
        assert user is not None
        assert user.id == test_patient.id

        # Non-existent user
        user = get_user_by_username(test_db, "nonexistent")
        assert user is None

    def test_get_user_by_id(self, test_db, test_doctor):
        """Test getting user by ID"""
        user = get_user_by_id(test_db, test_doctor.id)
        assert user is not None
        assert user.username == test_doctor.username

        # Non-existent ID
        user = get_user_by_id(test_db, 99999)
        assert user is None

    def test_get_all_doctors(self, test_db, test_doctor, test_patient):
        """Test getting all doctors"""
        doctors = get_all_doctors(test_db)
        assert len(doctors) >= 1
        assert all(d.role == UserRole.DOCTOR for d in doctors)
        assert test_doctor in doctors
        assert test_patient not in doctors


class TestAppointmentCRUD:
    """Test appointment CRUD operations"""

    def test_create_appointment(self, test_db, test_doctor, test_patient):
        """Test creating appointment via CRUD"""
        appointment_data = AppointmentCreate(
            doctor_id=test_doctor.id,
            appointment_date=date.today() + timedelta(days=10),
            appointment_time=time(14, 0),
            reason="CRUD test appointment",
            duration=30
        )

        appointment = create_appointment(test_db, appointment_data, test_patient.id)
        assert appointment.doctor_id == test_doctor.id
        assert appointment.patient_id == test_patient.id
        assert appointment.status == AppointmentStatus.SCHEDULED

    def test_get_appointments_by_patient(self, test_db, test_appointment, test_patient):
        """Test getting appointments by patient"""
        appointments = get_appointments_by_patient(test_db, test_patient.id)
        assert len(appointments) >= 1
        assert test_appointment in appointments

    def test_get_appointments_by_doctor(self, test_db, test_appointment, test_doctor):
        """Test getting appointments by doctor"""
        appointments = get_appointments_by_doctor(test_db, test_doctor.id)
        assert len(appointments) >= 1
        assert test_appointment in appointments

    def test_update_appointment(self, test_db, test_appointment):
        """Test updating appointment"""
        update_data = AppointmentUpdate(
            status=AppointmentStatus.COMPLETED,
            reason="Updated reason"
        )

        updated = update_appointment(test_db, test_appointment.id, update_data)
        assert updated.status == AppointmentStatus.COMPLETED
        assert updated.reason == "Updated reason"

    def test_check_slot_availability(self, test_db, test_doctor, test_schedule, test_appointment):
        """Test checking slot availability"""
        # Booked slot should not be available
        available = check_slot_availability(
            test_db,
            test_doctor.id,
            test_appointment.appointment_date,
            test_appointment.appointment_time
        )
        assert available is False

        # Different time on same day should be available (if within schedule hours)
        available = check_slot_availability(
            test_db,
            test_doctor.id,
            test_appointment.appointment_date,
            time(15, 0)  # 3 PM - within 9-5 schedule
        )
        assert available is True

        # Time outside schedule hours should not be available
        available = check_slot_availability(
            test_db,
            test_doctor.id,
            test_appointment.appointment_date,
            time(18, 0)  # 6 PM - outside schedule
        )
        assert available is False

        # Day without schedule should not be available
        # Find a Sunday (no schedule)
        sunday = test_appointment.appointment_date
        while sunday.weekday() != 6:  # Find next Sunday
            sunday += timedelta(days=1)

        available = check_slot_availability(
            test_db,
            test_doctor.id,
            sunday,
            time(10, 0)
        )
        assert available is False


class TestScheduleCRUD:
    """Test schedule CRUD operations"""

    def test_create_schedule(self, test_db, test_doctor):
        """Test creating schedule via CRUD"""
        schedule_data = ScheduleCreate(
            day_of_week=4,  # Friday
            start_time=time(8, 0),
            end_time=time(12, 0),
            slot_duration=30
        )

        schedule = create_schedule(test_db, schedule_data, test_doctor.id)
        assert schedule.doctor_id == test_doctor.id
        assert schedule.day_of_week == 4
        assert schedule.is_active is True

    def test_get_schedules_by_doctor(self, test_db, test_schedule, test_doctor):
        """Test getting schedules by doctor"""
        schedules = get_schedules_by_doctor(test_db, test_doctor.id)
        assert len(schedules) >= 1
        assert test_schedule in schedules
        assert all(s.is_active for s in schedules)  # Only active schedules

    def test_update_schedule(self, test_db, test_schedule):
        """Test updating schedule"""
        update_data = ScheduleUpdate(
            slot_duration=45,
            end_time=time(18, 0)
        )

        updated = update_schedule(test_db, test_schedule.id, update_data)
        assert updated.slot_duration == 45
        assert updated.end_time == time(18, 0)

    def test_get_available_slots(self, test_db, test_doctor, test_schedule):
        """Test getting available slots"""
        # Get slots for next Tuesday
        today = date.today()
        days_until_tuesday = (1 - today.weekday()) % 7
        if days_until_tuesday == 0:
            days_until_tuesday = 7
        next_tuesday = today + timedelta(days=days_until_tuesday)

        slots = get_available_slots(test_db, test_doctor.id, next_tuesday, next_tuesday)

        # Should have slots from 9 AM to 5 PM with 30 min intervals
        assert len(slots) == 16
        assert all(slot.date == next_tuesday for slot in slots)
        assert slots[0].time == time(9, 0)
        assert slots[-1].time == time(16, 30)

    def test_get_available_slots_multiple_days(self, test_db, test_doctor, test_schedule):
        """Test getting available slots for multiple days"""
        start_date = date.today()
        end_date = start_date + timedelta(days=7)

        slots = get_available_slots(test_db, test_doctor.id, start_date, end_date)

        # Should only have slots on Tuesdays (day_of_week=1)
        tuesday_slots = [slot for slot in slots if slot.date.weekday() == 1]
        assert len(tuesday_slots) > 0

        # No slots on other days
        non_tuesday_slots = [slot for slot in slots if slot.date.weekday() != 1]
        assert len(non_tuesday_slots) == 0
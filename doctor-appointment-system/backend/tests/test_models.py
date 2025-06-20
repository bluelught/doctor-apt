import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy.exc import IntegrityError
from app.models.models import User, UserRole, Schedule, Appointment, AppointmentStatus
from app.core.security import get_password_hash


class TestModels:
    """Test database models and constraints"""

    def test_create_user(self, test_db):
        """Test creating a user"""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.PATIENT
        )
        test_db.add(user)
        test_db.commit()

        assert user.id is not None
        assert user.is_active is True
        assert user.created_at is not None

    def test_user_unique_username(self, test_db, test_patient):
        """Test username uniqueness constraint"""
        duplicate_user = User(
            username=test_patient.username,  # Duplicate
            email="different@example.com",
            full_name="Different User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.PATIENT
        )
        test_db.add(duplicate_user)

        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_user_unique_email(self, test_db, test_patient):
        """Test email uniqueness constraint"""
        duplicate_user = User(
            username="different_username",
            email=test_patient.email,  # Duplicate
            full_name="Different User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.PATIENT
        )
        test_db.add(duplicate_user)

        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_create_schedule(self, test_db, test_doctor):
        """Test creating a schedule"""
        schedule = Schedule(
            doctor_id=test_doctor.id,
            day_of_week=2,  # Wednesday
            start_time=time(8, 0),
            end_time=time(16, 0),
            slot_duration=45
        )
        test_db.add(schedule)
        test_db.commit()

        assert schedule.id is not None
        assert schedule.is_active is True
        assert schedule.created_at is not None
        assert schedule.doctor.id == test_doctor.id

    def test_schedule_unique_constraint(self, test_db, test_schedule):
        """Test schedule uniqueness constraint"""
        duplicate_schedule = Schedule(
            doctor_id=test_schedule.doctor_id,
            day_of_week=test_schedule.day_of_week,
            start_time=test_schedule.start_time,
            end_time=test_schedule.end_time,
            slot_duration=30
        )
        test_db.add(duplicate_schedule)

        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_create_appointment(self, test_db, test_doctor, test_patient):
        """Test creating an appointment"""
        appointment = Appointment(
            doctor_id=test_doctor.id,
            patient_id=test_patient.id,
            appointment_date=date.today() + timedelta(days=14),
            appointment_time=time(11, 0),
            duration=30,
            reason="Follow-up",
            status=AppointmentStatus.SCHEDULED
        )
        test_db.add(appointment)
        test_db.commit()

        assert appointment.id is not None
        assert appointment.created_at is not None
        assert appointment.doctor.id == test_doctor.id
        assert appointment.patient.id == test_patient.id

    def test_appointment_unique_constraint(self, test_db, test_appointment, test_patient):
        """Test appointment slot uniqueness constraint"""
        duplicate_appointment = Appointment(
            doctor_id=test_appointment.doctor_id,
            patient_id=test_patient.id,  # Different patient
            appointment_date=test_appointment.appointment_date,
            appointment_time=test_appointment.appointment_time,
            duration=30,
            reason="Different appointment"
        )
        test_db.add(duplicate_appointment)

        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_appointment_status_enum(self, test_db, test_appointment):
        """Test appointment status enum values"""
        # Valid status changes
        test_appointment.status = AppointmentStatus.COMPLETED
        test_db.commit()
        assert test_appointment.status == AppointmentStatus.COMPLETED

        test_appointment.status = AppointmentStatus.CANCELLED
        test_db.commit()
        assert test_appointment.status == AppointmentStatus.CANCELLED

    def test_user_relationships(self, test_db, test_doctor, test_patient, test_schedule, test_appointment):
        """Test user relationships"""
        # Refresh to load relationships
        test_db.refresh(test_doctor)
        test_db.refresh(test_patient)

        # Doctor relationships
        assert len(test_doctor.doctor_schedules) >= 1
        assert len(test_doctor.doctor_appointments) >= 1
        assert test_schedule in test_doctor.doctor_schedules
        assert test_appointment in test_doctor.doctor_appointments

        # Patient relationships
        assert len(test_patient.patient_appointments) >= 1
        assert test_appointment in test_patient.patient_appointments

    def test_cascade_behavior(self, test_db, test_doctor, test_schedule, test_appointment):
        """Test cascade behaviors"""
        # SQLAlchemy doesn't cascade delete by default for safety
        # This test verifies that we can't delete a doctor with existing appointments
        doctor_id = test_doctor.id

        # Try to delete doctor - should fail due to foreign key constraints
        try:
            test_db.delete(test_doctor)
            test_db.commit()
            assert False, "Should have raised IntegrityError"
        except IntegrityError:
            test_db.rollback()
            # This is expected - can't delete doctor with appointments
            pass

        # Proper way: First delete appointments and schedules
        test_db.delete(test_appointment)
        test_db.delete(test_schedule)
        test_db.commit()

        # Now we can delete the doctor
        test_db.delete(test_doctor)
        test_db.commit()

        # Verify doctor is deleted
        from app.models.models import User as UserModel
        deleted_doctor = test_db.query(UserModel).filter_by(id=doctor_id).first()
        assert deleted_doctor is None
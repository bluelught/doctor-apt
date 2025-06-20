import pytest
import tempfile
import os
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.models import User, UserRole, Schedule, Appointment, AppointmentStatus
from datetime import date, time, datetime, timedelta


# Create temporary database for tests
@pytest.fixture(scope="function")
def test_db():
    """Create a temporary database for testing"""
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    # Create engine with the temporary file
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{temp_file.name}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Cleanup
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        os.unlink(temp_file.name)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with overridden database"""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass  # Don't close here as it's managed by test_db fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_doctor(test_db) -> User:
    """Create a test doctor"""
    doctor = User(
        username="dr_test",
        email="dr.test@example.com",
        full_name="Dr. Test Smith",
        hashed_password=get_password_hash("password123"),
        role=UserRole.DOCTOR,
        is_active=True
    )
    test_db.add(doctor)
    test_db.commit()
    test_db.refresh(doctor)
    return doctor


@pytest.fixture
def test_patient(test_db) -> User:
    """Create a test patient"""
    patient = User(
        username="patient_test",
        email="patient.test@example.com",
        full_name="Test Patient",
        hashed_password=get_password_hash("password123"),
        role=UserRole.PATIENT,
        is_active=True
    )
    test_db.add(patient)
    test_db.commit()
    test_db.refresh(patient)
    return patient


@pytest.fixture
def test_schedule(test_db, test_doctor) -> Schedule:
    """Create a test schedule for doctor"""
    # Make sure it's a future day
    today = date.today()
    # Find next Tuesday
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0:
        days_until_tuesday = 7

    schedule = Schedule(
        doctor_id=test_doctor.id,
        day_of_week=1,  # Tuesday
        start_time=time(9, 0),
        end_time=time(17, 0),
        slot_duration=30,
        is_active=True
    )
    test_db.add(schedule)
    test_db.commit()
    test_db.refresh(schedule)
    return schedule


@pytest.fixture
def test_appointment(test_db, test_doctor, test_patient, test_schedule) -> Appointment:
    """Create a test appointment"""
    # Ensure appointment is on a day that matches the schedule
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7
    if days_until_tuesday == 0:
        days_until_tuesday = 7
    appointment_date = today + timedelta(days=days_until_tuesday)

    appointment = Appointment(
        doctor_id=test_doctor.id,
        patient_id=test_patient.id,
        appointment_date=appointment_date,
        appointment_time=time(10, 0),
        duration=30,
        reason="Regular checkup",
        status=AppointmentStatus.SCHEDULED
    )
    test_db.add(appointment)
    test_db.commit()
    test_db.refresh(appointment)
    return appointment


@pytest.fixture
def doctor_token(client, test_doctor):
    """Get authentication token for doctor"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": test_doctor.username, "password": "password123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def patient_token(client, test_patient):
    """Get authentication token for patient"""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": test_patient.username, "password": "password123"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def doctor_headers(doctor_token):
    """Get headers with doctor authentication"""
    return {"Cookie": f"access_token={doctor_token}"}


@pytest.fixture
def patient_headers(patient_token):
    """Get headers with patient authentication"""
    return {"Cookie": f"access_token={patient_token}"}
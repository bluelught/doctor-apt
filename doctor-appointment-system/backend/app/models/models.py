from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, Time, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from datetime import datetime


class UserRole(str, enum.Enum):
    DOCTOR = "doctor"
    PATIENT = "patient"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    doctor_schedules = relationship("Schedule", back_populates="doctor", foreign_keys="Schedule.doctor_id")
    doctor_appointments = relationship("Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id")
    patient_appointments = relationship("Appointment", back_populates="patient", foreign_keys="Appointment.patient_id")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration = Column(Integer, default=30)  # in minutes
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    doctor = relationship("User", back_populates="doctor_schedules", foreign_keys=[doctor_id])

    # Unique constraint to prevent duplicate schedules
    __table_args__ = (
        UniqueConstraint('doctor_id', 'day_of_week', 'start_time', 'end_time', name='unique_doctor_schedule'),
    )


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)
    duration = Column(Integer, default=30)  # in minutes
    reason = Column(String, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    doctor = relationship("User", back_populates="doctor_appointments", foreign_keys=[doctor_id])
    patient = relationship("User", back_populates="patient_appointments", foreign_keys=[patient_id])

    # Unique constraint to prevent double booking
    __table_args__ = (
        UniqueConstraint('doctor_id', 'appointment_date', 'appointment_time', name='unique_doctor_appointment_slot'),
    )
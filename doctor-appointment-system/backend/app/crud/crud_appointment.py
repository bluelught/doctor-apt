from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import date, time
from app.models.models import Appointment, AppointmentStatus, Schedule
from app.schemas.schemas import AppointmentCreate, AppointmentUpdate


def create_appointment(db: Session, appointment: AppointmentCreate, patient_id: int) -> Appointment:
    try:
        db_appointment = Appointment(
            doctor_id=appointment.doctor_id,
            patient_id=patient_id,
            appointment_date=appointment.appointment_date,
            appointment_time=appointment.appointment_time,
            duration=appointment.duration,
            reason=appointment.reason
        )
        db.add(db_appointment)
        db.commit()
        db.refresh(db_appointment)
        return db_appointment
    except IntegrityError:
        db.rollback()
        raise ValueError("This time slot is already booked")


def get_appointment(db: Session, appointment_id: int) -> Optional[Appointment]:
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()


def get_appointments_by_patient(db: Session, patient_id: int) -> List[Appointment]:
    return db.query(Appointment) \
        .filter(Appointment.patient_id == patient_id) \
        .order_by(Appointment.appointment_date, Appointment.appointment_time) \
        .all()


def get_appointments_by_doctor(db: Session, doctor_id: int) -> List[Appointment]:
    return db.query(Appointment) \
        .filter(Appointment.doctor_id == doctor_id) \
        .order_by(Appointment.appointment_date, Appointment.appointment_time) \
        .all()


def update_appointment(db: Session, appointment_id: int, appointment_update: AppointmentUpdate) -> Appointment:
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        return None

    update_data = appointment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    try:
        db.commit()
        db.refresh(appointment)
        return appointment
    except IntegrityError:
        db.rollback()
        raise ValueError("This time slot is already booked")


def delete_appointment(db: Session, appointment_id: int) -> bool:
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        return False

    db.delete(appointment)
    db.commit()
    return True


def check_slot_availability(
        db: Session,
        doctor_id: int,
        appointment_date: date,
        appointment_time: time,
        exclude_appointment_id: Optional[int] = None
) -> bool:
    """Check if a time slot is available for a doctor"""
    # First check if doctor works on this day
    day_of_week = appointment_date.weekday()

    # Check if there's a schedule for this day
    schedule = db.query(Schedule).filter(
        Schedule.doctor_id == doctor_id,
        Schedule.day_of_week == day_of_week,
        Schedule.is_active == True
    ).first()

    if not schedule:
        return False

    # Check if the time is within the doctor's working hours
    if not (schedule.start_time <= appointment_time < schedule.end_time):
        return False

    # Check if the slot is already booked
    query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.appointment_time == appointment_time,
        Appointment.status != AppointmentStatus.CANCELLED
    )

    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)

    existing_appointment = query.first()

    return existing_appointment is None
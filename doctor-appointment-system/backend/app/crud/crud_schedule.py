from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import date, datetime, timedelta, time
from app.models.models import Schedule, Appointment, AppointmentStatus
from app.schemas.schemas import ScheduleCreate, ScheduleUpdate, AvailableSlot


def create_schedule(db: Session, schedule: ScheduleCreate, doctor_id: int) -> Schedule:
    try:
        db_schedule = Schedule(
            doctor_id=doctor_id,
            day_of_week=schedule.day_of_week,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            slot_duration=schedule.slot_duration
        )
        db.add(db_schedule)
        db.commit()
        db.refresh(db_schedule)
        return db_schedule
    except IntegrityError:
        db.rollback()
        raise ValueError("A schedule already exists for this day and time")


def get_schedule(db: Session, schedule_id: int) -> Optional[Schedule]:
    return db.query(Schedule).filter(Schedule.id == schedule_id).first()


def get_schedules_by_doctor(db: Session, doctor_id: int) -> List[Schedule]:
    return db.query(Schedule) \
        .filter(Schedule.doctor_id == doctor_id, Schedule.is_active == True) \
        .order_by(Schedule.day_of_week, Schedule.start_time) \
        .all()


def update_schedule(db: Session, schedule_id: int, schedule_update: ScheduleUpdate) -> Schedule:
    schedule = get_schedule(db, schedule_id)
    if not schedule:
        return None

    # Check if update would conflict with existing appointments
    update_data = schedule_update.dict(exclude_unset=True)

    # Special handling for deactivation
    if schedule_update.is_active == False:
        # Check if there are future appointments
        today = date.today()
        future_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == schedule.doctor_id,
            Appointment.appointment_date >= today,
            Appointment.status == AppointmentStatus.SCHEDULED
        ).all()

        conflicting_appointments = []
        for apt in future_appointments:
            if apt.appointment_date.weekday() == schedule.day_of_week:
                if schedule.start_time <= apt.appointment_time < schedule.end_time:
                    conflicting_appointments.append(apt)

        if conflicting_appointments:
            raise ValueError(
                f"Cannot deactivate schedule: {len(conflicting_appointments)} appointments would be affected")

    # Check if changing time would conflict with appointments
    if 'start_time' in update_data or 'end_time' in update_data:
        new_start = update_data.get('start_time', schedule.start_time)
        new_end = update_data.get('end_time', schedule.end_time)

        # Check future appointments
        today = date.today()
        future_appointments = db.query(Appointment).filter(
            Appointment.doctor_id == schedule.doctor_id,
            Appointment.appointment_date >= today,
            Appointment.status == AppointmentStatus.SCHEDULED
        ).all()

        conflicting_appointments = []
        for apt in future_appointments:
            if apt.appointment_date.weekday() == schedule.day_of_week:
                # Check if appointment would be outside new hours
                if not (new_start <= apt.appointment_time < new_end):
                    conflicting_appointments.append(apt)

        if conflicting_appointments:
            raise ValueError(
                f"Cannot modify schedule: {len(conflicting_appointments)} appointments would be outside new hours")

    # Apply updates
    for field, value in update_data.items():
        setattr(schedule, field, value)

    try:
        db.commit()
        db.refresh(schedule)
        return schedule
    except IntegrityError:
        db.rollback()
        raise ValueError("A schedule already exists for this day and time")


def delete_schedule(db: Session, schedule_id: int) -> bool:
    schedule = get_schedule(db, schedule_id)
    if not schedule:
        return False

    # Check if there are any appointments linked to this schedule
    today = date.today()
    future_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == schedule.doctor_id,
        Appointment.appointment_date >= today,
        Appointment.status == AppointmentStatus.SCHEDULED
    ).all()

    conflicting_appointments = []
    for apt in future_appointments:
        if apt.appointment_date.weekday() == schedule.day_of_week:
            if schedule.start_time <= apt.appointment_time < schedule.end_time:
                conflicting_appointments.append(apt)

    if conflicting_appointments:
        raise ValueError(f"Cannot delete schedule: {len(conflicting_appointments)} appointments would be affected")

    db.delete(schedule)
    db.commit()
    return True


def get_available_slots(db: Session, doctor_id: int, start_date: date, end_date: date) -> List[AvailableSlot]:
    """Get all available time slots for a doctor within a date range"""
    available_slots = []

    # Get doctor's schedules
    schedules = get_schedules_by_doctor(db, doctor_id)
    if not schedules:
        return available_slots

    # Get all booked appointments in the date range
    booked_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date >= start_date,
        Appointment.appointment_date <= end_date,
        Appointment.status != AppointmentStatus.CANCELLED
    ).all()

    # Create a set of booked slots for quick lookup
    booked_slots = {(apt.appointment_date, apt.appointment_time) for apt in booked_appointments}

    # Iterate through each day in the range
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.weekday()

        # Find schedules for this day of week
        day_schedules = [s for s in schedules if s.day_of_week == day_of_week]

        for schedule in day_schedules:
            # Generate time slots for this schedule
            current_time = schedule.start_time

            while current_time < schedule.end_time:
                # Check if this slot is not booked
                if (current_date, current_time) not in booked_slots:
                    available_slots.append(AvailableSlot(
                        date=current_date,
                        time=current_time,
                        doctor_id=doctor_id
                    ))

                # Move to next slot
                current_datetime = datetime.combine(current_date, current_time)
                next_datetime = current_datetime + timedelta(minutes=schedule.slot_duration)
                current_time = next_datetime.time()

        current_date += timedelta(days=1)

    return available_slots
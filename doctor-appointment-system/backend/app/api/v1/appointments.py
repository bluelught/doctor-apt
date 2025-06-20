from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta
from app.core.database import get_db
from app.schemas.schemas import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from app.models.models import Appointment, AppointmentStatus, UserRole
from app.api.v1.dependencies import get_current_user
from app.crud.crud_appointment import (
    create_appointment, get_appointment, get_appointments_by_patient,
    get_appointments_by_doctor, update_appointment, delete_appointment,
    check_slot_availability
)

router = APIRouter()


@router.post("/", response_model=AppointmentResponse)
def create_new_appointment(
        appointment: AppointmentCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    # Only patients can create appointments
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can book appointments"
        )

    # Check if slot is available
    if not check_slot_availability(db, appointment.doctor_id, appointment.appointment_date,
                                   appointment.appointment_time):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This time slot is not available"
        )

    try:
        return create_appointment(db, appointment, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my", response_model=List[AppointmentResponse])
def get_my_appointments(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    if current_user.role == UserRole.PATIENT:
        return get_appointments_by_patient(db, current_user.id)
    else:  # Doctor
        return get_appointments_by_doctor(db, current_user.id)


@router.get("/doctor/{doctor_id}", response_model=List[AppointmentResponse])
def get_doctor_appointments(
        doctor_id: int,
        appointment_date: date = None,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    # Only doctors can see all appointments, patients can only see their own
    if current_user.role == UserRole.PATIENT and current_user.id != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own appointments"
        )

    appointments = get_appointments_by_doctor(db, doctor_id)

    # Filter by date if provided
    if appointment_date:
        appointments = [a for a in appointments if a.appointment_date == appointment_date]

    return appointments


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment_by_id(
        appointment_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check if user has access to this appointment
    if current_user.role == UserRole.PATIENT and appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this appointment"
        )
    elif current_user.role == UserRole.DOCTOR and appointment.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this appointment"
        )

    return appointment


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment_by_id(
        appointment_id: int,
        appointment_update: AppointmentUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check permissions
    if current_user.role == UserRole.PATIENT:
        if appointment.patient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own appointments"
            )
        # Patients can only cancel appointments
        if appointment_update.status and appointment_update.status != AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients can only cancel appointments"
            )
    elif current_user.role == UserRole.DOCTOR:
        if appointment.doctor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update appointments for your patients"
            )

    # Check if new time slot is available (if changing time)
    if appointment_update.appointment_date or appointment_update.appointment_time:
        new_date = appointment_update.appointment_date or appointment.appointment_date
        new_time = appointment_update.appointment_time or appointment.appointment_time

        if not check_slot_availability(db, appointment.doctor_id, new_date, new_time,
                                       exclude_appointment_id=appointment_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The new time slot is not available"
            )

    return update_appointment(db, appointment_id, appointment_update)


@router.delete("/{appointment_id}")
def cancel_appointment(
        appointment_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    appointment = get_appointment(db, appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check permissions
    if current_user.role == UserRole.PATIENT and appointment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own appointments"
        )
    elif current_user.role == UserRole.DOCTOR and appointment.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel appointments for your patients"
        )

    # Update status to cancelled instead of deleting
    appointment_update = AppointmentUpdate(status=AppointmentStatus.CANCELLED)
    update_appointment(db, appointment_id, appointment_update)

    return {"message": "Appointment cancelled successfully"}
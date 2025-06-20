from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime, timedelta, time
from app.core.database import get_db
from app.schemas.schemas import ScheduleCreate, ScheduleResponse, ScheduleUpdate, AvailableSlot
from app.models.models import Schedule, UserRole
from app.api.v1.dependencies import get_current_user
from app.crud.crud_schedule import (
    create_schedule, get_schedule, get_schedules_by_doctor,
    update_schedule, delete_schedule, get_available_slots
)

router = APIRouter()


@router.post("/", response_model=ScheduleResponse)
def create_doctor_schedule(
        schedule: ScheduleCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    # Only doctors can create schedules
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can create schedules"
        )

    try:
        return create_schedule(db, schedule, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my", response_model=List[ScheduleResponse])
def get_my_schedules(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors have schedules"
        )

    return get_schedules_by_doctor(db, current_user.id)


@router.get("/doctor/{doctor_id}", response_model=List[ScheduleResponse])
def get_doctor_schedules(
        doctor_id: int,
        db: Session = Depends(get_db)
):
    return get_schedules_by_doctor(db, doctor_id)


@router.get("/doctor/{doctor_id}/available-slots", response_model=List[AvailableSlot])
def get_doctor_available_slots(
        doctor_id: int,
        start_date: date = Query(..., description="Start date for availability search"),
        end_date: date = Query(..., description="End date for availability search"),
        db: Session = Depends(get_db)
):
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date"
        )

    if (end_date - start_date).days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 30 days"
        )

    return get_available_slots(db, doctor_id, start_date, end_date)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_doctor_schedule(
        schedule_id: int,
        schedule_update: ScheduleUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    schedule = get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Only the doctor who owns the schedule can update it
    if schedule.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own schedules"
        )

    try:
        updated_schedule = update_schedule(db, schedule_id, schedule_update)
        if not updated_schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )
        return updated_schedule
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{schedule_id}")
def delete_doctor_schedule(
        schedule_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):
    schedule = get_schedule(db, schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Only the doctor who owns the schedule can delete it
    if schedule.doctor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own schedules"
        )

    try:
        delete_schedule(db, schedule_id)
        return {"message": "Schedule deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
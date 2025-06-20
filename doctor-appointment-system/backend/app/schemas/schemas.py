from pydantic import BaseModel, EmailStr, validator
from datetime import date, time, datetime
from typing import Optional, List
from app.models.models import UserRole, AppointmentStatus


# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: UserRole


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Schedule schemas
class ScheduleBase(BaseModel):
    day_of_week: int
    start_time: time
    end_time: time
    slot_duration: int = 30

    @validator('day_of_week')
    def validate_day_of_week(cls, v):
        if not 0 <= v <= 6:
            raise ValueError('Day of week must be between 0 (Monday) and 6 (Sunday)')
        return v

    @validator('end_time')
    def validate_times(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    slot_duration: Optional[int] = None
    is_active: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    id: int
    doctor_id: int
    is_active: bool
    created_at: datetime
    doctor: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# Appointment schemas
class AppointmentBase(BaseModel):
    appointment_date: date
    appointment_time: time
    reason: str
    duration: int = 30

    @validator('appointment_date')
    def validate_future_date(cls, v):
        if v < date.today():
            raise ValueError('Appointment date must be in the future')
        return v


class AppointmentCreate(AppointmentBase):
    doctor_id: int


class AppointmentUpdate(BaseModel):
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    reason: Optional[str] = None
    status: Optional[AppointmentStatus] = None


class AppointmentResponse(AppointmentBase):
    id: int
    doctor_id: int
    patient_id: int
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
    doctor: Optional[UserResponse] = None
    patient: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# Available slot schema
class AvailableSlot(BaseModel):
    date: date
    time: time
    doctor_id: int
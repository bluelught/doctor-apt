from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.schemas.schemas import UserResponse
from app.models.models import UserRole
from app.crud.crud_user import get_all_doctors, get_user_by_id

router = APIRouter()

@router.get("/doctors", response_model=List[UserResponse])
def get_doctors_list(db: Session = Depends(get_db)):
    """Get list of all doctors"""
    return get_all_doctors(db)

@router.get("/{user_id}", response_model=UserResponse)
def get_user_details(user_id: int, db: Session = Depends(get_db)):
    """Get user details by ID"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
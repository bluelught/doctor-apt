from sqlalchemy.orm import Session
from app.models.models import User, UserRole
from app.schemas.schemas import UserCreate
from app.core.security import get_password_hash

def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_username(db: Session, username: str) -> User:
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()

def get_users_by_role(db: Session, role: UserRole, skip: int = 0, limit: int = 100):
    return db.query(User).filter(User.role == role).offset(skip).limit(limit).all()

def get_all_doctors(db: Session):
    return db.query(User).filter(User.role == UserRole.DOCTOR).all()
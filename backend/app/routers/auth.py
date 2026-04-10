from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserRole
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut)
def signup(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    u = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole.user,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.post("/login", response_model=Token)
def login(body: UserCreate, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email).first()
    if not u or not verify_password(body.password, u.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not u.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return Token(access_token=create_access_token(u.email))

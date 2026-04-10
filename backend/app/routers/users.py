from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import User, UserRole
from app.schemas import UserAdminUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("", response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserAdminUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is None and body.is_active is None:
        raise HTTPException(status_code=400, detail="No fields to update")
    if body.role is not None:
        u.role = UserRole(body.role.value)
    if body.is_active is not None:
        u.is_active = body.is_active
    db.commit()
    db.refresh(u)
    return u

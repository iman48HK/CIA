from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import User, UserProfile, UserRole
from app.schemas import UserAdminUpdate, UserOut, UserProfileUpdate
from app.security import hash_password, verify_password

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        display_name=profile.display_name if profile else None,
        avatar_url=profile.avatar_url if profile else None,
    )


@router.patch("/me/profile", response_model=UserOut)
def update_my_profile(
    body: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    new_password = updates.get("new_password")
    current_password = updates.get("current_password")
    next_email = updates.get("email")

    if new_password and not current_password:
        raise HTTPException(status_code=400, detail="Current password is required to set a new password")
    if new_password and not verify_password(str(current_password or ""), user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if new_password:
        user.hashed_password = hash_password(str(new_password))
    if next_email is not None and str(next_email) != user.email:
        exists = db.query(User).filter(User.email == str(next_email)).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = str(next_email)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
    if "display_name" in updates:
        display_name = updates.get("display_name")
        if display_name is None:
            profile.display_name = None
        else:
            profile.display_name = str(display_name).strip() or None
    if "avatar_url" in updates:
        avatar_url = updates.get("avatar_url")
        if avatar_url is None:
            profile.avatar_url = None
        else:
            profile.avatar_url = str(avatar_url).strip() or None
    db.commit()
    db.refresh(user)
    return UserOut(
        id=user.id,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
    )


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

from sqlalchemy.orm import Session

from app.models import User, UserRole
from app.security import hash_password


def seed_if_empty(db: Session) -> None:
    if db.query(User).filter(User.email == "admin@abc.com").first() is None:
        admin = User(
            email="admin@abc.com",
            hashed_password=hash_password("123456"),
            role=UserRole.admin,
            is_active=True,
        )
        user = User(
            email="user@abc.com",
            hashed_password=hash_password("123456"),
            role=UserRole.user,
            is_active=True,
        )
        db.add_all([admin, user])

    db.commit()

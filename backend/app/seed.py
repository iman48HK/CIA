from sqlalchemy.orm import Session

from app.models import OrdinanceFolder, User, UserRole
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

    if db.query(OrdinanceFolder).filter(OrdinanceFolder.code == "ORD1").first() is None:
        db.add(OrdinanceFolder(code="ORD1", name="ORD1"))

    db.commit()

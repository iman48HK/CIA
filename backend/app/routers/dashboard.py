from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Drawing, OrdinanceFile, Project, UploadedFile, User
from app.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    project_ids = [p.id for p in db.query(Project).filter(Project.owner_id == user.id).all()]
    if not project_ids:
        ord_count = db.query(func.count(OrdinanceFile.id)).scalar() or 0
        return DashboardStats(
            project_count=0,
            drawing_count=0,
            uploaded_file_count=0,
            ordinance_file_count=int(ord_count),
        )

    d_count = (
        db.query(func.count(Drawing.id)).filter(Drawing.project_id.in_(project_ids)).scalar() or 0
    )
    f_count = (
        db.query(func.count(UploadedFile.id))
        .filter(UploadedFile.project_id.in_(project_ids))
        .scalar()
        or 0
    )
    ord_count = db.query(func.count(OrdinanceFile.id)).scalar() or 0
    return DashboardStats(
        project_count=len(project_ids),
        drawing_count=int(d_count),
        uploaded_file_count=int(f_count),
        ordinance_file_count=int(ord_count),
    )

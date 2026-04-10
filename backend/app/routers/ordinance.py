from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import OrdinanceFile, OrdinanceFolder, User
from app.schemas import OrdinanceFileOut, OrdinanceFolderOut
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ordinance", tags=["ordinance"])


class OrdinanceFileCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)


@router.get("/folders", response_model=list[OrdinanceFolderOut])
def list_folders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    folders = db.query(OrdinanceFolder).order_by(OrdinanceFolder.id).all()
    out: list[OrdinanceFolderOut] = []
    for f in folders:
        cnt = db.query(OrdinanceFile).filter(OrdinanceFile.folder_id == f.id).count()
        out.append(
            OrdinanceFolderOut(id=f.id, code=f.code, name=f.name, file_count=cnt)
        )
    return out


@router.get("/folders/{folder_id}/files", response_model=list[OrdinanceFileOut])
def list_files(
    folder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    fo = db.query(OrdinanceFolder).filter(OrdinanceFolder.id == folder_id).first()
    if not fo:
        raise HTTPException(status_code=404, detail="Folder not found")
    return (
        db.query(OrdinanceFile)
        .filter(OrdinanceFile.folder_id == folder_id)
        .order_by(OrdinanceFile.id)
        .all()
    )


@router.post("/folders/{folder_id}/files", response_model=OrdinanceFileOut)
def add_ordinance_file(
    folder_id: int,
    body: OrdinanceFileCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    fo = db.query(OrdinanceFolder).filter(OrdinanceFolder.id == folder_id).first()
    if not fo:
        raise HTTPException(status_code=404, detail="Folder not found")
    of = OrdinanceFile(folder_id=folder_id, title=body.title.strip())
    db.add(of)
    db.commit()
    db.refresh(of)
    return of

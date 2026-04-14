from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import OrdinanceFile, OrdinanceFileUploadMeta, OrdinanceFolder, User
from app.schemas import OrdinanceFileOut, OrdinanceFolderOut
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ordinance", tags=["ordinance"])
MAX_FILE_SIZE = 10 * 1024 * 1024
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "storage" / "ordinance_uploads"


class OrdinanceFileCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)


class OrdinanceFolderCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)


class OrdinanceFolderRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


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


@router.post("/folders", response_model=OrdinanceFolderOut)
def create_folder(
    body: OrdinanceFolderCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    exists = db.query(OrdinanceFolder).filter(OrdinanceFolder.code == body.code.strip()).first()
    if exists:
        raise HTTPException(status_code=400, detail="Folder code already exists")
    folder = OrdinanceFolder(code=body.code.strip(), name=body.name.strip())
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return OrdinanceFolderOut(
        id=folder.id, code=folder.code, name=folder.name, file_count=0
    )


@router.patch("/folders/{folder_id}", response_model=OrdinanceFolderOut)
def rename_folder(
    folder_id: int,
    body: OrdinanceFolderRename,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    folder = db.query(OrdinanceFolder).filter(OrdinanceFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    folder.name = body.name.strip()
    db.commit()
    cnt = db.query(OrdinanceFile).filter(OrdinanceFile.folder_id == folder.id).count()
    return OrdinanceFolderOut(id=folder.id, code=folder.code, name=folder.name, file_count=cnt)


@router.delete("/folders/{folder_id}")
def delete_folder(
    folder_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    folder = db.query(OrdinanceFolder).filter(OrdinanceFolder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    db.delete(folder)
    db.commit()
    return {"ok": True}


@router.get("/folders/{folder_id}/files", response_model=list[OrdinanceFileOut])
def list_files(
    folder_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    fo = db.query(OrdinanceFolder).filter(OrdinanceFolder.id == folder_id).first()
    if not fo:
        raise HTTPException(status_code=404, detail="Folder not found")
    rows = (
        db.query(OrdinanceFile)
        .filter(OrdinanceFile.folder_id == folder_id)
        .order_by(OrdinanceFile.id)
        .all()
    )
    out: list[OrdinanceFileOut] = []
    for row in rows:
        meta = (
            db.query(OrdinanceFileUploadMeta)
            .filter(OrdinanceFileUploadMeta.ordinance_file_id == row.id)
            .first()
        )
        out.append(
            OrdinanceFileOut(
                id=row.id,
                folder_id=row.folder_id,
                title=row.title,
                created_at=row.created_at,
                content_type=meta.content_type if meta else None,
                size_bytes=meta.size_bytes if meta else None,
            )
        )
    return out


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


@router.post("/folders/{folder_id}/upload", response_model=list[OrdinanceFileOut])
def upload_ordinance_files(
    folder_id: int,
    files: list[UploadFile] = File(...),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    fo = db.query(OrdinanceFolder).filter(OrdinanceFolder.id == folder_id).first()
    if not fo:
        raise HTTPException(status_code=404, detail="Folder not found")
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    folder_dir = UPLOAD_ROOT / str(folder_id)
    folder_dir.mkdir(parents=True, exist_ok=True)
    created: list[OrdinanceFileOut] = []
    for upload in files:
        if not upload.filename:
            continue
        content = upload.file.read()
        size = len(content)
        if size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Single file size must be <= 10 MB")
        ext = Path(upload.filename).suffix
        disk_name = f"{uuid4().hex}{ext}"
        disk_path = folder_dir / disk_name
        disk_path.write_bytes(content)
        row = OrdinanceFile(folder_id=folder_id, title=upload.filename)
        db.add(row)
        db.flush()
        db.add(
            OrdinanceFileUploadMeta(
                ordinance_file_id=row.id,
                filename=upload.filename,
                file_path=str(disk_path),
                content_type=upload.content_type or "application/octet-stream",
                size_bytes=size,
            )
        )
        created.append(
            OrdinanceFileOut(
                id=row.id,
                folder_id=row.folder_id,
                title=row.title,
                created_at=row.created_at,
                content_type=upload.content_type or "application/octet-stream",
                size_bytes=size,
            )
        )
    db.commit()
    return created


@router.delete("/files/{file_id}")
def delete_ordinance_file(
    file_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    row = db.query(OrdinanceFile).filter(OrdinanceFile.id == file_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ordinance file not found")
    meta = (
        db.query(OrdinanceFileUploadMeta)
        .filter(OrdinanceFileUploadMeta.ordinance_file_id == file_id)
        .first()
    )
    if meta:
        try:
            Path(meta.file_path).unlink(missing_ok=True)
        except OSError:
            pass
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/files/{file_id}/content")
def get_ordinance_file_content(
    file_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(OrdinanceFile).filter(OrdinanceFile.id == file_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Ordinance file not found")
    meta = (
        db.query(OrdinanceFileUploadMeta)
        .filter(OrdinanceFileUploadMeta.ordinance_file_id == file_id)
        .first()
    )
    if not meta:
        raise HTTPException(status_code=404, detail="No uploaded content for this ordinance file")
    path = Path(meta.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Ordinance file missing on disk")
    return FileResponse(path, media_type=meta.content_type, filename=meta.filename)

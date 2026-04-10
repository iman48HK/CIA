from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Drawing, Project, ProjectFolder, UploadedFile, User
from app.schemas import (
    DrawingCreate,
    ProjectCreate,
    ProjectFolderCreate,
    ProjectFolderOut,
    ProjectOut,
    UploadedFileCreate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _project(db: Session, project_id: int, user: User) -> Project:
    p = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _enrich_project(db: Session, p: Project) -> ProjectOut:
    fc = db.query(ProjectFolder).filter(ProjectFolder.project_id == p.id).count()
    dc = db.query(Drawing).filter(Drawing.project_id == p.id).count()
    uc = db.query(UploadedFile).filter(UploadedFile.project_id == p.id).count()
    return ProjectOut(
        id=p.id,
        name=p.name,
        owner_id=p.owner_id,
        created_at=p.created_at,
        folder_count=fc,
        drawing_count=dc,
        file_count=uc,
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.owner_id == user.id).order_by(Project.id.desc()).all()
    return [_enrich_project(db, p) for p in projects]


@router.post("", response_model=ProjectOut)
def create_project(
    body: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    p = Project(name=body.name.strip(), owner_id=user.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _enrich_project(db, p)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _enrich_project(db, _project(db, project_id, user))


@router.get("/{project_id}/folders", response_model=list[ProjectFolderOut])
def list_folders(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _project(db, project_id, user)
    return (
        db.query(ProjectFolder)
        .filter(ProjectFolder.project_id == project_id)
        .order_by(ProjectFolder.id)
        .all()
    )


@router.post("/{project_id}/folders", response_model=ProjectFolderOut)
def create_folder(
    project_id: int,
    body: ProjectFolderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    f = ProjectFolder(project_id=project_id, name=body.name.strip())
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@router.post("/{project_id}/drawings", response_model=dict)
def add_drawing(
    project_id: int,
    body: DrawingCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    d = Drawing(project_id=project_id, title=body.title.strip())
    db.add(d)
    db.commit()
    db.refresh(d)
    return {"id": d.id, "title": d.title, "project_id": d.project_id}


@router.post("/{project_id}/files", response_model=dict)
def add_file(
    project_id: int,
    body: UploadedFileCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    uf = UploadedFile(project_id=project_id, filename=body.filename.strip())
    db.add(uf)
    db.commit()
    db.refresh(uf)
    return {"id": uf.id, "filename": uf.filename, "project_id": uf.project_id}


@router.delete("/{project_id}")
def delete_project(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    p = _project(db, project_id, user)
    db.delete(p)
    db.commit()
    return {"ok": True}

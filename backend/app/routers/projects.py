from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import (
    OrdinanceFile,
    Project,
    ProjectDrawingUpload,
    ProjectFileUpload,
    ProjectFolder,
    ProjectOrdinanceSelection,
    ProjectWorkspaceFolder,
    ProjectWorkspaceLink,
    UploadedFile,
    User,
)
from app.schemas import (
    OrdinanceSelectionRefOut,
    ProjectAnalysisFilesOut,
    ProjectCreate,
    ProjectFolderCreate,
    ProjectFolderOut,
    ProjectOrdinanceSelectionCreate,
    ProjectOut,
    ProjectUploadOut,
    WorkspaceFolderCreate,
    WorkspaceFolderOut,
)

router = APIRouter(prefix="/projects", tags=["projects"])
MAX_FILE_SIZE = 10 * 1024 * 1024
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "storage" / "project_uploads"


def _project(db: Session, project_id: int, user: User) -> Project:
    p = db.query(Project).filter(Project.id == project_id, Project.owner_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _enrich_project(db: Session, p: Project) -> ProjectOut:
    fc = db.query(ProjectFolder).filter(ProjectFolder.project_id == p.id).count()
    dc = db.query(ProjectDrawingUpload).filter(ProjectDrawingUpload.project_id == p.id).count()
    uc = db.query(ProjectFileUpload).filter(ProjectFileUpload.project_id == p.id).count()
    ws_link = db.query(ProjectWorkspaceLink).filter(ProjectWorkspaceLink.project_id == p.id).first()
    ws_folder = (
        db.query(ProjectWorkspaceFolder).filter(ProjectWorkspaceFolder.id == ws_link.workspace_folder_id).first()
        if ws_link
        else None
    )
    return ProjectOut(
        id=p.id,
        name=p.name,
        owner_id=p.owner_id,
        created_at=p.created_at,
        folder_count=fc,
        drawing_count=dc,
        file_count=uc,
        workspace_folder_id=ws_folder.id if ws_folder else None,
        workspace_folder_name=ws_folder.name if ws_folder else None,
    )


def _workspace_folder(db: Session, folder_id: int, user: User) -> ProjectWorkspaceFolder:
    folder = (
        db.query(ProjectWorkspaceFolder)
        .filter(ProjectWorkspaceFolder.id == folder_id, ProjectWorkspaceFolder.owner_id == user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="Workspace folder not found")
    return folder


def _store_upload(project_id: int, upload: UploadFile, category: str) -> tuple[str, int]:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    project_dir = UPLOAD_ROOT / str(project_id) / category
    project_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(upload.filename or "").suffix
    disk_name = f"{uuid4().hex}{ext}"
    disk_path = project_dir / disk_name
    content = upload.file.read()
    size = len(content)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Single file size must be <= 10 MB")
    disk_path.write_bytes(content)
    return str(disk_path), size


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.owner_id == user.id).order_by(Project.id.desc()).all()
    return [_enrich_project(db, p) for p in projects]


@router.post("", response_model=ProjectOut)
def create_project(
    body: ProjectCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    folder = _workspace_folder(db, body.workspace_folder_id, user)
    p = Project(name=body.name.strip(), owner_id=user.id)
    db.add(p)
    db.flush()
    db.add(ProjectWorkspaceLink(project_id=p.id, workspace_folder_id=folder.id))
    db.commit()
    db.refresh(p)
    return _enrich_project(db, p)


@router.get("/by-id/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _enrich_project(db, _project(db, project_id, user))


@router.get("/by-id/{project_id}/folders", response_model=list[ProjectFolderOut])
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


@router.post("/by-id/{project_id}/folders", response_model=ProjectFolderOut)
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


@router.post("/by-id/{project_id}/drawings", response_model=dict)
def add_drawings(
    project_id: int,
    drawings: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    created: list[dict] = []
    for drawing in drawings:
        if not drawing.filename:
            continue
        disk_path, size = _store_upload(project_id, drawing, "drawings")
        row = ProjectDrawingUpload(
            project_id=project_id,
            filename=drawing.filename,
            file_path=disk_path,
            content_type=drawing.content_type or "application/octet-stream",
            size_bytes=size,
        )
        db.add(row)
        db.flush()
        created.append({"id": row.id, "filename": row.filename, "size_bytes": row.size_bytes})
    db.commit()
    return {"project_id": project_id, "items": created}


@router.post("/by-id/{project_id}/files", response_model=dict)
def add_files(
    project_id: int,
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    created: list[dict] = []
    for file in files:
        if not file.filename:
            continue
        disk_path, size = _store_upload(project_id, file, "project_files")
        row = ProjectFileUpload(
            project_id=project_id,
            filename=file.filename,
            file_path=disk_path,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size,
        )
        db.add(row)
        db.flush()
        created.append({"id": row.id, "filename": row.filename, "size_bytes": row.size_bytes})
    db.commit()
    return {"project_id": project_id, "items": created}


@router.get("/workspaces/folders", response_model=list[WorkspaceFolderOut])
def list_workspace_folders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    folders = (
        db.query(ProjectWorkspaceFolder)
        .filter(ProjectWorkspaceFolder.owner_id == user.id)
        .order_by(ProjectWorkspaceFolder.id.desc())
        .all()
    )
    out: list[WorkspaceFolderOut] = []
    for folder in folders:
        cnt = (
            db.query(ProjectWorkspaceLink)
            .filter(ProjectWorkspaceLink.workspace_folder_id == folder.id)
            .count()
        )
        out.append(
            WorkspaceFolderOut(
                id=folder.id,
                owner_id=folder.owner_id,
                name=folder.name,
                created_at=folder.created_at,
                project_count=cnt,
            )
        )
    return out


@router.post("/workspaces/folders", response_model=WorkspaceFolderOut)
def create_workspace_folder(
    body: WorkspaceFolderCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    folder = ProjectWorkspaceFolder(owner_id=user.id, name=body.name.strip())
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return WorkspaceFolderOut(
        id=folder.id,
        owner_id=folder.owner_id,
        name=folder.name,
        created_at=folder.created_at,
        project_count=0,
    )


@router.put("/workspaces/folders/{folder_id}", response_model=WorkspaceFolderOut)
def update_workspace_folder(
    folder_id: int,
    body: WorkspaceFolderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = _workspace_folder(db, folder_id, user)
    folder.name = body.name.strip()
    db.commit()
    db.refresh(folder)
    cnt = db.query(ProjectWorkspaceLink).filter(ProjectWorkspaceLink.workspace_folder_id == folder.id).count()
    return WorkspaceFolderOut(
        id=folder.id,
        owner_id=folder.owner_id,
        name=folder.name,
        created_at=folder.created_at,
        project_count=cnt,
    )


@router.delete("/workspaces/folders/{folder_id}")
def delete_workspace_folder(
    folder_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    folder = _workspace_folder(db, folder_id, user)
    in_use = db.query(ProjectWorkspaceLink).filter(ProjectWorkspaceLink.workspace_folder_id == folder.id).count()
    if in_use > 0:
        raise HTTPException(
            status_code=400,
            detail="Folder contains projects. Move/delete those projects before deleting folder.",
        )
    db.delete(folder)
    db.commit()
    return {"ok": True}


@router.get("/by-id/{project_id}/drawings", response_model=list[ProjectUploadOut])
def list_project_drawings(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _project(db, project_id, user)
    rows = (
        db.query(ProjectDrawingUpload)
        .filter(ProjectDrawingUpload.project_id == project_id)
        .order_by(ProjectDrawingUpload.id.desc())
        .all()
    )
    return [
        ProjectUploadOut(
            id=r.id,
            filename=r.filename,
            content_type=r.content_type,
            size_bytes=r.size_bytes,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/by-id/{project_id}/analysis-files", response_model=ProjectAnalysisFilesOut)
def list_project_analysis_files(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Drawings, project files, and selected ordinance documents for AI analysis context."""
    _project(db, project_id, user)
    drawing_rows = (
        db.query(ProjectDrawingUpload)
        .filter(ProjectDrawingUpload.project_id == project_id)
        .order_by(ProjectDrawingUpload.id.desc())
        .all()
    )
    file_rows = (
        db.query(ProjectFileUpload)
        .filter(ProjectFileUpload.project_id == project_id)
        .order_by(ProjectFileUpload.id.desc())
        .all()
    )
    sel_ids = [
        oid
        for (oid,) in db.query(ProjectOrdinanceSelection.ordinance_file_id)
        .filter(ProjectOrdinanceSelection.project_id == project_id)
        .all()
    ]
    ord_rows = (
        db.query(OrdinanceFile.id, OrdinanceFile.title).filter(OrdinanceFile.id.in_(sel_ids)).all() if sel_ids else []
    )
    return ProjectAnalysisFilesOut(
        drawings=[
            ProjectUploadOut(
                id=r.id,
                filename=r.filename,
                content_type=r.content_type,
                size_bytes=r.size_bytes,
                created_at=r.created_at,
            )
            for r in drawing_rows
        ],
        project_files=[
            ProjectUploadOut(
                id=r.id,
                filename=r.filename,
                content_type=r.content_type,
                size_bytes=r.size_bytes,
                created_at=r.created_at,
            )
            for r in file_rows
        ],
        ordinances=[OrdinanceSelectionRefOut(id=oid, title=title) for oid, title in ord_rows],
    )


@router.delete("/by-id/{project_id}/drawings/{drawing_id}")
def delete_project_drawing(
    project_id: int,
    drawing_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    row = (
        db.query(ProjectDrawingUpload)
        .filter(ProjectDrawingUpload.project_id == project_id, ProjectDrawingUpload.id == drawing_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Drawing upload not found")
    try:
        Path(row.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/by-id/{project_id}/drawings/{drawing_id}/content")
def get_project_drawing_content(
    project_id: int,
    drawing_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    row = (
        db.query(ProjectDrawingUpload)
        .filter(ProjectDrawingUpload.project_id == project_id, ProjectDrawingUpload.id == drawing_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Drawing upload not found")
    path = Path(row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Drawing file missing on disk")
    return FileResponse(path, media_type=row.content_type, filename=row.filename)


@router.get("/by-id/{project_id}/project-files", response_model=list[ProjectUploadOut])
def list_project_files(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _project(db, project_id, user)
    rows = (
        db.query(ProjectFileUpload)
        .filter(ProjectFileUpload.project_id == project_id)
        .order_by(ProjectFileUpload.id.desc())
        .all()
    )
    return [
        ProjectUploadOut(
            id=r.id,
            filename=r.filename,
            content_type=r.content_type,
            size_bytes=r.size_bytes,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/by-id/{project_id}/project-files/{file_id}")
def delete_project_file(
    project_id: int,
    file_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    row = (
        db.query(ProjectFileUpload)
        .filter(ProjectFileUpload.project_id == project_id, ProjectFileUpload.id == file_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Project file not found")
    try:
        Path(row.file_path).unlink(missing_ok=True)
    except OSError:
        pass
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/by-id/{project_id}/project-files/{file_id}/content")
def get_project_file_content(
    project_id: int,
    file_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    row = (
        db.query(ProjectFileUpload)
        .filter(ProjectFileUpload.project_id == project_id, ProjectFileUpload.id == file_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Project file not found")
    path = Path(row.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Project file missing on disk")
    return FileResponse(path, media_type=row.content_type, filename=row.filename)


@router.get("/by-id/{project_id}/ordinance-selections", response_model=list[int])
def list_project_ordinance_selections(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _project(db, project_id, user)
    rows = (
        db.query(ProjectOrdinanceSelection)
        .filter(ProjectOrdinanceSelection.project_id == project_id)
        .order_by(ProjectOrdinanceSelection.id)
        .all()
    )
    return [r.ordinance_file_id for r in rows]


@router.put("/by-id/{project_id}/ordinance-selections", response_model=dict)
def set_project_ordinance_selections(
    project_id: int,
    body: ProjectOrdinanceSelectionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _project(db, project_id, user)
    target_ids = sorted(set(body.ordinance_file_ids))
    if not target_ids:
        raise HTTPException(status_code=400, detail="At least one ordinance file must be selected")
    existing_files = db.query(OrdinanceFile.id).filter(OrdinanceFile.id.in_(target_ids)).all()
    existing_ids = {rid for (rid,) in existing_files}
    missing = [fid for fid in target_ids if fid not in existing_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Ordinance files not found: {missing}")
    db.query(ProjectOrdinanceSelection).filter(ProjectOrdinanceSelection.project_id == project_id).delete()
    for fid in target_ids:
        db.add(ProjectOrdinanceSelection(project_id=project_id, ordinance_file_id=fid))
    db.commit()
    return {"project_id": project_id, "ordinance_file_ids": target_ids}


@router.delete("/by-id/{project_id}")
def delete_project(
    project_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    p = _project(db, project_id, user)
    db.delete(p)
    db.commit()
    return {"ok": True}

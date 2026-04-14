from datetime import datetime
from enum import Enum

from pydantic import BaseModel, EmailStr, Field


class UserRoleEnum(str, Enum):
    admin = "admin"
    user = "user"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserOut(BaseModel):
    id: int
    email: str
    role: UserRoleEnum
    is_active: bool
    created_at: datetime
    display_name: str | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class UserAdminUpdate(BaseModel):
    role: UserRoleEnum | None = None
    is_active: bool | None = None


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    avatar_url: str | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=6)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    workspace_folder_id: int


class ProjectFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class ProjectOut(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    folder_count: int = 0
    drawing_count: int = 0
    file_count: int = 0
    workspace_folder_id: int | None = None
    workspace_folder_name: str | None = None

    model_config = {"from_attributes": True}


class ProjectFolderOut(BaseModel):
    id: int
    project_id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class WorkspaceFolderOut(BaseModel):
    id: int
    owner_id: int
    name: str
    created_at: datetime
    project_count: int = 0

    model_config = {"from_attributes": True}


class DrawingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class UploadedFileCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=512)


class ProjectUploadOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class OrdinanceSelectionRefOut(BaseModel):
    id: int
    title: str


class ProjectAnalysisFilesOut(BaseModel):
    drawings: list[ProjectUploadOut]
    project_files: list[ProjectUploadOut]
    ordinances: list[OrdinanceSelectionRefOut]


class ProjectOrdinanceSelectionCreate(BaseModel):
    ordinance_file_ids: list[int] = Field(default_factory=list)


class OrdinanceFolderOut(BaseModel):
    id: int
    code: str
    name: str
    file_count: int = 0

    model_config = {"from_attributes": True}


class OrdinanceFileOut(BaseModel):
    id: int
    folder_id: int
    title: str
    content_type: str | None = None
    size_bytes: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    project_count: int
    drawing_count: int
    uploaded_file_count: int
    ordinance_file_count: int


class AIChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class AIChatResponse(BaseModel):
    reply: str

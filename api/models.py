"""Pydantic 스키마 — API 요청/응답 모델."""

from pydantic import BaseModel
from typing import Optional


# ── Auth ──
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    branch_id: Optional[int] = None


class UserInfo(BaseModel):
    username: str
    role: str
    branch_id: Optional[int] = None


# ── Users ──
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    branch_id: Optional[int] = None
    memo: str = ""


class UserUpdate(BaseModel):
    role: Optional[str] = None
    password: Optional[str] = None
    memo: Optional[str] = None
    branch_id: Optional[int] = None


# ── Cafe ──
class BranchPeriodCreate(BaseModel):
    year: int
    month: int
    branch_id: int


class ArticleUpdate(BaseModel):
    keyword: Optional[str] = None
    category: Optional[str] = None
    equipment_name: Optional[str] = None
    photo_ref: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None


class StatusChange(BaseModel):
    new_status: str
    changed_by: str = ""
    note: str = ""


class PublishInfo(BaseModel):
    url: str
    published_by: str = ""


class CommentUpsert(BaseModel):
    comment_text: str = ""
    reply_text: str = ""


class FeedbackCreate(BaseModel):
    author: str
    content: str


class CafeSyncRequest(BaseModel):
    year: int
    month: int
    branch_filter: str = ""
    sheet_url: str = ""


# ── Equipment ──
class EquipmentUpdate(BaseModel):
    quantity: Optional[int] = None
    note: Optional[str] = None
    photo_status: Optional[bool] = None


class PhotoChangeItem(BaseModel):
    equipment_id: int
    photo_status: bool


class DeviceInfoUpsert(BaseModel):
    name: str
    category: str = ""
    summary: str = ""
    target: str = ""
    mechanism: str = ""
    note: str = ""
    aliases: str = ""
    is_verified: int = 0


# ── Events ──
class TreatmentUpdate(BaseModel):
    description: Optional[str] = None
    is_verified: Optional[bool] = None


class TreatmentCreate(BaseModel):
    name: str
    brand: str = ""
    category_id: int
    description: str = ""


class EventSyncRequest(BaseModel):
    year: int
    start_month: int
    end_month: int
    source_url: str = ""

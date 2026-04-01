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


class BranchPeriodMetaUpdate(BaseModel):
    smart_manager: Optional[str] = None
    writer: Optional[str] = None
    publisher: Optional[str] = None
    publish_count: Optional[int] = None
    review_count: Optional[int] = None
    superset_count: Optional[int] = None
    self_made: Optional[str] = None
    report_link: Optional[str] = None
    comment_link: Optional[str] = None
    photo_link: Optional[str] = None
    general_photo_link: Optional[str] = None
    progress_note: Optional[str] = None


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


# ── Papers (논문) ──
class PaperCreate(BaseModel):
    device_info_id: Optional[int] = None
    treatment_id: Optional[int] = None
    doi: str = ""
    title: str
    title_ko: str = ""
    authors: str = ""
    journal: str = ""
    pub_year: Optional[int] = None
    pub_date: str = ""
    abstract_summary: str = ""
    key_findings: str = ""
    keywords: str = "[]"
    evidence_level: int = 0
    study_type: str = ""
    sample_size: str = ""
    source_url: str = ""
    source_file: str = ""
    status: str = "draft"
    one_line_summary: str = ""
    research_purpose: str = ""
    study_design_detail: str = ""
    key_results: str = ""
    conclusion: str = ""
    quotable_stats: str = "[]"
    cautions: str = ""
    follow_up_period: str = ""
    photo_restriction: str = ""


class PaperUpdate(BaseModel):
    device_info_id: Optional[int] = None
    treatment_id: Optional[int] = None
    doi: Optional[str] = None
    title: Optional[str] = None
    title_ko: Optional[str] = None
    authors: Optional[str] = None
    journal: Optional[str] = None
    pub_year: Optional[int] = None
    pub_date: Optional[str] = None
    abstract_summary: Optional[str] = None
    key_findings: Optional[str] = None
    keywords: Optional[str] = None
    evidence_level: Optional[int] = None
    study_type: Optional[str] = None
    sample_size: Optional[str] = None
    source_url: Optional[str] = None
    source_file: Optional[str] = None
    status: Optional[str] = None
    one_line_summary: Optional[str] = None
    research_purpose: Optional[str] = None
    study_design_detail: Optional[str] = None
    key_results: Optional[str] = None
    conclusion: Optional[str] = None
    quotable_stats: Optional[str] = None
    cautions: Optional[str] = None
    follow_up_period: Optional[str] = None
    photo_restriction: Optional[str] = None

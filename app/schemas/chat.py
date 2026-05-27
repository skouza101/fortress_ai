"""Chat & Conversation schemas — aligned to frontend types/index.ts."""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


# ─── Enums (mirror frontend union types) ────────────────────

class UserType(str, Enum):
    ATTORNEY = "attorney"
    INDIVIDUAL = "individual"


class ContractType(str, Enum):
    RESIDENTIAL_LEASE = "residential_lease"
    EMPLOYMENT_AGREEMENT = "employment_agreement"
    FREELANCE_AGREEMENT = "freelance_agreement"
    NDA_PERSONAL = "nda_personal"
    PARTNERSHIP_AGREEMENT = "partnership_agreement"
    VENDOR_AGREEMENT = "vendor_agreement"
    NDA_BUSINESS = "nda_business"
    CONSULTING_AGREEMENT = "consulting_agreement"
    OTHER = "other"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ReportVerdict(str, Enum):
    SIGN = "SIGN"
    NEGOTIATE = "NEGOTIATE"
    REJECT = "REJECT"
    SEEK_COUNSEL = "SEEK_COUNSEL"


# ─── Attachment ─────────────────────────────────────────────

class AttachmentOut(BaseModel):
    id: str
    name: str
    size: int
    type: str


# ─── Message ────────────────────────────────────────────────

class MessageOut(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: datetime
    attachment: Optional[AttachmentOut] = None


# ─── Conversation ───────────────────────────────────────────

class ConversationOut(BaseModel):
    id: str
    title: str
    last_message: str = Field(serialization_alias="lastMessage")
    timestamp: datetime
    messages: List[MessageOut] = []
    contract_type: Optional[ContractType] = Field(None, serialization_alias="contractType")
    user_type: Optional[UserType] = Field(None, serialization_alias="userType")
    verdict: Optional[ReportVerdict] = None
    is_pinned: bool = Field(False, serialization_alias="isPinned")

    model_config = {"populate_by_name": True}


class ConversationSummaryOut(BaseModel):
    """Lightweight version without full message list — for sidebar listing."""
    id: str
    title: str
    last_message: str = Field(serialization_alias="lastMessage")
    timestamp: datetime
    contract_type: Optional[ContractType] = Field(None, serialization_alias="contractType")
    user_type: Optional[UserType] = Field(None, serialization_alias="userType")
    verdict: Optional[ReportVerdict] = None
    is_pinned: bool = Field(False, serialization_alias="isPinned")

    model_config = {"populate_by_name": True}


# ─── Requests ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    """User sends a message in a conversation."""
    message: str
    conversation_id: Optional[str] = None
    user_type: Optional[UserType] = None
    contract_type: Optional[ContractType] = None
    model: Optional[str] = None


class ConversationCreateRequest(BaseModel):
    """Create a new conversation."""
    title: Optional[str] = "New Analysis"
    contract_type: Optional[ContractType] = None
    user_type: Optional[UserType] = None


class ConversationUpdateRequest(BaseModel):
    """Rename or pin/unpin a conversation."""
    title: Optional[str] = None
    is_pinned: Optional[bool] = None


# ─── Responses ──────────────────────────────────────────────

class ChatResponse(BaseModel):
    message: MessageOut
    conversation_id: str


class FileUploadResponse(BaseModel):
    id: str
    name: str
    size: int
    type: str
    conversation_id: str

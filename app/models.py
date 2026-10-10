"""Pydantic models: profile, scheme records, API payloads."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


class SocialCategory(str, Enum):
    GENERAL = "General"
    OBC = "OBC"
    SC = "SC"
    ST = "ST"
    EWS = "EWS"
    UNKNOWN = "prefer not to say"


class Gender(str, Enum):
    FEMALE = "Female"
    MALE = "Male"
    OTHER = "Other"
    UNKNOWN = "prefer not to say"


class OccupationStage(str, Enum):
    STUDENT = "student"
    ASPIRING = "aspiring entrepreneur"
    EXISTING = "existing business"
    FARMER = "farmer"
    SALARIED = "salaried"
    ARTISAN = "artisan"
    OTHER = "other"


class Sector(str, Enum):
    MANUFACTURING = "manufacturing"
    SERVICES = "services"
    TRADING = "trading"
    AGRICULTURE = "agriculture"
    TECH = "tech"
    HANDICRAFT = "handicraft"
    OTHER = "other"


class IncomeBand(str, Enum):
    LT_1L = "under 1 lakh"
    B1_2_5L = "1 to 2.5 lakh"
    B2_5_6L = "2.5 to 6 lakh"
    B6_12L = "6 to 12 lakh"
    GT_12L = "above 12 lakh"


class FundingNeed(str, Enum):
    LT_50K = "under 50k"
    B50K_5L = "50k to 5 lakh"
    B5_10L = "5 to 10 lakh"
    B10_50L = "10 to 50 lakh"
    B50L_1CR = "50 lakh to 1 crore"
    GT_1CR = "above 1 crore"


class Operator(str, Enum):
    EQUALS = "equals"
    IN = "in"
    NOT_IN = "not_in"
    LTE = "lte"
    GTE = "gte"
    BETWEEN = "between"


CriterionStatus = Literal["met", "not_met", "unknown", "na"]
SchemeStatus = Literal["eligible", "near_miss", "possibly_eligible", "not_eligible"]


class Profile(BaseModel):
    age: Optional[int] = Field(default=None, ge=5, le=100)
    state: Optional[str] = None
    social_category: Optional[str] = None
    gender: Optional[str] = None
    occupation_stage: Optional[str] = None
    sector: Optional[str] = None
    education_level: Optional[str] = None
    income_band: Optional[str] = None
    funding_need: Optional[str] = None
    business_registered: Optional[bool] = None
    first_time_borrower: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Criterion(BaseModel):
    field: str
    operator: str
    value: Any
    required: bool = True
    actionable: bool = False
    fix_hint: Optional[str] = None
    label: Optional[str] = None


class SchemeRecord(BaseModel):
    id: str
    name: str
    body: str
    benefit_summary: str
    benefit_amount: int = Field(default=0, description="Numeric proxy (max loan/subsidy in INR) for ranking")
    ease_score: int = Field(default=3, ge=1, le=5)
    category_boost: List[str] = Field(default_factory=list)
    criteria: List[Criterion]
    documents: List[str] = Field(default_factory=list)
    channel: str = ""
    url: str = ""
    last_verified: str = ""
    source: str = ""


class CriterionResult(BaseModel):
    field: str
    status: CriterionStatus
    expected: Any = None
    actual: Any = None
    operator: str = ""
    required: bool = True
    actionable: bool = False
    fix_hint: Optional[str] = None
    gap: Optional[str] = None
    label: Optional[str] = None


class SchemeEvaluation(BaseModel):
    scheme_id: str
    scheme_name: str
    status: SchemeStatus
    criteria: List[CriterionResult] = Field(default_factory=list)
    score: float = 0.0
    rank_reason: Optional[str] = None
    failed_required: int = 0
    unknown_required: int = 0


# ---- API payloads ----
class CreateSessionResponse(BaseModel):
    session_id: str
    message: str
    question: Optional[str] = None
    progress: Optional[str] = None
    field: Optional[str] = None
    options: Optional[List[str]] = None
    option_labels: Optional[List[str]] = None
    lang: str = "en"


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    reply: str
    question: Optional[str] = None
    progress: Optional[str] = None
    field: Optional[str] = None
    options: Optional[List[str]] = None
    done: bool = False
    results: Optional[Dict[str, Any]] = None
    transitions: Optional[List[Dict[str, Any]]] = None
    option_labels: Optional[List[str]] = None


class ProfilePatchRequest(BaseModel):
    field: str
    value: Any


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    token: str
    name: str
    email: str

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, model_validator


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800


class MFALoginResponse(BaseModel):
    mfa_required: bool
    temp_token: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class MFAVerifyRequest(BaseModel):
    temp_token: str
    code: str


class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str
    manual_entry: str


class MFAConfirmRequest(BaseModel):
    code: str
    secret: str = ""  # передаётся через /mfa/confirm-with-secret


class MFADisableRequest(BaseModel):
    code: str
    password: str


class MFABackupRequest(BaseModel):
    backup_code: str
    temp_token: str = ""


class RefreshRequest(BaseModel):
    refresh_token: str


class CandidateStatusUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None


class CommentCreate(BaseModel):
    text: str
    is_private: bool = False


class CommentUpdate(BaseModel):
    text: str


class CommentOut(BaseModel):
    id: int
    candidate_id: int
    user_id: int
    text: str
    is_private: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ConsentRequest(BaseModel):
    consent_type: str
    ip_address: Optional[str] = None


class ApprovalSubmitRequest(BaseModel):
    approver_id: int


class ApprovalDecisionRequest(BaseModel):
    comment: Optional[str] = None


class ApprovalOut(BaseModel):
    id: int
    project_id: int
    result_id: int
    requested_by: int
    approver_id: Optional[int]
    status: str
    comment: Optional[str]
    created_at: datetime
    decided_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationSettings(BaseModel):
    notify_email: bool = True
    telegram_chat_id: Optional[str] = None


class WebhookSettings(BaseModel):
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None


class BrandingUpdate(BaseModel):
    brand_color: Optional[str] = None
    report_footer: Optional[str] = None


class SAMLConfig(BaseModel):
    saml_entity_id: str
    saml_sso_url: str
    saml_certificate: str


class ProjectCreate(BaseModel):
    title: str
    fot_limit: Optional[float] = None


class ProjectOut(BaseModel):
    id: int
    title: str
    fot_limit: Optional[float]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class VacancyOut(BaseModel):
    id: int
    title: str
    required_skills: list[str]
    salary_max: Optional[float]

    class Config:
        from_attributes = True


class CandidateOut(BaseModel):
    id: int
    display_name: str
    parsed_skills: dict
    salary_expectation: Optional[float]
    parse_status: str
    workflow_status: str = "new"
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectDetail(BaseModel):
    id: int
    title: str
    fot_limit: Optional[float]
    status: str
    created_at: datetime
    vacancies: list[VacancyOut]
    candidates: list[CandidateOut]

    class Config:
        from_attributes = True


class VacancyCreate(BaseModel):
    title: str
    required_skills: list[str]
    salary_max: Optional[float] = None


class OptimizationResultOut(BaseModel):
    id: int
    assignment: dict
    total_cost: Optional[float]
    match_scores: dict
    explanation: str
    created_at: datetime
    reserve: list[int] = []
    uncovered_vacancies: list[int] = []

    class Config:
        from_attributes = True


class OptimizationWeights(BaseModel):
    skill_match: float = 0.6
    salary_fit: float = 0.3
    experience: float = 0.1

    @model_validator(mode='after')
    def normalize(self) -> 'OptimizationWeights':
        total = self.skill_match + self.salary_fit + self.experience
        if total > 0:
            self.skill_match /= total
            self.salary_fit /= total
            self.experience /= total
        return self


class OptimizeRequest(BaseModel):
    weights: Optional[OptimizationWeights] = None


class SimulateRequest(BaseModel):
    excluded_candidate_ids: list[int] = []
    excluded_vacancy_ids: list[int] = []


class SimulateDiff(BaseModel):
    coverage_delta: float
    cost_delta: float


class SimulateResponse(BaseModel):
    assignment: dict
    total_cost: float
    coverage: float
    match_scores: dict
    diff: SimulateDiff


class SkillGapItem(BaseModel):
    skill: str
    coverage: float
    required: int
    covered: int
    critical: bool


class SkillGapResponse(BaseModel):
    gaps: list[SkillGapItem]
    fully_covered: list[str]
    overall_coverage: float


class ReserveItem(BaseModel):
    candidate_id: int
    display_name: str
    best_vacancy_id: int
    best_vacancy_title: str
    best_score: float
    competitor_candidate_id: Optional[int]
    rejection_reason: str
    rank: int


class ReserveResponse(BaseModel):
    reserve: list[ReserveItem]


class BudgetScenario(BaseModel):
    fot_limit: float
    coverage: float
    assigned_count: int
    total_cost: float


class BudgetAnalysisResponse(BaseModel):
    scenarios: list[BudgetScenario]
    current_fot: Optional[float]
    full_coverage_fot: Optional[float]
    delta_to_full: Optional[float]


# Интеграции — Pydantic схемы для валидации входных данных

class EmailIntegrationConfig(BaseModel):
    host: str
    port: int
    user: str
    password: str
    use_ssl: bool = True

    @model_validator(mode='after')
    def validate_fields(self) -> 'EmailIntegrationConfig':
        if not self.host or len(self.host) > 253:
            raise ValueError("host: недопустимое значение")
        if not (1 <= self.port <= 65535):
            raise ValueError("port: должен быть в диапазоне 1-65535")
        if len(self.password) > 256:
            raise ValueError("password: слишком длинный")
        return self


class AvitoIntegrationConfig(BaseModel):
    client_id: str
    client_secret: str

    @model_validator(mode='after')
    def validate_fields(self) -> 'AvitoIntegrationConfig':
        if not self.client_id or len(self.client_id) > 128:
            raise ValueError("client_id: недопустимое значение")
        if not self.client_secret or len(self.client_secret) > 256:
            raise ValueError("client_secret: недопустимое значение")
        return self

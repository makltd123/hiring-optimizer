from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from .base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    settings_json = Column(JSON, default=dict)

    # v4: SAML/OIDC
    saml_enabled = Column(Boolean, default=False)
    saml_entity_id = Column(String(500), nullable=True)
    saml_sso_url = Column(String(500), nullable=True)
    saml_certificate = Column(Text, nullable=True)
    oidc_enabled = Column(Boolean, default=False)
    oidc_client_id = Column(String(200), nullable=True)
    oidc_client_secret = Column(String(200), nullable=True)
    oidc_discovery_url = Column(String(500), nullable=True)

    # v4: вебхуки
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(100), nullable=True)

    # v4: брендинг PDF
    logo_url = Column(String(500), nullable=True)
    brand_color = Column(String(7), nullable=True)
    report_footer = Column(Text, nullable=True)

    departments = relationship("Department", back_populates="organization", cascade="all, delete-orphan")
    users = relationship("User", back_populates="organization")
    projects = relationship("Project", back_populates="organization")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="departments")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="free", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # v3: RBAC + org
    role = Column(String, default="hr_manager", nullable=False)  # admin|org_admin|dept_manager|hr_manager|viewer
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    dept_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    ldap_dn = Column(String, nullable=True)
    last_login = Column(DateTime, nullable=True)

    # v4: MFA
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(64), nullable=True)
    mfa_backup_codes = Column(JSON, default=list)
    mfa_verified_at = Column(DateTime, nullable=True)
    mfa_last_totp_counter = Column(Integer, nullable=True)

    # v4: refresh tokens (token_version для logout-all)
    token_version = Column(Integer, default=0)

    # v4: уведомления
    notify_email = Column(Boolean, default=True)
    telegram_chat_id = Column(String(50), nullable=True)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    organization = relationship("Organization", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    fot_limit = Column(Float, nullable=True)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    optimization_weights = Column(JSON, default=lambda: {"skill_match": 0.6, "salary_fit": 0.3, "experience": 0.1})

    # v3: org structure
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    dept_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    priority = Column(String, default="normal")
    deadline = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="projects")
    organization = relationship("Organization", back_populates="projects")
    vacancies = relationship("Vacancy", back_populates="project", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="project", cascade="all, delete-orphan")
    results = relationship("OptimizationResult", back_populates="project", cascade="all, delete-orphan")


class Vacancy(Base):
    __tablename__ = "vacancies"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    required_skills = Column(JSON, default=list)
    salary_max = Column(Float, nullable=True)

    project = relationship("Project", back_populates="vacancies")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    display_name = Column(String, nullable=False)
    raw_text_anonymized = Column(Text, nullable=False)
    parsed_skills = Column(JSON, default=dict)
    salary_expectation = Column(Float, nullable=True)
    parse_status = Column(String, default="parsing")
    created_at = Column(DateTime, default=datetime.utcnow)

    # v3: импорт из разных источников
    source = Column(String, default="upload")  # "upload" | "email" | "avito"

    # v4: workflow статус
    workflow_status = Column(String(20), default="new")
    status_changed_at = Column(DateTime, nullable=True)
    status_changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    merged_into = Column(Integer, ForeignKey("candidates.id"), nullable=True)

    # v4: GDPR
    erased_at = Column(DateTime, nullable=True)
    erased_by = Column(Integer, nullable=True)

    project = relationship("Project", back_populates="candidates")
    comments = relationship("CandidateComment", back_populates="candidate", cascade="all, delete-orphan")


class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assignment = Column(JSON, nullable=False)
    total_cost = Column(Float, nullable=True)
    match_scores = Column(JSON, nullable=False)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    coverage = Column(Float, nullable=True)
    weights_used = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="results")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audit_logs")


class IntegrationConfig(Base):
    """Хранит настройки интеграций (email IMAP, Авито) per user."""
    __tablename__ = "integration_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)  # "email" | "avito"
    config_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── v4 модели ────────────────────────────────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    user_agent = Column(String(512), nullable=True)
    ip_address = Column(String(64), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class CandidateComment(Base):
    __tablename__ = "candidate_comments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

    candidate = relationship("Candidate", back_populates="comments")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    consent_type = Column(String(50), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)


class ErasureRequest(Base):
    __tablename__ = "erasure_requests"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")


class BreachNotification(Base):
    __tablename__ = "breach_notifications"

    id = Column(Integer, primary_key=True, index=True)
    detected_at = Column(DateTime, nullable=False)
    notified_at = Column(DateTime, nullable=True)
    affected_records = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), default="open")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    event = Column(String(100), nullable=False)
    payload = Column(JSON, default=dict)
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(Integer, default=0)


class HiringApproval(Base):
    __tablename__ = "hiring_approvals"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    result_id = Column(Integer, ForeignKey("optimization_results.id"), nullable=False)
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="pending")  # pending|approved|rejected|revision
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime, nullable=True)

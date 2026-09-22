export interface Project {
  id: number
  title: string
  fot_limit: number | null
  status: string
  created_at: string
}

export interface Vacancy {
  id: number
  title: string
  required_skills: string[]
  salary_max: number | null
}

export type CandidateWorkflowStatus =
  | 'new' | 'in_review' | 'interview' | 'offer' | 'hired' | 'rejected' | 'archived' | 'merged'

export interface Candidate {
  id: number
  display_name: string
  parsed_skills: {
    skills?: string[]
    experience_years?: number
    salary_expectation?: number | null
    summary?: string
    _possible_duplicates?: Array<{ candidate_id: number; display_name: string; similarity: number; is_likely_duplicate: boolean }>
  }
  salary_expectation: number | null
  parse_status: 'parsing' | 'ready' | 'error'
  workflow_status: CandidateWorkflowStatus
  created_at: string
}

export interface ProjectDetail extends Project {
  vacancies: Vacancy[]
  candidates: Candidate[]
}

export interface OptimizationResult {
  id: number
  assignment: Record<string, number | null>
  total_cost: number | null
  match_scores: Record<string, Record<string, number>>
  explanation: string
  created_at: string
  reserve: number[]
  uncovered_vacancies: number[]
}

export interface OptimizationWeights {
  skill_match: number
  salary_fit: number
  experience: number
}

export interface SimulateResponse {
  assignment: Record<string, number | null>
  total_cost: number
  coverage: number
  match_scores: Record<string, Record<string, number>>
  diff: { coverage_delta: number; cost_delta: number }
}

export interface SkillGapItem {
  skill: string
  coverage: number
  required: number
  covered: number
  critical: boolean
}

export interface SkillGapResponse {
  gaps: SkillGapItem[]
  fully_covered: string[]
  overall_coverage: number
}

export interface ReserveItem {
  candidate_id: number
  display_name: string
  best_vacancy_id: number
  best_vacancy_title: string
  best_score: number
  competitor_candidate_id: number | null
  rejection_reason: string
  rank: number
}

export interface ReserveResponse {
  reserve: ReserveItem[]
}

export interface BudgetScenario {
  fot_limit: number
  coverage: number
  assigned_count: number
  total_cost: number
}

export interface BudgetAnalysisResponse {
  scenarios: BudgetScenario[]
  current_fot: number | null
  full_coverage_fot: number | null
  delta_to_full: number | null
}

// v3 Enterprise типы

export type UserRole = 'admin' | 'org_admin' | 'dept_manager' | 'hr_manager' | 'viewer'

export interface OrgUser {
  id: number
  email: string
  role: UserRole
  dept_id: number | null
  last_login: string | null
  created_at: string
}

export interface Organization {
  id: number
  name: string
  domain: string | null
  created_at: string
  settings: Record<string, unknown>
}

export interface Department {
  id: number
  name: string
  parent_id: number | null
}

export interface AuditLogEntry {
  id: number
  user_id: number | null
  action: string
  entity_type: string | null
  entity_id: number | null
  details: Record<string, unknown>
  ip_address: string | null
  created_at: string
}

export interface AuditLogResponse {
  total: number
  items: AuditLogEntry[]
}

export interface IntegrationStatus {
  email: 'configured' | 'not_configured'
  avito: 'configured' | 'not_configured'
}

export interface AsyncTaskStatus {
  state: 'queued' | 'running' | 'done' | 'error'
  progress: number
  stage?: string
  result?: { result_id: number }
  error?: string
}

// v4: типы

export interface Comment {
  id: number
  candidate_id: number
  user_id: number
  text: string
  is_private: boolean
  created_at: string
  updated_at?: string
}

export interface Session {
  id: number
  created_at: string
  expires_at: string
  ip_address: string | null
  user_agent: string | null
}

export interface Approval {
  id: number
  project_id: number
  result_id: number
  requested_by: number
  approver_id: number | null
  status: 'pending' | 'approved' | 'rejected' | 'revision'
  comment: string | null
  created_at: string
  decided_at: string | null
}

export interface DuplicateInfo {
  candidate_id: number
  display_name: string
  similarity: number
  is_likely_duplicate: boolean
}

export interface BrandingSettings {
  brand_color: string | null
  report_footer: string | null
  logo_url: string | null
}

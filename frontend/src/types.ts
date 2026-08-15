export type Dimension = string

export interface AuthUser {
  username: string
}

export interface ProjectExperience {
  name: string
  description: string
  technologies: string[]
}
export interface CandidateContext {
  name: string
  email?: string
  education?: string
  graduation_year?: number
  experience_level: string
  target_role: string
  technical_skills: string[]
  projects: ProjectExperience[]
  resume_context?: {
    professional_summary?: string | null
    work_experience: ResumeWorkExperience[]
    achievements: string[]
    certifications: string[]
    additional_context: string[]
    source_filename?: string | null
    source_text?: string | null
  }
}

export interface ResumeWorkExperience {
  title?: string | null
  company?: string | null
  start_date?: string | null
  end_date?: string | null
  description?: string | null
  achievements: string[]
  technologies: string[]
}

export interface ResumeProfile {
  name?: string | null
  email?: string | null
  education?: string | null
  graduation_year?: number | null
  experience_level?: string | null
  target_role?: string | null
  professional_summary?: string | null
  technical_skills: string[]
  projects: Array<{
    name?: string | null
    description?: string | null
    technologies: string[]
  }>
  work_experience: ResumeWorkExperience[]
  achievements: string[]
  certifications: string[]
  additional_context: string[]
}

export interface ResumeParseResponse {
  filename: string
  profile: ResumeProfile
  extracted_fields: string[]
  warnings: string[]
  parser_model: string
  context_text: string
}

export interface SavedProfileFormValues {
  name: string
  email: string
  education: string
  graduation_year: string
  experience_level: string
  target_role: string
  skills: string
}

export interface CandidateProfileDraft {
  form_values: SavedProfileFormValues
  resume_profile?: ResumeProfile | null
  resume_context_text?: string | null
  resume_name?: string | null
  candidate?: CandidateContext | null
  active_assessment_id?: string | null
  active_question_remaining_seconds?: number | null
}

export interface SavedCandidateProfile extends CandidateProfileDraft {
  updated_at: string
}

export interface Question {
  id: string
  sequence_no: number
  dimension: Dimension
  dimension_label: string
  type: 'text' | 'scenario' | 'code_review' | 'debugging' | 'agent_instruction'
  difficulty: 'foundation' | 'standard' | 'advanced'
  prompt: string
  intent: string
  expected_signals: string[]
  personalization_context?: string
  is_follow_up: boolean
  parent_question_id?: string
  adaptation_reason: string
  assessment_area: 'introduction' | 'experience' | 'project' | 'role_capability' | 'professional_judgment'
  time_limit_seconds: 120 | 180 | 300
  issued_at?: string | null
  expires_at?: string | null
}

export interface EvidenceItem {
  claim: string
  support: string
  strength: string
}

export interface DimensionScore {
  dimension: Dimension
  label: string
  score: number
  confidence: number
  evidence_count: number
  strengths: string[]
  gaps: string[]
  evidence_quality: number
  confidence_label: string
  rationale: string
  limiting_gap?: string
}

export interface Recommendation {
  pathway: string
  title: string
  rationale: string
  priority_capabilities: string[]
  next_actions: string[]
  top_development_priority: string
  why: string
  proof_of_improvement_challenge?: string | null
}

export interface AssessmentResult {
  assessment_id: string
  readiness_score: number
  classification: string
  dimensions: DimensionScore[]
  strengths: string[]
  gaps: string[]
  evidence_summary: EvidenceItem[]
  summary: string
  recommendation: Recommendation
  overall_confidence: number
  confidence_label: string
}

export interface AssessmentState {
  assessment_id: string
  status: 'in_progress' | 'completed' | 'failed'
  progress: number
  candidate?: CandidateContext
  questions_answered?: number
  max_questions?: number
  question: Question | null
  result?: AssessmentResult | null
}

export interface AssessmentHistoryItem {
  assessment_id: string
  completed_at: string
  target_role: string
  result: AssessmentResult
}

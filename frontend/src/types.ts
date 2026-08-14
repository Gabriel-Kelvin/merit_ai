export type Dimension =
  | 'engineering_fundamentals'
  | 'problem_solving'
  | 'ai_fluency'
  | 'agentic_engineering'
  | 'communication'

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
  ai_tools_used: string[]
  github_url?: string
  linkedin_url?: string
}

export interface Question {
  id: string
  sequence_no: number
  dimension: Dimension
  type: 'text' | 'scenario' | 'code_review' | 'debugging' | 'agent_instruction'
  difficulty: 'foundation' | 'standard' | 'advanced'
  prompt: string
  intent: string
  expected_signals: string[]
  personalization_context?: string
  is_follow_up: boolean
  parent_question_id?: string
  adaptation_reason: string
}

export interface EvidenceItem {
  claim: string
  support: string
  strength: string
}

export interface DimensionScore {
  dimension: Dimension
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
  question: Question | null
  result?: AssessmentResult | null
}

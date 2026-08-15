import type {
  AssessmentState,
  AuthUser,
  CandidateContext,
  CandidateProfileDraft,
  ResumeParseResponse,
  SavedCandidateProfile,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const isFormData = options?.body instanceof FormData
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...options?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || payload?.error?.message || 'Something went wrong. Please try again.')
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function login(username: string, password: string) {
  return request<AuthUser>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function getCurrentUser() {
  return request<AuthUser>('/api/v1/auth/me')
}

export async function getSavedProfile() {
  const response = await fetch(`${API_BASE_URL}/api/v1/profile`, { credentials: 'include' })
  if (response.status === 404) return null
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || 'Unable to load your saved profile.')
  }
  return response.json() as Promise<SavedCandidateProfile>
}

export function saveCandidateProfile(profile: CandidateProfileDraft) {
  return request<SavedCandidateProfile>('/api/v1/profile', {
    method: 'PUT',
    body: JSON.stringify(profile),
  })
}

export function logout() {
  return request<void>('/api/v1/auth/logout', { method: 'POST' })
}

export function startAssessment(candidate: CandidateContext) {
  return request<AssessmentState>('/api/v1/assessments', {
    method: 'POST',
    body: JSON.stringify({ candidate }),
  })
}

export function submitResponse(
  assessmentId: string,
  questionId: string,
  content: string,
  submissionReason: 'manual' | 'time_expired' = 'manual',
  timeSpentSeconds?: number,
) {
  return request<AssessmentState>(`/api/v1/assessments/${assessmentId}/responses`, {
    method: 'POST',
    body: JSON.stringify({
      question_id: questionId,
      content,
      submission_reason: submissionReason,
      time_spent_seconds: timeSpentSeconds,
    }),
  })
}

export function getAssessment(assessmentId: string) {
  return request<AssessmentState>(`/api/v1/assessments/${assessmentId}`)
}

export function parseResume(file: File) {
  const body = new FormData()
  body.append('file', file)
  return request<ResumeParseResponse>('/api/v1/resumes/parse', { method: 'POST', body })
}

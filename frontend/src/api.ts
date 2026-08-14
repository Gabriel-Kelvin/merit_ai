import type { AssessmentState, CandidateContext } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.detail || payload?.error?.message || 'Something went wrong. Please try again.')
  }
  return response.json() as Promise<T>
}

export function startAssessment(candidate: CandidateContext) {
  return request<AssessmentState>('/api/v1/assessments', {
    method: 'POST',
    body: JSON.stringify({ candidate }),
  })
}

export function submitResponse(assessmentId: string, questionId: string, content: string) {
  return request<AssessmentState>(`/api/v1/assessments/${assessmentId}/responses`, {
    method: 'POST',
    body: JSON.stringify({ question_id: questionId, content }),
  })
}

export function getAssessment(assessmentId: string) {
  return request<AssessmentState>(`/api/v1/assessments/${assessmentId}`)
}

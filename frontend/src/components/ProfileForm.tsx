import { useState, type FormEvent } from 'react'
import type { CandidateContext } from '../types'

interface ProfileFormProps {
  onSubmit: (candidate: CandidateContext) => Promise<void>
  isLoading: boolean
  error: string | null
}
interface FormValues {
  name: string
  email: string
  education: string
  graduationYear: string
  experienceLevel: string
  targetRole: string
  skills: string
  aiTools: string
  projectName: string
  projectDescription: string
  projectTechnologies: string
  githubUrl: string
  linkedinUrl: string
}

const initialValues: FormValues = {
  name: '', email: '', education: '', graduationYear: '', experienceLevel: 'fresher',
  targetRole: 'AI Engineer', skills: '', aiTools: '', projectName: '',
  projectDescription: '', projectTechnologies: '', githubUrl: '', linkedinUrl: '',
}

function list(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

export function ProfileForm({ onSubmit, isLoading, error }: ProfileFormProps) {
  const [values, setValues] = useState(initialValues)

  function update(field: keyof FormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const candidate: CandidateContext = {
      name: values.name,
      email: values.email || undefined,
      education: values.education || undefined,
      graduation_year: values.graduationYear ? Number(values.graduationYear) : undefined,
      experience_level: values.experienceLevel,
      target_role: values.targetRole,
      technical_skills: list(values.skills),
      ai_tools_used: list(values.aiTools),
      github_url: values.githubUrl || undefined,
      linkedin_url: values.linkedinUrl || undefined,
      projects: values.projectName && values.projectDescription ? [{
        name: values.projectName,
        description: values.projectDescription,
        technologies: list(values.projectTechnologies),
      }] : [],
    }
    await onSubmit(candidate)
  }

  return (
    <section className="form-page page-enter">
      <div className="section-heading"><p className="step-label">Before we begin</p><h1>Help us understand you.</h1><p>We use this context to make your assessment relevant—not to judge your background.</p></div>
      <form className="profile-form" onSubmit={handleSubmit}>
        <fieldset><legend>About you</legend><div className="form-grid">
          <label><span>Name *</span><input required value={values.name} onChange={(e) => update('name', e.target.value)} placeholder="Your full name" /></label>
          <label><span>Email</span><input type="email" value={values.email} onChange={(e) => update('email', e.target.value)} placeholder="you@example.com" /></label>
          <label><span>Education</span><input value={values.education} onChange={(e) => update('education', e.target.value)} placeholder="B.Tech Computer Science" /></label>
          <label><span>Graduation year</span><input type="number" min="1950" max="2100" value={values.graduationYear} onChange={(e) => update('graduationYear', e.target.value)} placeholder="2026" /></label>
          <label><span>Experience level *</span><select value={values.experienceLevel} onChange={(e) => update('experienceLevel', e.target.value)}><option value="student">Student</option><option value="fresher">Fresher</option><option value="0-2 years">0–2 years</option><option value="2-5 years">2–5 years</option></select></label>
          <label><span>Target role *</span><input required value={values.targetRole} onChange={(e) => update('targetRole', e.target.value)} /></label>
        </div></fieldset>
        <fieldset><legend>Your technical context</legend><div className="form-grid">
          <label className="wide"><span>Technical skills</span><input value={values.skills} onChange={(e) => update('skills', e.target.value)} placeholder="Python, FastAPI, React, PostgreSQL" /><small>Separate skills with commas</small></label>
          <label className="wide"><span>AI and coding tools</span><input value={values.aiTools} onChange={(e) => update('aiTools', e.target.value)} placeholder="Gemini, Codex, GitHub Copilot" /></label>
        </div></fieldset>
        <fieldset><legend>A project you know well</legend><div className="form-grid">
          <label><span>Project name</span><input value={values.projectName} onChange={(e) => update('projectName', e.target.value)} placeholder="Campus support assistant" /></label>
          <label><span>Technologies</span><input value={values.projectTechnologies} onChange={(e) => update('projectTechnologies', e.target.value)} placeholder="React, FastAPI, Supabase" /></label>
          <label className="wide"><span>What did you build?</span><textarea value={values.projectDescription} onChange={(e) => update('projectDescription', e.target.value)} placeholder="Describe the problem, your contribution, and how the system worked." rows={4} /></label>
        </div></fieldset>
        <details><summary>Professional links <span>Optional</span></summary><div className="form-grid optional-links">
          <label><span>GitHub</span><input type="url" value={values.githubUrl} onChange={(e) => update('githubUrl', e.target.value)} placeholder="https://github.com/..." /></label>
          <label><span>LinkedIn</span><input type="url" value={values.linkedinUrl} onChange={(e) => update('linkedinUrl', e.target.value)} placeholder="https://linkedin.com/in/..." /></label>
        </div></details>
        {error ? <p className="error-message" role="alert">{error}</p> : null}
        <div className="form-actions"><p>Your answers remain private and are used only for this assessment.</p><button className="primary-button" disabled={isLoading} type="submit">{isLoading ? 'Preparing assessment…' : 'Begin assessment →'}</button></div>
      </form>
    </section>
  )
}

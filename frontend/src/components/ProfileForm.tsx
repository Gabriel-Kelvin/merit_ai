import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { parseResume, saveCandidateProfile } from '../api'
import type {
  CandidateContext,
  CandidateProfileDraft,
  ResumeProfile,
  SavedCandidateProfile,
} from '../types'

interface ProfileFormProps {
  onSubmit: (candidate: CandidateContext, savedProfile?: SavedCandidateProfile) => Promise<void>
  isLoading: boolean
  error: string | null
  initialCandidate?: CandidateContext | null
  savedProfile?: SavedCandidateProfile | null
  onProfileSaved?: (profile: SavedCandidateProfile) => void
}

interface FormValues {
  name: string
  email: string
  education: string
  graduationYear: string
  experienceLevel: string
  targetRole: string
  skills: string
}

const initialValues: FormValues = {
  name: '',
  email: '',
  education: '',
  graduationYear: '',
  experienceLevel: '',
  targetRole: '',
  skills: '',
}

function list(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

function ResumeIcon({ complete = false }: { complete?: boolean }) {
  return (
    <span className={`resume-icon${complete ? ' complete' : ''}`} aria-hidden="true">
      {complete ? (
        <svg viewBox="0 0 24 24"><path d="m5 12 4 4L19 6" /></svg>
      ) : (
        <svg viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
          <path d="M14 2v6h6M12 18v-6m-3 3 3-3 3 3" />
        </svg>
      )}
    </span>
  )
}

function experienceValue(value?: string | null) {
  if (!value) return ''
  const normalized = value.toLowerCase().replaceAll('–', '-').trim()
  const allowed = new Set(['student', 'fresher', '0-2 years', '2-5 years', '5+ years'])
  return allowed.has(normalized) ? normalized : ''
}

function applyProfile(current: FormValues, profile: ResumeProfile): FormValues {
  return {
    name: profile.name ?? current.name,
    email: profile.email ?? current.email,
    education: profile.education ?? current.education,
    graduationYear: profile.graduation_year?.toString() ?? current.graduationYear,
    experienceLevel: experienceValue(profile.experience_level) || current.experienceLevel,
    targetRole: profile.target_role ?? current.targetRole,
    skills: profile.technical_skills.length ? profile.technical_skills.join(', ') : current.skills,
  }
}

export function ProfileForm({
  onSubmit,
  isLoading,
  error,
  initialCandidate,
  savedProfile,
  onProfileSaved,
}: ProfileFormProps) {
  const [values, setValues] = useState<FormValues>(() => savedProfile ? {
    name: savedProfile.form_values.name,
    email: savedProfile.form_values.email,
    education: savedProfile.form_values.education,
    graduationYear: savedProfile.form_values.graduation_year,
    experienceLevel: savedProfile.form_values.experience_level,
    targetRole: savedProfile.form_values.target_role,
    skills: savedProfile.form_values.skills,
  } : initialCandidate ? {
    name: initialCandidate.name,
    email: initialCandidate.email || '',
    education: initialCandidate.education || '',
    graduationYear: initialCandidate.graduation_year?.toString() || '',
    experienceLevel: initialCandidate.experience_level,
    targetRole: initialCandidate.target_role,
    skills: initialCandidate.technical_skills.join(', '),
  } : initialValues)
  const [resumeProfile, setResumeProfile] = useState<ResumeProfile | null>(savedProfile?.resume_profile ?? null)
  const [resumeContextText, setResumeContextText] = useState<string | null>(savedProfile?.resume_context_text ?? null)
  const [resumeName, setResumeName] = useState<string | null>(savedProfile?.resume_name ?? null)
  const [isParsing, setIsParsing] = useState(false)
  const [resumeMessage, setResumeMessage] = useState<string | null>(null)
  const [resumeError, setResumeError] = useState<string | null>(null)

  const buildCandidate = useCallback((): CandidateContext | null => {
    if (!values.name || !values.experienceLevel || !values.targetRole) return null
    const resumeProjects = (resumeProfile?.projects ?? [])
      .filter((project) => project.name && project.description)
      .map((project) => ({
        name: project.name as string,
        description: project.description as string,
        technologies: project.technologies,
      }))
    return {
      name: values.name,
      email: values.email || undefined,
      education: values.education || undefined,
      graduation_year: values.graduationYear ? Number(values.graduationYear) : undefined,
      experience_level: values.experienceLevel,
      target_role: values.targetRole,
      technical_skills: list(values.skills),
      projects: resumeProjects,
      resume_context: resumeProfile ? {
        professional_summary: resumeProfile.professional_summary,
        work_experience: resumeProfile.work_experience,
        achievements: resumeProfile.achievements,
        certifications: resumeProfile.certifications,
        additional_context: resumeProfile.additional_context,
        source_filename: resumeName,
        source_text: resumeContextText,
      } : undefined,
    }
  }, [values, resumeProfile, resumeName, resumeContextText])

  const profileDraft = useCallback((candidate: CandidateContext | null = buildCandidate()): CandidateProfileDraft => {
    return {
      form_values: {
        name: values.name,
        email: values.email,
        education: values.education,
        graduation_year: values.graduationYear,
        experience_level: values.experienceLevel,
        target_role: values.targetRole,
        skills: values.skills,
      },
      resume_profile: resumeProfile,
      resume_context_text: resumeContextText,
      resume_name: resumeName,
      candidate,
    }
  }, [values, resumeProfile, resumeContextText, resumeName, buildCandidate])

  useEffect(() => {
    if (!values.name && !resumeProfile) return
    const timer = window.setTimeout(() => {
      void saveCandidateProfile(profileDraft())
        .then((profile) => onProfileSaved?.(profile))
        .catch(() => undefined)
    }, 700)
    return () => window.clearTimeout(timer)
  }, [values.name, resumeProfile, profileDraft, onProfileSaved])

  function update(field: keyof FormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  async function extractResume(file: File) {
    setResumeName(file.name)
    setResumeProfile(null)
    setResumeContextText(null)
    setIsParsing(true)
    setResumeError(null)
    setResumeMessage(null)
    try {
      const extracted = await parseResume(file)
      setResumeProfile(extracted.profile)
      setResumeContextText(extracted.context_text)
      setValues((current) => applyProfile(current, extracted.profile))
      const warning = extracted.warnings.length ? ` ${extracted.warnings.join(' ')}` : ''
      setResumeMessage(
        `Imported ${extracted.extracted_fields.length} profile sections. Your complete resume context will personalize the assessment.${warning}`,
      )
    } catch (requestError) {
      setResumeError(
        requestError instanceof Error ? requestError.message : 'Unable to read this resume.',
      )
    } finally {
      setIsParsing(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const candidate = buildCandidate()
    if (!candidate) return
    const saved = await saveCandidateProfile(profileDraft(candidate))
    onProfileSaved?.(saved)
    await onSubmit(candidate, saved)
  }

  return (
    <section className="form-page page-enter">
      <div className="section-heading">
        <p className="step-label">Before we begin</p>
        <h1>Help us understand you.</h1>
        <p>Use your résumé to save time, then review or complete any missing details.</p>
      </div>
      <form className="profile-form" onSubmit={handleSubmit}>
        <section className={`resume-autofill${resumeProfile ? ' has-resume' : ''}`} aria-labelledby="resume-heading">
          <ResumeIcon complete={Boolean(resumeProfile)} />
          <div className="resume-copy">
            <span className="resume-kicker">Personalize your assessment</span>
            <h2 id="resume-heading">
              {isParsing ? 'Reading your résumé…' : resumeProfile ? 'Résumé ready' : 'Add your résumé'}
            </h2>
            <p>{resumeProfile
              ? `${resumeName} · Profile fields and deeper career context imported`
              : 'We’ll extract your profile, experience, projects and achievements. You can review everything before continuing.'}</p>
          </div>
          <label className="resume-upload-action">
            <span>{resumeProfile ? 'Replace résumé' : 'Upload résumé'}</span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6" /></svg>
            <input
              type="file"
              disabled={isParsing}
              accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
              onChange={(event) => {
                const file = event.target.files?.[0]
                if (file) void extractResume(file)
                event.target.value = ''
              }}
            />
          </label>
          {isParsing ? <div className="resume-progress" aria-hidden="true"><span /></div> : null}
          {resumeMessage ? <p className="resume-success" role="status">{resumeMessage}</p> : null}
          {resumeError ? <p className="error-message" role="alert">{resumeError}</p> : null}
        </section>

        <fieldset><legend>About you</legend><div className="form-grid">
          <label><span>Name *</span><input required value={values.name} onChange={(e) => update('name', e.target.value)} placeholder="Your full name" /></label>
          <label><span>Email</span><input type="email" value={values.email} onChange={(e) => update('email', e.target.value)} placeholder="you@example.com" /></label>
          <label><span>Education</span><input value={values.education} onChange={(e) => update('education', e.target.value)} placeholder="B.Tech Computer Science" /></label>
          <label><span>Graduation year</span><input type="number" min="1950" max="2100" value={values.graduationYear} onChange={(e) => update('graduationYear', e.target.value)} placeholder="2026" /></label>
          <label><span>Experience level *</span><select required value={values.experienceLevel} onChange={(e) => update('experienceLevel', e.target.value)}><option value="" disabled>Select experience level</option><option value="student">Student</option><option value="fresher">Fresher</option><option value="0-2 years">0-2 years</option><option value="2-5 years">2-5 years</option><option value="5+ years">5+ years</option></select></label>
          <label><span>Target role *</span><input required value={values.targetRole} onChange={(e) => update('targetRole', e.target.value)} placeholder="Enter the role you want to assess" /></label>
        </div></fieldset>

        <fieldset><legend>Your technical context</legend><div className="form-grid">
          <label className="wide"><span>Technical skills</span><input value={values.skills} onChange={(e) => update('skills', e.target.value)} placeholder="Python, FastAPI, React, PostgreSQL" /><small>Separate skills with commas</small></label>
        </div></fieldset>

        {error ? <p className="error-message" role="alert">{error}</p> : null}
        <div className="form-actions"><p>The raw file is not stored. Structured résumé details are used to personalize your questions.</p><button className="primary-button" disabled={isLoading || isParsing} type="submit">{isLoading ? 'Preparing assessment…' : 'Begin assessment →'}</button></div>
      </form>
    </section>
  )
}

import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'
import {
  getAssessment,
  getCurrentUser,
  getSavedProfile,
  login,
  logout,
  saveCandidateProfile,
  signup,
  startAssessment,
  submitResponse,
} from './api'
import { AppHeader } from './components/AppHeader'
import { AssessmentScreen } from './components/AssessmentScreen'
import { LandingPage } from './components/LandingPage'
import { LoginScreen } from './components/LoginScreen'
import { ProfileForm } from './components/ProfileForm'
import { ProfilePage } from './components/ProfilePage'
import { ResultsScreen } from './components/ResultsScreen'
import type {
  AssessmentHistoryItem,
  AssessmentResult,
  CandidateContext,
  CandidateProfileDraft,
  Question,
  SavedCandidateProfile,
} from './types'

type View = 'profile' | 'assessment' | 'results'
type PublicView = 'landing' | 'login' | 'signup'

const STORAGE_KEY = 'merit:assessment:v1'
const CANDIDATE_KEY = 'merit:candidate:v1'
const HISTORY_KEY = 'merit:history:v1'
const ACCOUNT_KEY = 'merit:account:v1'

function readJson<T>(key: string, fallback: T): T {
  try {
    const value = localStorage.getItem(key)
    return value ? JSON.parse(value) as T : fallback
  } catch {
    return fallback
  }
}

function writeJson(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* optional local history */ }
}

function readCachedAssessment(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function cacheAssessment(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Persistence is an enhancement; the live session still works without it.
  }
}

function draftFromCandidate(candidate: CandidateContext): CandidateProfileDraft {
  return {
    form_values: {
      name: candidate.name,
      email: candidate.email || '',
      education: candidate.education || '',
      graduation_year: candidate.graduation_year?.toString() || '',
      experience_level: candidate.experience_level,
      target_role: candidate.target_role,
      skills: candidate.technical_skills.join(', '),
    },
    candidate,
  }
}

function profileDraftWithAssessment(
  profile: SavedCandidateProfile,
  activeAssessmentId: string | null,
  remainingSeconds: number | null = null,
): CandidateProfileDraft {
  return {
    form_values: profile.form_values,
    resume_profile: profile.resume_profile,
    resume_context_text: profile.resume_context_text,
    resume_name: profile.resume_name,
    candidate: profile.candidate,
    active_assessment_id: activeAssessmentId,
    active_question_remaining_seconds: remainingSeconds,
  }
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)
  const [authLoading, setAuthLoading] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)
  const [publicView, setPublicView] = useState<PublicView>('landing')
  const [view, setView] = useState<View>('profile')
  const [assessmentId, setAssessmentId] = useState<string | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [result, setResult] = useState<AssessmentResult | null>(null)
  const [candidate, setCandidate] = useState<CandidateContext | null>(() => readJson(CANDIDATE_KEY, null))
  const [savedProfile, setSavedProfile] = useState<SavedCandidateProfile | null>(null)
  const [history, setHistory] = useState<AssessmentHistoryItem[]>(() => readJson(HISTORY_KEY, []))
  const [showProfileForm, setShowProfileForm] = useState(() => !readJson<CandidateContext | null>(CANDIDATE_KEY, null))
  const [progress, setProgress] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [resumeChecked, setResumeChecked] = useState(false)
  const [profileChecked, setProfileChecked] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [pausedRemaining, setPausedRemaining] = useState<number | null>(null)
  const savedActiveAssessmentId = savedProfile?.active_assessment_id
  const savedProfileRef = useRef(savedProfile)
  savedProfileRef.current = savedProfile

  function adoptAccount(username: string) {
    const previousAccount = localStorage.getItem(ACCOUNT_KEY)
    const shouldResetWorkspace = previousAccount
      ? previousAccount !== username
      : username !== 'demo'
    if (shouldResetWorkspace) {
      localStorage.removeItem(STORAGE_KEY)
      localStorage.removeItem(CANDIDATE_KEY)
      localStorage.removeItem(HISTORY_KEY)
      setAssessmentId(null)
      setCandidate(null)
      setHistory([])
      setSavedProfile(null)
      setQuestion(null)
      setResult(null)
      setShowProfileForm(true)
    }
    localStorage.setItem(ACCOUNT_KEY, username)
  }

  const rememberResult = useCallback((completedResult: AssessmentResult, targetRole?: string) => {
    setHistory((current) => {
      if (current.some((item) => item.assessment_id === completedResult.assessment_id)) return current
      const next = [{
        assessment_id: completedResult.assessment_id,
        completed_at: new Date().toISOString(),
        target_role: targetRole || 'Assessment',
        result: completedResult,
      }, ...current]
      writeJson(HISTORY_KEY, next)
      return next
    })
  }, [])

  const rememberProfile = useCallback((profile: SavedCandidateProfile) => {
    setSavedProfile(profile)
    if (profile.candidate) {
      setCandidate(profile.candidate)
      writeJson(CANDIDATE_KEY, profile.candidate)
    }
  }, [])

  useEffect(() => {
    getCurrentUser()
      .then((user) => {
        adoptAccount(user.username)
        setIsAuthenticated(true)
      })
      .catch(() => setIsAuthenticated(false))
      .finally(() => setAuthChecked(true))
  }, [])

  useEffect(() => {
    if (!authChecked || !isAuthenticated) return
    const localCandidate = readJson<CandidateContext | null>(CANDIDATE_KEY, null)
    getSavedProfile()
      .then(async (profile) => {
        if (!profile && localCandidate) {
          profile = await saveCandidateProfile(draftFromCandidate(localCandidate))
        }
        setSavedProfile(profile)
        setPausedRemaining(profile?.active_question_remaining_seconds ?? null)
        if (profile?.candidate) {
          setCandidate(profile.candidate)
          writeJson(CANDIDATE_KEY, profile.candidate)
          setShowProfileForm(false)
        } else {
          setShowProfileForm(true)
        }
      })
      .catch(() => setShowProfileForm(!localCandidate))
      .finally(() => setProfileChecked(true))
  }, [authChecked, isAuthenticated])

  useEffect(() => {
    if (!authChecked || !isAuthenticated || !profileChecked) return
    const profile = savedProfileRef.current
    const cachedId = savedActiveAssessmentId || readCachedAssessment()
    if (!cachedId) {
      setResumeChecked(true)
      return
    }
    getAssessment(cachedId)
      .then((state) => {
        setAssessmentId(cachedId)
        setProgress(state.progress)
        if (state.candidate) {
          setCandidate(state.candidate)
          writeJson(CANDIDATE_KEY, state.candidate)
        }
        if (state.status === 'completed' && state.result) {
          setResult(state.result)
          setView('results')
          rememberResult(state.result, state.candidate?.target_role)
          if (savedActiveAssessmentId && profile) {
            void saveCandidateProfile(profileDraftWithAssessment(profile, null))
              .then(rememberProfile)
              .catch(() => undefined)
          }
        } else if (state.question) {
          setQuestion(state.question)
          setPausedRemaining((current) => current ?? state.question?.time_limit_seconds ?? null)
          if (profile && savedActiveAssessmentId !== cachedId) {
            void saveCandidateProfile(profileDraftWithAssessment(profile, cachedId))
              .then(rememberProfile)
              .catch(() => undefined)
          }
        }
      })
      .catch(() => cacheAssessment(null))
      .finally(() => setResumeChecked(true))
  }, [authChecked, isAuthenticated, profileChecked, savedActiveAssessmentId, rememberProfile, rememberResult])

  async function handleLogin(username: string, password: string) {
    setAuthLoading(true)
    setAuthError(null)
    try {
      const user = await login(username, password)
      adoptAccount(user.username)
      setView('profile')
      setProfileChecked(false)
      setIsAuthenticated(true)
    } catch (requestError) {
      setAuthError(requestError instanceof Error ? requestError.message : 'Unable to sign in.')
    } finally {
      setAuthLoading(false)
    }
  }

  async function handleSignup(
    name: string,
    email: string,
    password: string,
    confirmPassword: string,
  ) {
    setAuthLoading(true)
    setAuthError(null)
    try {
      const user = await signup(name, email, password, confirmPassword)
      adoptAccount(user.username)
      setView('profile')
      setProfileChecked(false)
      setResumeChecked(false)
      setIsAuthenticated(true)
    } catch (requestError) {
      setAuthError(requestError instanceof Error ? requestError.message : 'Unable to create account.')
    } finally {
      setAuthLoading(false)
    }
  }

  async function handleLogout() {
    try {
      await logout()
    } finally {
      cacheAssessment(null)
      setAssessmentId(null)
      setQuestion(null)
      setResult(null)
      setResumeChecked(false)
      setProfileChecked(false)
      setSavedProfile(null)
      setIsAuthenticated(false)
      setPublicView('landing')
      setView('profile')
    }
  }

  async function handleStart(candidate: CandidateContext, freshlySaved?: SavedCandidateProfile) {
    if (!document.fullscreenElement) {
      void document.documentElement.requestFullscreen().catch(() => undefined)
    }
    setIsLoading(true)
    setError(null)
    try {
      const persisted = freshlySaved || await saveCandidateProfile({
          ...draftFromCandidate(candidate),
          resume_profile: savedProfile?.resume_profile,
          resume_context_text: savedProfile?.resume_context_text,
          resume_name: savedProfile?.resume_name,
        })
      setSavedProfile(persisted)
      setCandidate(candidate)
      writeJson(CANDIDATE_KEY, candidate)
      const state = await startAssessment(candidate)
      setAssessmentId(state.assessment_id)
      setQuestion(state.question)
      setProgress(state.progress)
      setPausedRemaining(null)
      cacheAssessment(state.assessment_id)
      const activeProfile = await saveCandidateProfile(
        profileDraftWithAssessment(persisted, state.assessment_id),
      ).catch(() => persisted)
      rememberProfile(activeProfile)
      setShowProfileForm(false)
      setView('assessment')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to start assessment.')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleAnswer(
    content: string,
    submissionReason: 'manual' | 'time_expired',
    timeSpentSeconds: number,
  ) {
    if (!assessmentId || !question) return false
    setIsLoading(true)
    setError(null)
    try {
      const state = await submitResponse(
        assessmentId,
        question.id,
        content,
        submissionReason,
        timeSpentSeconds,
      )
      setProgress(state.progress)
      if (state.status === 'completed' && state.result) {
        setResult(state.result)
        rememberResult(state.result, candidate?.target_role)
        setQuestion(null)
        setPausedRemaining(null)
        setView('results')
        if (savedProfile) {
          void saveCandidateProfile(profileDraftWithAssessment(savedProfile, null))
            .then(rememberProfile)
            .catch(() => undefined)
        }
      } else {
        setQuestion(state.question)
        setPausedRemaining(null)
        const profile = savedProfileRef.current
        if (profile && assessmentId) {
          void saveCandidateProfile(
            profileDraftWithAssessment(profile, assessmentId, null),
          ).then(rememberProfile).catch(() => undefined)
        }
      }
      return true
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to evaluate response.')
      return false
    } finally {
      setIsLoading(false)
    }
  }

  function startFresh() {
    cacheAssessment(null)
    setAssessmentId(null)
    setQuestion(null)
    setResult(null)
    setProgress(0)
    setError(null)
    setShowProfileForm(true)
    setView('profile')
  }

  function pauseAssessment(remainingSeconds: number) {
    setError(null)
    setPausedRemaining(remainingSeconds)
    const profile = savedProfileRef.current
    if (profile && assessmentId) {
      void saveCandidateProfile(
        profileDraftWithAssessment(profile, assessmentId, remainingSeconds),
      ).then(rememberProfile).catch(() => undefined)
    }
    setShowProfileForm(false)
    setView('profile')
  }

  useEffect(() => {
    if (view !== 'assessment' && document.fullscreenElement) {
      void document.exitFullscreen().catch(() => undefined)
    }
  }, [view])

  if (!authChecked) {
    return <div className="app-loading">Securing your workspace…</div>
  }

  if (!isAuthenticated) {
    if (publicView === 'login' || publicView === 'signup') {
      return (
        <LoginScreen
          onLogin={handleLogin}
          onSignup={handleSignup}
          initialMode={publicView}
          onBack={() => {
            setAuthError(null)
            setPublicView('landing')
          }}
          isLoading={authLoading}
          error={authError}
        />
      )
    }
    return (
      <div className="app-shell public-shell">
        <header className="site-header public-header">
          <button className="wordmark" type="button" aria-label="Merit AI home">
            <span className="wordmark-mark">M</span><span>Merit AI</span>
          </button>
          <div className="public-auth-actions">
            <button className="public-login-button" type="button" onClick={() => setPublicView('login')}>Log in</button>
            <button className="primary-button public-signup-button" type="button" onClick={() => setPublicView('signup')}>Create account</button>
          </div>
        </header>
        <main><LandingPage onStart={() => setPublicView('signup')} /></main>
      </div>
    )
  }

  if (!resumeChecked || !profileChecked) {
    return <div className="app-loading">Restoring your assessment…</div>
  }

  return (
    <div className={`app-shell${view === 'assessment' ? ' assessment-shell' : ''}`}>
      {view !== 'assessment' ? <AppHeader
        activeView={view}
        onAssessment={() => (assessmentId ? setView(result ? 'results' : 'assessment') : startFresh())}
        onProfile={() => { setShowProfileForm(false); setView('profile') }}
        onLogout={() => void handleLogout()}
      /> : null}
      <main>
        {view === 'profile' ? (
          showProfileForm ? (
            <ProfileForm
              initialCandidate={candidate}
              savedProfile={savedProfile}
              onProfileSaved={rememberProfile}
              onSubmit={handleStart}
              isLoading={isLoading}
              error={error}
            />
          ) : (
            <ProfilePage
              candidate={candidate}
              activeAssessment={assessmentId && question ? { progress, questionNumber: question.sequence_no } : null}
              history={history}
              onContinue={() => setView('assessment')}
              onBeginSaved={() => { if (candidate) void handleStart(candidate) }}
              onEdit={() => { setError(null); setShowProfileForm(true) }}
              onOpenReport={(item) => { setResult(item.result); setView('results') }}
            />
          )
        ) : null}
        {view === 'assessment' && question ? (
          <AssessmentScreen
            question={question}
            progress={progress}
            isLoading={isLoading}
            error={error}
            initialRemainingSeconds={pausedRemaining}
            onExit={pauseAssessment}
            onSubmit={handleAnswer}
          />
        ) : null}
        {view === 'results' && result ? (
          <ResultsScreen result={result} onReassess={startFresh} />
        ) : null}
      </main>
    </div>
  )
}

export default App

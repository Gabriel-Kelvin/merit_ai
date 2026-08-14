import { useEffect, useState } from 'react'
import './App.css'
import { getAssessment, startAssessment, submitResponse } from './api'
import { AppHeader } from './components/AppHeader'
import { AssessmentScreen } from './components/AssessmentScreen'
import { LandingPage } from './components/LandingPage'
import { ProfileForm } from './components/ProfileForm'
import { ResultsScreen } from './components/ResultsScreen'
import type { AssessmentResult, CandidateContext, Question } from './types'

type View = 'landing' | 'profile' | 'assessment' | 'results'

const STORAGE_KEY = 'merit:assessment:v1'

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

function App() {
  const [view, setView] = useState<View>('landing')
  const [assessmentId, setAssessmentId] = useState<string | null>(null)
  const [question, setQuestion] = useState<Question | null>(null)
  const [result, setResult] = useState<AssessmentResult | null>(null)
  const [progress, setProgress] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const [resumeChecked, setResumeChecked] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const cachedId = readCachedAssessment()
    if (!cachedId) {
      setResumeChecked(true)
      return
    }
    getAssessment(cachedId)
      .then((state) => {
        setAssessmentId(cachedId)
        setProgress(state.progress)
        if (state.status === 'completed' && state.result) {
          setResult(state.result)
          setView('results')
        } else if (state.question) {
          setQuestion(state.question)
          setView('assessment')
        }
      })
      .catch(() => cacheAssessment(null))
      .finally(() => setResumeChecked(true))
  }, [])

  async function handleStart(candidate: CandidateContext) {
    setIsLoading(true)
    setError(null)
    try {
      const state = await startAssessment(candidate)
      setAssessmentId(state.assessment_id)
      setQuestion(state.question)
      setProgress(state.progress)
      cacheAssessment(state.assessment_id)
      setView('assessment')
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to start assessment.')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleAnswer(content: string) {
    if (!assessmentId || !question) return
    setIsLoading(true)
    setError(null)
    try {
      const state = await submitResponse(assessmentId, question.id, content)
      setProgress(state.progress)
      if (state.status === 'completed' && state.result) {
        setResult(state.result)
        setQuestion(null)
        setView('results')
      } else {
        setQuestion(state.question)
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to evaluate response.')
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
    setView('profile')
  }

  if (!resumeChecked) {
    return <div className="app-loading">Restoring your assessment…</div>
  }

  return (
    <div className="app-shell">
      <AppHeader
        activeView={view}
        onHome={() => setView('landing')}
        onAssessment={() => (assessmentId ? setView(result ? 'results' : 'assessment') : startFresh())}
        onProfile={startFresh}
      />
      <main>
        {view === 'landing' ? <LandingPage onStart={startFresh} /> : null}
        {view === 'profile' ? (
          <ProfileForm onSubmit={handleStart} isLoading={isLoading} error={error} />
        ) : null}
        {view === 'assessment' && question ? (
          <AssessmentScreen
            question={question}
            progress={progress}
            isLoading={isLoading}
            error={error}
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

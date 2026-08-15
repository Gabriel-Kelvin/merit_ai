import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Question } from '../types'

interface AssessmentScreenProps {
  question: Question
  progress: number
  isLoading: boolean
  error: string | null
  initialRemainingSeconds: number | null
  onExit: (remainingSeconds: number) => void
  onSubmit: (
    content: string,
    submissionReason: 'manual' | 'time_expired',
    timeSpentSeconds: number,
  ) => Promise<boolean>
}

const typeLabels: Record<Question['type'], string> = {
  text: 'Evidence question', scenario: 'Scenario', code_review: 'Code review',
  debugging: 'Debugging exercise', agent_instruction: 'Agent instruction exercise',
}

const areaLabels: Record<Question['assessment_area'], string> = {
  introduction: 'Your story',
  experience: 'Past experience',
  project: 'Project evidence',
  role_capability: 'Role capability',
  professional_judgment: 'Professional judgment',
}

function startingSeconds(question: Question, savedRemaining: number | null) {
  if (savedRemaining === null) return question.time_limit_seconds
  return Math.max(0, Math.min(question.time_limit_seconds, savedRemaining))
}

function clock(seconds: number) {
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`
}

function draftKey(questionId: string) {
  return `merit:answer-draft:${questionId}`
}

function readDraft(questionId: string) {
  try { return localStorage.getItem(draftKey(questionId)) || '' } catch { return '' }
}

function writeDraft(questionId: string, value: string) {
  try {
    if (value) localStorage.setItem(draftKey(questionId), value)
    else localStorage.removeItem(draftKey(questionId))
  } catch { /* The assessment still works when storage is unavailable. */ }
}

export function AssessmentScreen({
  question,
  progress,
  isLoading,
  error,
  initialRemainingSeconds,
  onExit,
  onSubmit,
}: AssessmentScreenProps) {
  const [answer, setAnswer] = useState(() => readDraft(question.id))
  const [remaining, setRemaining] = useState(() => startingSeconds(question, initialRemainingSeconds))
  const [notice, setNotice] = useState<string | null>(null)
  const [isFullscreen, setIsFullscreen] = useState(Boolean(document.fullscreenElement))
  const [focusEvents, setFocusEvents] = useState(0)
  const answerRef = useRef(answer)
  const startedAtRef = useRef(Date.now())
  const deadlineRef = useRef(Date.now() + remaining * 1000)
  const submittingRef = useRef(false)
  const noticeTimerRef = useRef<number | null>(null)

  function showNotice(message: string) {
    setNotice(message)
    if (noticeTimerRef.current) window.clearTimeout(noticeTimerRef.current)
    noticeTimerRef.current = window.setTimeout(() => setNotice(null), 2800)
  }

  async function enterFullscreen() {
    try {
      await document.documentElement.requestFullscreen()
      setIsFullscreen(true)
    } catch {
      showNotice('Fullscreen is required to continue the assessment.')
    }
  }

  useEffect(() => {
    const draft = readDraft(question.id)
    setAnswer(draft)
    answerRef.current = draft
    startedAtRef.current = Date.now()
    submittingRef.current = false
    const seconds = startingSeconds(question, initialRemainingSeconds)
    setRemaining(seconds)
    deadlineRef.current = Date.now() + seconds * 1000
  }, [question, initialRemainingSeconds])

  useEffect(() => {
    const fullscreenChanged = () => setIsFullscreen(Boolean(document.fullscreenElement))
    const visibilityChanged = () => {
      if (document.hidden) setFocusEvents((current) => current + 1)
      else showNotice('Leaving the assessment window is not allowed. This event was recorded.')
    }
    const warnBeforeLeaving = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    document.addEventListener('fullscreenchange', fullscreenChanged)
    document.addEventListener('visibilitychange', visibilityChanged)
    window.addEventListener('beforeunload', warnBeforeLeaving)
    if (!document.fullscreenElement) void enterFullscreen()
    return () => {
      document.removeEventListener('fullscreenchange', fullscreenChanged)
      document.removeEventListener('visibilitychange', visibilityChanged)
      window.removeEventListener('beforeunload', warnBeforeLeaving)
      if (noticeTimerRef.current) window.clearTimeout(noticeTimerRef.current)
    }
  }, [])

  useEffect(() => {
    const tick = () => {
      const next = Math.max(0, Math.ceil((deadlineRef.current - Date.now()) / 1000))
      setRemaining(next)
      if (next === 0 && !isLoading && !submittingRef.current) {
        submittingRef.current = true
        const elapsed = Math.min(
          question.time_limit_seconds,
          Math.round((Date.now() - startedAtRef.current) / 1000),
        )
        void onSubmit(answerRef.current.trim(), 'time_expired', elapsed).then((accepted) => {
          if (accepted) writeDraft(question.id, '')
          else submittingRef.current = false
        })
      }
    }
    tick()
    const timer = window.setInterval(tick, 500)
    return () => window.clearInterval(timer)
  }, [isLoading, onSubmit, question])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submittingRef.current || isLoading) return
    submittingRef.current = true
    const elapsed = Math.min(
      question.time_limit_seconds,
      Math.round((Date.now() - startedAtRef.current) / 1000),
    )
    const accepted = await onSubmit(answer.trim(), 'manual', elapsed)
    if (accepted) writeDraft(question.id, '')
    else submittingRef.current = false
  }

  const urgency = remaining <= 30 ? ' urgent' : remaining <= 60 ? ' warning' : ''
  const timerProgress = Math.max(0, (remaining / question.time_limit_seconds) * 100)

  return (
    <section
      className="assessment-page page-enter"
      onCopyCapture={(event) => { event.preventDefault(); showNotice('Copying is disabled during the assessment.') }}
      onCutCapture={(event) => { event.preventDefault(); showNotice('Cutting is disabled during the assessment.') }}
      onPasteCapture={(event) => { event.preventDefault(); showNotice('Pasting is disabled during the assessment.') }}
      onContextMenu={(event) => { event.preventDefault(); showNotice('The context menu is disabled during the assessment.') }}
      onKeyDownCapture={(event) => {
        if ((event.ctrlKey || event.metaKey) && ['c', 'v', 'x'].includes(event.key.toLowerCase())) {
          event.preventDefault()
          showNotice('Copying and pasting are disabled during the assessment.')
        }
      }}
      onDragStart={(event) => event.preventDefault()}
      onDrop={(event) => { event.preventDefault(); showNotice('Dragging content into the assessment is disabled.') }}
    >
      {notice ? <div className="integrity-toast" role="status">{notice}</div> : null}
      {!isFullscreen ? (
        <div className="fullscreen-gate" role="dialog" aria-modal="true" aria-labelledby="fullscreen-title">
          <div>
            <span>Assessment paused</span>
            <h2 id="fullscreen-title">Return to fullscreen.</h2>
            <p>Continue in fullscreen, or safely exit and resume later from your profile.</p>
            <div className="fullscreen-actions">
              <button className="primary-button" type="button" onClick={() => void enterFullscreen()}>Enter fullscreen</button>
              <button className="secondary-button" type="button" onClick={() => onExit(remaining)}>Save &amp; exit</button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="assessment-toolbar">
        <div className="assessment-brand"><span>M</span><div><strong>Merit assessment</strong><small>Progress saves automatically</small></div></div>
        <button className="assessment-exit" type="button" onClick={() => onExit(remaining)} disabled={isLoading}>Save &amp; exit</button>
      </div>

      <div className="assessment-meta">
        <div><span>{areaLabels[question.assessment_area]}</span><strong>{question.dimension_label}</strong></div>
        <div className={`question-timer${urgency}`} role="timer" aria-live={remaining <= 30 ? 'polite' : 'off'}>
          <span>Question {question.sequence_no} of up to 20{focusEvents ? ` · ${focusEvents} focus event${focusEvents === 1 ? '' : 's'}` : ''}</span>
          <strong>{clock(remaining)}</strong>
        </div>
      </div>

      <div className="assessment-progress-row">
        <span>{Math.round(progress)}% complete</span>
        <div className="progress-track" aria-label={`${progress}% complete`}><span style={{ width: `${Math.max(progress, 5)}%` }} /></div>
      </div>

      <form className="question-panel" onSubmit={handleSubmit}>
        <div className="question-time-track" aria-hidden="true"><span style={{ width: `${timerProgress}%` }} /></div>
        <div className="question-type">{typeLabels[question.type]} · {question.difficulty} · {question.time_limit_seconds / 60} min</div>
        <h1 className="protected-question">{question.prompt}</h1>
        <label className="answer-field"><span>Your response</span><textarea
          autoFocus
          value={answer}
          onChange={(event) => {
            setAnswer(event.target.value)
            answerRef.current = event.target.value
            writeDraft(question.id, event.target.value)
          }}
          rows={7}
          placeholder="Answer in your own words. You can also say you do not know or ask to change the topic."
          disabled={isLoading}
        /></label>
        <div className="answer-footer">
          <p>{answer.trim() ? `${answer.trim().split(/\s+/).length} words · Draft saved` : 'An empty response will be recorded if time expires.'}</p>
          <button className="primary-button" type="submit" disabled={isLoading}>{isLoading ? 'Updating assessment...' : 'Submit & continue →'}</button>
        </div>
        {isLoading ? <div className="processing-state"><span /><div><strong>Updating your assessment</strong><p>Evaluating this answer and selecting the next short question.</p></div></div> : null}
        {error ? <p className="error-message" role="alert">{error}</p> : null}
      </form>
    </section>
  )
}

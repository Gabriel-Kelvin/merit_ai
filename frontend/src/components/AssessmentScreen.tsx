import { useEffect, useState, type FormEvent } from 'react'
import type { Dimension, Question } from '../types'

interface AssessmentScreenProps {
  question: Question
  progress: number
  isLoading: boolean
  error: string | null
  onSubmit: (content: string) => Promise<void>
}
const labels: Record<Dimension, string> = {
  engineering_fundamentals: 'Engineering fundamentals', problem_solving: 'Problem solving',
  ai_fluency: 'AI fluency', agentic_engineering: 'Agentic engineering', communication: 'Communication',
}

const typeLabels: Record<Question['type'], string> = {
  text: 'Experience question', scenario: 'Scenario', code_review: 'Code review',
  debugging: 'Debugging exercise', agent_instruction: 'Agent instruction exercise',
}

export function AssessmentScreen({ question, progress, isLoading, error, onSubmit }: AssessmentScreenProps) {
  const [answer, setAnswer] = useState('')

  useEffect(() => setAnswer(''), [question.id])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (answer.trim().length < 3) return
    await onSubmit(answer.trim())
  }

  return (
    <section className="assessment-page page-enter">
      <div className="assessment-meta"><div><span>Assessment</span><strong>{labels[question.dimension]}</strong></div><span>Question {question.sequence_no}</span></div>
      <div className="progress-track" aria-label={`${progress}% complete`}><span style={{ width: `${Math.max(progress, 7)}%` }} /></div>
      <form className="question-panel" onSubmit={handleSubmit}>
        <div className="question-type">{typeLabels[question.type]} · {question.difficulty}</div>
        <h1>{question.prompt}</h1>
        <label className="answer-field"><span>Your response</span><textarea autoFocus value={answer} onChange={(e) => setAnswer(e.target.value)} rows={8} placeholder="Think aloud. Specific examples, trade-offs, and verification matter more than perfect wording." disabled={isLoading} /></label>
        <div className="answer-footer"><p>{answer.trim() ? `${answer.trim().split(/\s+/).length} words` : 'Take a moment to structure your answer.'}</p><button className="primary-button" type="submit" disabled={isLoading || answer.trim().length < 3}>{isLoading ? 'Evaluating response…' : 'Continue →'}</button></div>
        {isLoading ? <div className="processing-state"><span /><div><strong>Evaluating your evidence</strong><p>Reviewing the depth, specificity, and verification in your answer.</p></div></div> : null}
        {error ? <p className="error-message" role="alert">{error}</p> : null}
      </form>
    </section>
  )
}

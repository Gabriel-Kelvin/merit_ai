import type { AssessmentHistoryItem, CandidateContext } from '../types'

interface ProfilePageProps {
  candidate: CandidateContext | null
  activeAssessment: { progress: number; questionNumber?: number } | null
  history: AssessmentHistoryItem[]
  onContinue: () => void
  onBeginSaved: () => void
  onEdit: () => void
  onOpenReport: (item: AssessmentHistoryItem) => void
}

function classification(value: string) {
  return value
    .split('_')
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ')
}

export function ProfilePage({
  candidate,
  activeAssessment,
  history,
  onContinue,
  onBeginSaved,
  onEdit,
  onOpenReport,
}: ProfilePageProps) {
  const latest = history[0]

  return (
    <section className="candidate-profile page-enter">
      <header className="profile-hero">
        <div>
          <p className="step-label">Candidate profile</p>
          <h1>{candidate ? `Welcome, ${candidate.name}.` : 'Your Merit profile.'}</h1>
          <p>{candidate
            ? `${candidate.target_role} · ${candidate.experience_level}`
            : 'Add your professional context to begin a personalized assessment.'}</p>
        </div>
        <div className="profile-actions">
          {activeAssessment ? <button className="primary-button" type="button" onClick={onContinue}>Resume assessment</button> : null}
          {candidate && !activeAssessment ? <button className="primary-button" type="button" onClick={onBeginSaved}>Begin with saved details</button> : null}
          <button className="secondary-button" type="button" onClick={onEdit}>{candidate ? 'Edit details or résumé' : 'Add your details'}</button>
        </div>
      </header>

      {activeAssessment ? (
        <section className="continue-assessment" aria-labelledby="continue-title">
          <div>
            <span>Assessment in progress</span>
            <h2 id="continue-title">Continue where you left off.</h2>
            <p>Question {activeAssessment.questionNumber || 1} is ready. Your answers, adaptive state, and progress are saved.</p>
          </div>
          <div className="continue-progress">
            <div><strong>{Math.max(1, Math.round(activeAssessment.progress))}%</strong><span>complete</span></div>
            <div className="profile-progress-track" aria-label={`${activeAssessment.progress}% complete`}><span style={{ width: `${Math.max(activeAssessment.progress, 3)}%` }} /></div>
            <button className="primary-button" type="button" onClick={onContinue}>Continue assessment →</button>
          </div>
        </section>
      ) : null}

      <div className="profile-layout">
        <section className="profile-details" aria-labelledby="details-title">
          <div className="section-title simple-title">
            <span>01</span><div><h2 id="details-title">Professional context</h2><p>Information used to personalize your assessment.</p></div>
          </div>
          {candidate ? (
            <dl className="detail-list">
              <div><dt>Name</dt><dd>{candidate.name}</dd></div>
              <div><dt>Email</dt><dd>{candidate.email || 'Not provided'}</dd></div>
              <div><dt>Education</dt><dd>{candidate.education || 'Not provided'}</dd></div>
              <div><dt>Graduation</dt><dd>{candidate.graduation_year || 'Not provided'}</dd></div>
              <div><dt>Experience</dt><dd>{candidate.experience_level}</dd></div>
              <div><dt>Target role</dt><dd>{candidate.target_role}</dd></div>
              <div className="detail-wide"><dt>Technical background</dt><dd>{candidate.technical_skills.length ? candidate.technical_skills.join(', ') : 'Not provided'}</dd></div>
            </dl>
          ) : <p className="empty-copy">No candidate details have been added yet.</p>}
        </section>

        <aside className="latest-result" aria-labelledby="latest-title">
          <div className="section-title simple-title">
            <span>02</span><div><h2 id="latest-title">Latest result</h2><p>Your most recent readiness outcome.</p></div>
          </div>
          {latest ? (
            <button type="button" className="latest-result-button" onClick={() => onOpenReport(latest)}>
              <span>Latest readiness classification</span>
              <b>{classification(latest.result.classification)}</b>
              <p>{latest.result.summary}</p>
              <small>Open full report →</small>
            </button>
          ) : <p className="empty-copy">Complete an assessment to see your personalized readiness report.</p>}
        </aside>
      </div>

      <section className="history-section" aria-labelledby="history-title">
        <div className="section-title simple-title">
          <span>03</span><div><h2 id="history-title">Assessment history</h2><p>Previous results and progress over time.</p></div>
        </div>
        {history.length ? (
          <div className="history-table" role="table" aria-label="Assessment history">
            <div className="history-head" role="row"><span>Date</span><span>Role</span><span>Readiness classification</span><span /></div>
            {history.map((item) => (
              <div className="history-row" role="row" key={item.assessment_id}>
                <span>{new Intl.DateTimeFormat('en', { dateStyle: 'medium' }).format(new Date(item.completed_at))}</span>
                <span>{item.target_role}</span>
                <span>{classification(item.result.classification)}</span>
                <button type="button" onClick={() => onOpenReport(item)}>View report</button>
              </div>
            ))}
          </div>
        ) : <p className="empty-copy history-empty">No completed assessments yet.</p>}
      </section>
    </section>
  )
}

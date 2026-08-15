import type { AssessmentResult } from '../types'

interface ResultsScreenProps {
  result: AssessmentResult
  onReassess: () => void
}

function classificationLabel(value: string) {
  return value
    .split('_')
    .map((word) => word.charAt(0) + word.slice(1).toLowerCase())
    .join(' ')
}

export function ResultsScreen({ result, onReassess }: ResultsScreenProps) {
  return (
    <section className="results-page page-enter">
      <div className="results-hero">
        <div>
          <p className="step-label">Personalized assessment summary</p>
          <h1>Your readiness, made clear.</h1>
          <p>{result.summary}</p>
        </div>
        <div className="score-block" aria-label={`Overall readiness score: ${result.readiness_score} out of 100`}>
          <span>Overall readiness score</span>
          <div><strong>{result.readiness_score}</strong><small>/ 100</small></div>
          <p>One combined view of your assessment.</p>
        </div>
      </div>

      <div className="classification-panel">
        <div>
          <span>Readiness classification</span>
          <h2>{classificationLabel(result.classification)}</h2>
        </div>
        <p>{result.recommendation.rationale}</p>
      </div>

      <div className="result-section">
        <div className="section-title">
          <span>01</span>
          <div>
            <h2>Dimension-level assessment</h2>
            <p>What your responses showed in each capability area.</p>
          </div>
        </div>
        <div className="dimension-assessment-list">
          {result.dimensions.map((item) => (
            <article key={item.dimension}>
              <div>
                <span>Capability area</span>
                <h3>{item.label}</h3>
              </div>
              {item.limiting_gap ? <small>{item.limiting_gap}</small> : <small>Evidence demonstrated across your responses.</small>}
            </article>
          ))}
        </div>
      </div>

      <div className="result-columns">
        <div className="result-section compact">
          <div className="section-title"><span>02</span><div><h2>Key strengths</h2><p>Capabilities you demonstrated consistently.</p></div></div>
          <ul className="finding-list">{result.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
        <div className="result-section compact">
          <div className="section-title"><span>03</span><div><h2>Capability gaps</h2><p>Areas where stronger evidence or practice would improve readiness.</p></div></div>
          <ul className="finding-list">{result.gaps.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      </div>

      <div className="recommendation-panel">
        <div className="recommendation-kicker">04 · Recommended pathway</div>
        <div className="recommendation-grid">
          <div>
            <span className="pathway-label">{classificationLabel(result.recommendation.pathway)}</span>
            <h2>{result.recommendation.title}</h2>
            <p>{result.recommendation.rationale}</p>
            <div className="priority-tags">{result.recommendation.priority_capabilities.map((item) => <span key={item}>{item}</span>)}</div>
          </div>
          <div className="challenge">
            <span>Primary development focus</span>
            <h3>{result.recommendation.top_development_priority}</h3>
            <p>{result.recommendation.why}</p>
          </div>
        </div>
      </div>

      <div className="result-section action-plan">
        <div className="section-title"><span>05</span><div><h2>Your next steps</h2><p>A practical sequence for turning this assessment into progress.</p></div></div>
        <ol>
          {result.recommendation.next_actions.map((item, index) => (
            <li key={`${item}-${index}`}><span>{String(index + 1).padStart(2, '0')}</span><p>{item}</p></li>
          ))}
        </ol>
      </div>

      <div className="results-actions">
        <button className="secondary-button" type="button" onClick={() => window.print()}>Save report</button>
        <button className="primary-button" type="button" onClick={onReassess}>Reassess →</button>
      </div>
    </section>
  )
}

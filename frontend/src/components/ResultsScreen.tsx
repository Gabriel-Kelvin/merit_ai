import type { AssessmentResult, Dimension } from '../types'

interface ResultsScreenProps { result: AssessmentResult; onReassess: () => void }

const labels: Record<Dimension, string> = {
  engineering_fundamentals: 'Engineering Fundamentals', problem_solving: 'Problem Solving',
  ai_fluency: 'AI Fluency', agentic_engineering: 'Agentic Engineering', communication: 'Communication',
}
function classificationLabel(value: string) {
  return value.split('_').map((word) => word.charAt(0) + word.slice(1).toLowerCase()).join(' ')
}

export function ResultsScreen({ result, onReassess }: ResultsScreenProps) {
  return (
    <section className="results-page page-enter">
      <div className="results-hero"><div><p className="step-label">Your assessment</p><h1>Your readiness, made clear.</h1><p>{result.summary}</p></div><div className="score-block"><strong>{result.readiness_score}</strong><span>Readiness score</span><em>{classificationLabel(result.classification)}</em></div></div>
      <div className="result-section"><div className="section-title"><span>01</span><div><h2>Capability profile</h2><p>How your evidence performed across the assessed dimensions.</p></div></div><div className="dimension-list">{result.dimensions.map((item) => <div className="dimension-row" key={item.dimension}><div><strong>{labels[item.dimension]}</strong><small>{item.evidence_count} evidence signals · {Math.round(item.confidence * 100)}% confidence</small></div><div className="score-bar"><span style={{ width: `${item.score}%` }} /></div><b>{item.score}</b></div>)}</div></div>
      <div className="result-columns"><div className="result-section compact"><div className="section-title"><span>02</span><div><h2>Demonstrated strengths</h2><p>Capabilities supported by your responses.</p></div></div><ul className="finding-list strengths">{result.strengths.map((item) => <li key={item}>{item}</li>)}</ul></div><div className="result-section compact"><div className="section-title"><span>03</span><div><h2>Development priorities</h2><p>The gaps currently limiting your readiness.</p></div></div><ul className="finding-list gaps">{result.gaps.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
      <div className="recommendation-panel"><div className="recommendation-kicker">Recommended next step</div><div className="recommendation-grid"><div><h2>{result.recommendation.title}</h2><p>{result.recommendation.rationale}</p><div className="priority-tags">{result.recommendation.priority_capabilities.map((item) => <span key={item}>{item}</span>)}</div></div><div className="challenge"><span>Proof-of-improvement challenge</span><p>{result.recommendation.proof_of_improvement_challenge}</p></div></div></div>
      <div className="report-evidence"><div className="section-title"><span>04</span><div><h2>Why this result</h2><p>A sample of the evidence behind your score.</p></div></div><div className="evidence-grid">{result.evidence_summary.slice(0, 6).map((item, index) => <article key={`${item.claim}-${index}`}><span>{item.strength}</span><h3>{item.claim}</h3><p>{item.support}</p></article>)}</div></div>
      <div className="results-actions"><button className="secondary-button" type="button" onClick={() => window.print()}>Save report</button><button className="primary-button" type="button" onClick={onReassess}>Reassess →</button></div>
    </section>
  )
}

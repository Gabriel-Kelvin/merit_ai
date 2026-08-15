interface LandingPageProps {
  onStart: () => void
}

export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <section className="landing page-enter">
      <div className="eyebrow"><span /> Evidence-based readiness assessment</div>
      <h1>Find out how ready you are for your next role.</h1>
      <p className="hero-copy">Understand your strengths, identify capability gaps, and receive a personalized readiness assessment.</p>
      <button className="primary-button hero-button" type="button" onClick={onStart}>Start assessment <span>→</span></button>
      <p className="hero-note">Adaptive questions · Evidence-backed report · Clear next steps</p>
      <div className="promise-grid" aria-label="Assessment benefits">
        <article><span>01</span><h2>Built around your context</h2><p>Your background, experience, and projects shape what the assessment asks next.</p></article>
        <article><span>02</span><h2>Adaptive by design</h2><p>Each response updates the capability state and selects the highest-value next question.</p></article>
        <article><span>03</span><h2>Grounded in evidence</h2><p>Your result connects every conclusion to demonstrated strengths, gaps, and priorities.</p></article>
      </div>
    </section>
  )
}

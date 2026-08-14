interface LandingPageProps {
  onStart: () => void
}
export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <section className="landing page-enter">
      <div className="eyebrow"><span /> Evidence-based engineering assessment</div>
      <h1>Know where you stand.<br /><em>Prove what you can do.</em></h1>
      <p className="hero-copy">An adaptive AI assessment that understands your experience, tests real engineering judgement, and gives you a clear path forward.</p>
      <button className="primary-button hero-button" type="button" onClick={onStart}>Start your assessment <span>→</span></button>
      <p className="hero-note">About 15 minutes · Personalized questions · Evidence-backed report</p>
      <div className="promise-grid" aria-label="Assessment benefits">
        <article><span>01</span><h2>Understands your context</h2><p>Questions begin with what you have actually built and where you want to go.</p></article>
        <article><span>02</span><h2>Adapts to your evidence</h2><p>Strong answers go deeper. Unclear answers receive one precise follow-up.</p></article>
        <article><span>03</span><h2>Explains every conclusion</h2><p>Your score is connected to observable strengths, gaps, and next actions.</p></article>
      </div>
    </section>
  )
}

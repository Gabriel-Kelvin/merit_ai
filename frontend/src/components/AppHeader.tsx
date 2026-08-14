interface AppHeaderProps {
  activeView: string
  onHome: () => void
  onAssessment: () => void
  onProfile: () => void
}
export function AppHeader({ activeView, onHome, onAssessment, onProfile }: AppHeaderProps) {
  return (
    <header className="site-header">
      <button className="wordmark" type="button" onClick={onHome} aria-label="Merit AI home">
        <span className="wordmark-mark">M</span>
        <span>Merit AI</span>
      </button>
      <nav aria-label="Primary navigation">
        <button className={activeView === 'landing' ? 'active' : ''} type="button" onClick={onHome}>Home</button>
        <button className={activeView === 'assessment' || activeView === 'results' ? 'active' : ''} type="button" onClick={onAssessment}>Assessment</button>
        <button className={activeView === 'profile' ? 'active' : ''} type="button" onClick={onProfile}>Profile</button>
      </nav>
    </header>
  )
}

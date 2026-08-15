interface AppHeaderProps {
  activeView: string
  onAssessment: () => void
  onProfile: () => void
  onLogout: () => void
}
export function AppHeader({ activeView, onAssessment, onProfile, onLogout }: AppHeaderProps) {
  return (
    <header className="site-header">
      <button className="wordmark" type="button" onClick={onProfile} aria-label="Merit AI profile">
        <span className="wordmark-mark">M</span>
        <span>Merit AI</span>
      </button>
      <nav aria-label="Primary navigation">
        <button className={activeView === 'assessment' || activeView === 'results' ? 'active' : ''} type="button" onClick={onAssessment}>Assessment</button>
        <button className={activeView === 'profile' ? 'active' : ''} type="button" onClick={onProfile}>Profile</button>
        <button className="logout-button" type="button" onClick={onLogout}>Log out</button>
      </nav>
    </header>
  )
}

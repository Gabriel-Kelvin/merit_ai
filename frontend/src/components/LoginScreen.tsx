import { useState, type FormEvent } from 'react'

interface LoginScreenProps {
  onLogin: (username: string, password: string) => Promise<void>
  onBack: () => void
  isLoading: boolean
  error: string | null
}

export function LoginScreen({ onLogin, onBack, isLoading, error }: LoginScreenProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await onLogin(username.trim(), password)
  }

  return (
    <main className="login-page page-enter">
      <section className="login-story">
        <div className="wordmark login-wordmark" aria-label="Merit AI">
          <span className="wordmark-mark">M</span><span>Merit AI</span>
        </div>
        <div>
          <p className="eyebrow"><span />Evidence, not guesswork</p>
          <h1>A fairer signal of what you can do.</h1>
          <p>Adaptive questions follow your experience, examine the evidence in each response, and turn it into an explainable readiness report.</p>
        </div>
        <p className="login-footnote">Private demo workspace · 8-hour session</p>
      </section>
      <section className="login-panel" aria-labelledby="login-title">
        <button className="login-back" type="button" onClick={onBack}>← Back to overview</button>
        <form className="login-card" onSubmit={submit}>
          <span className="login-lock" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="3" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 15v2" /></svg></span>
          <p className="step-label">Demo access</p>
          <h2 id="login-title">Welcome back.</h2>
          <p className="login-intro">Sign in to enter the candidate assessment workspace.</p>
          <label><span>Username</span><input autoFocus autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Enter username" /></label>
          <label><span>Password</span><input autoComplete="current-password" required type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter password" /></label>
          {error ? <p className="error-message" role="alert">{error}</p> : null}
          <button className="primary-button login-button" disabled={isLoading} type="submit">{isLoading ? 'Signing in…' : 'Enter Merit AI →'}</button>
          <small>This is a controlled hackathon demo account. No email verification is required.</small>
        </form>
      </section>
    </main>
  )
}

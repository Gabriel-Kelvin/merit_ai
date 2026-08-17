import { useState, type FormEvent } from 'react'

interface LoginScreenProps {
  onLogin: (username: string, password: string) => Promise<void>
  onSignup: (name: string, email: string, password: string, confirmPassword: string) => Promise<void>
  onBack: () => void
  initialMode: 'login' | 'signup'
  isLoading: boolean
  error: string | null
}

export function LoginScreen({ onLogin, onSignup, onBack, initialMode, isLoading, error }: LoginScreenProps) {
  const [mode, setMode] = useState(initialMode)
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (mode === 'signup') {
      await onSignup(name.trim(), username.trim(), password, confirmPassword)
    } else {
      await onLogin(username.trim(), password)
    }
  }

  function switchMode(nextMode: 'login' | 'signup') {
    setMode(nextMode)
    setPassword('')
    setConfirmPassword('')
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
        <p className="login-footnote">Private candidate workspace · Secure 8-hour session</p>
      </section>
      <section className="login-panel" aria-labelledby="login-title">
        <button className="login-back" type="button" onClick={onBack}>← Back to overview</button>
        <form className="login-card" onSubmit={submit}>
          <span className="login-lock" aria-hidden="true"><svg viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="3" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 15v2" /></svg></span>
          <div className="auth-tabs" role="tablist" aria-label="Account access">
            <button className={mode === 'login' ? 'active' : ''} type="button" onClick={() => switchMode('login')}>Log in</button>
            <button className={mode === 'signup' ? 'active' : ''} type="button" onClick={() => switchMode('signup')}>Create account</button>
          </div>
          <p className="step-label">{mode === 'signup' ? 'New candidate' : 'Candidate access'}</p>
          <h2 id="login-title">{mode === 'signup' ? 'Begin with your own account.' : 'Welcome back.'}</h2>
          <p className="login-intro">{mode === 'signup' ? 'Create an account to save your profile, assessment progress, and results.' : 'Sign in to continue your candidate assessment workspace.'}</p>
          {mode === 'signup' ? <label><span>Full name</span><input autoFocus autoComplete="name" required value={name} onChange={(event) => setName(event.target.value)} placeholder="Your full name" /></label> : null}
          <label><span>{mode === 'signup' ? 'Email address' : 'Email or demo username'}</span><input autoFocus={mode === 'login'} autoComplete="username" inputMode={mode === 'signup' ? 'email' : undefined} type={mode === 'signup' ? 'email' : 'text'} required value={username} onChange={(event) => setUsername(event.target.value)} placeholder={mode === 'signup' ? 'you@example.com' : 'Email or username'} /></label>
          <label><span>Password</span><input autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} required type="password" minLength={mode === 'signup' ? 8 : undefined} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter password" /></label>
          {mode === 'signup' ? <label><span>Confirm password</span><input autoComplete="new-password" required type="password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter password again" /></label> : null}
          {error ? <p className="error-message" role="alert">{error}</p> : null}
          <button className="primary-button login-button" disabled={isLoading} type="submit">{isLoading ? (mode === 'signup' ? 'Creating account…' : 'Signing in…') : (mode === 'signup' ? 'Create account & continue →' : 'Enter Merit AI →')}</button>
          <small>{mode === 'signup' ? 'No email verification is required. Your work is saved to this account.' : 'New here? Choose Create account above.'}</small>
        </form>
      </section>
    </main>
  )
}

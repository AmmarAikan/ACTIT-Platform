import { FormEvent, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { useI18n } from '../i18n/I18nContext';
import { AuthFrame } from '../components/PublicFrame';

function TemporaryAccess() {
  const { t } = useI18n();
  const [copied, setCopied] = useState('');
  const demoMode = import.meta.env.VITE_ACTIT_DEMO_MODE === 'true';
  const committeeAccess = import.meta.env.VITE_ACTIT_COMMITTEE_ACCESS === 'true';
  if (!demoMode && !committeeAccess) return null;
  const accounts = [
    { id: 'viewer', label: t('viewer'), username: 'demo-viewer', password: 'ViewerDemo!2026' },
    { id: 'analyst', label: t('analyst'), username: 'demo-analyst', password: 'AnalystDemo!2026' },
  ];
  async function copy(id: string, value: string) {
    await navigator.clipboard.writeText(value);
    setCopied(id);
  }
  const eyebrow = t(demoMode ? 'demoAccessEyebrow' : 'committeeAccessEyebrow');
  const title = t(demoMode ? 'demoAccessTitle' : 'committeeAccessTitle');
  const description = t(demoMode ? 'demoAccessDescription' : 'committeeAccessDescription');
  return <section className="demo-access" aria-labelledby="temporary-access-title">
    <header><div><span className="eyebrow">{eyebrow}</span><h2 id="temporary-access-title">{title}</h2></div><p>{description}</p></header>
    <div className="demo-access-grid">
      {accounts.map((account) => <article key={account.id}>
        <h3>{account.label}</h3>
        <dl>
          <div><dt>{t('username')}</dt><dd><code dir="ltr">{account.username}</code><button type="button" className="button button-quiet" aria-label={`${t('copyUsername')} — ${account.label}`} onClick={() => void copy(`${account.id}-username`, account.username)}>{t('copyUsername')}</button></dd></div>
          <div><dt>{t('password')}</dt><dd><code dir="ltr">{account.password}</code><button type="button" className="button button-quiet" aria-label={`${t('copyPassword')} — ${account.label}`} onClick={() => void copy(`${account.id}-password`, account.password)}>{t('copyPassword')}</button></dd></div>
        </dl>
        {(copied === `${account.id}-username` || copied === `${account.id}-password`) && <span className="demo-copy-status" role="status">{t('copied')}</span>}
      </article>)}
    </div>
  </section>;
}

export function Login() {
  const { login } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    if (!username.trim() || !password) { setError(t('loginRequired')); return; }
    setBusy(true);
    try { await login(username.trim(), password); const from = (location.state as { from?: unknown } | null)?.from; navigate(typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') ? from : '/dashboard', { replace: true }); }
    catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) setError(t('invalidCredentials'));
      else if (reason instanceof ApiError && reason.status === 429) setError(t('loginLimited'));
      else setError(t('loginFailed'));
    }
    finally { setBusy(false); }
  }
  return (
    <AuthFrame
      eyebrow={t('secureAccess')}
      title={t('welcome')}
      description={t('loginIntro')}
      asideEyebrow={t('loginAsideEyebrow')}
      asideTitle={t('loginAsideTitle')}
      asideDescription={t('loginAsideDescription')}
      signals={[
        { label: t('authAccessLabel'), value: t('authRoleBasedValue') },
        { label: t('authSessionLabel'), value: t('authTimeLimitedValue') },
        { label: t('authActionsLabel'), value: t('authAuditedValue') },
      ]}
    >
      <form className="auth-form" onSubmit={submit} noValidate>
        <label htmlFor="username">{t('username')}</label>
        <input id="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} />
        <label htmlFor="password">{t('password')}</label>
        <input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="button button-primary full-width" disabled={busy}>
          {busy ? t('signingIn') : t('signIn')}
        </button>
        <p className="auth-switch">
          {t('loginRegisterPrompt')} <Link to="/register">{t('loginRegister')}</Link>
        </p>
      </form>
      <TemporaryAccess />
    </AuthFrame>
  );
}

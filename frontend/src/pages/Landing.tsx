import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { PublicHeader } from '../components/PublicFrame';
import { BrandMark } from '../components/BrandMark';
import { useI18n, type TranslationKey } from '../i18n/I18nContext';

const steps: Array<[string, TranslationKey, TranslationKey]> = [
  ['01', 'landingCollect', 'landingCollectDetail'],
  ['02', 'landingExtract', 'landingExtractDetail'],
  ['03', 'landingCorrelate', 'landingCorrelateDetail'],
  ['04', 'landingShare', 'landingShareDetail'],
];
const cards: Array<[TranslationKey, TranslationKey]> = [
  ['landingEvidenceTitle', 'landingEvidenceDescription'],
  ['landingCorrelationTitle', 'landingCorrelationDescription'],
  ['landingBehaviorTitle', 'landingBehaviorDescription'],
  ['landingSharingTitle', 'landingSharingDescription'],
];
const trust: TranslationKey[] = [
  'landingTrustViewer',
  'landingTrustWrite',
  'landingTrustAudit',
];

export function Landing() {
  const { t } = useI18n();
  const { user } = useAuth();

  return (
    <main className="public-page landing-page">
      <PublicHeader />
      <section className="landing-hero">
        <div className="landing-copy">
          <div className="landing-brand-signature" aria-hidden="true">
            <BrandMark />
            <span><strong>ACTIT</strong><small>AI-ASSISTED CYBER THREAT INTELLIGENCE</small></span>
          </div>
          <span className="eyebrow">{t('landingEyebrow')}</span>
          <h1>{t('landingTitle')}</h1>
          <p>{t('landingDescription')}</p>
          <div className="landing-actions">
            <Link className="button button-primary" to={user ? '/dashboard' : '/login'}>
              {user ? t('landingResume') : t('landingEnter')}
            </Link>
            {!user && <Link className="button button-secondary" to="/register">{t('landingRegister')}</Link>}
            <a
              className="button button-quiet github-source-link"
              href="https://github.com/AmmarAikan/ACTIT-Platform"
              target="_blank"
              rel="noreferrer"
              aria-label={t('githubRepositoryLabel')}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-3.16 19.49c.5.09.68-.22.68-.48v-1.69c-2.78.6-3.37-1.18-3.37-1.18-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.53 1.03 1.53 1.03.9 1.53 2.35 1.09 2.92.83.09-.65.35-1.09.64-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02A9.6 9.6 0 0 1 12 6.99a9.6 9.6 0 0 1 2.5.34c1.91-1.29 2.75-1.02 2.75-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.86v2.76c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" /></svg>
              {t('viewSourceGithub')}
            </a>
          </div>
          <ul className="trust-list" aria-label={t('landingAccessControls')}>
            {trust.map((key) => <li key={key}><span aria-hidden="true">✓</span>{t(key)}</li>)}
          </ul>
        </div>
        <div className="landing-terminal" aria-label={t('landingLifecycle')}>
          <div className="terminal-head">
            <span>{t('landingPipeline')}</span>
            <span className="terminal-live"><i /> {t('landingEvidenceReady')}</span>
          </div>
          <ol>
            {steps.map(([index, title, detail]) => (
              <li key={index}>
                <span>{index}</span>
                <div><strong>{t(title)}</strong><p>{t(detail)}</p></div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="landing-section" aria-labelledby="lifecycle-title">
        <div className="section-heading compact">
          <div>
            <span className="eyebrow">{t('landingKnowledgeAction')}</span>
            <h2 id="lifecycle-title">{t('landingCapabilities')}</h2>
            <p>{t('landingCapabilitiesHint')}</p>
          </div>
        </div>
        <div className="capability-grid">
          {cards.map(([title, detail], index) => (
            <article key={title}>
              <span>0{index + 1}</span>
              <h3>{t(title)}</h3>
              <p>{t(detail)}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

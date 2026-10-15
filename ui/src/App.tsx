import { useEffect, useState } from 'react';
import { api } from './api';
import { Results } from './components/Results';
import { Review } from './components/Review';
import { Start } from './components/Start';
import type { Health, Review as ReviewT, RunResult, Sample } from './types';

type View = { kind: 'start' } | { kind: 'review'; review: ReviewT } | { kind: 'results' };

export default function App() {
  const [view, setView] = useState<View>({ kind: 'start' });
  const [health, setHealth] = useState<Health | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<RunResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch((e: Error) => setError(`The service is not reachable: ${e.message}`));
    api.samples().then(setSamples).catch(() => setSamples([]));
  }, []);

  useEffect(() => {
    if (view.kind !== 'results' || run) return;
    api.latestEval().then(setRun).catch((e: Error) => setRunError(e.message));
  }, [view.kind, run]);

  async function open(work: Promise<ReviewT>, key: string) {
    setBusy(key);
    setError(null);
    try {
      setView({ kind: 'review', review: await work });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="app">
      <nav className="topbar" aria-label="Sections">
        <span className="brand">EEOC charge intake</span>
        <div className="topbar-links">
          <button className={`navlink ${view.kind !== 'results' ? 'is-on' : ''}`} onClick={() => setView({ kind: 'start' })}>
            Review
          </button>
          <button className={`navlink ${view.kind === 'results' ? 'is-on' : ''}`} onClick={() => setView({ kind: 'results' })}>
            Evaluation
          </button>
          <a className="navlink" href="https://github.com/iamkevinstreet/eeoc-charge-intake">
            Code
          </a>
        </div>
        {health?.demo && <span className="badge">Demo</span>}
      </nav>

      <main>
        {view.kind === 'start' && (
          <Start
            health={health}
            samples={samples}
            busy={busy}
            error={error}
            onSample={(id) => void open(api.extractSample(id), id)}
            onUpload={(c, n) => void open(api.extractUpload(c, n), 'upload')}
          />
        )}
        {view.kind === 'review' && (
          <Review
            review={view.review}
            onChange={(update) => setView((v) => (v.kind === 'review' ? { kind: 'review', review: update(v.review) } : v))}
            onBack={() => setView({ kind: 'start' })}
          />
        )}
        {view.kind === 'results' && <Results run={run} error={runError} />}
      </main>
    </div>
  );
}

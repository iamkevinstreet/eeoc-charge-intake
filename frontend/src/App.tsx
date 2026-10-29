// ########################################################################
// #                         frontend/src/App.tsx                         #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The app shell: the top bar, and the start,       #
// #                     review and evaluation screens.                   #
// ########################################################################
/** The app shell: the top bar, and the start, review and evaluation screens. */

import { useEffect, useState } from 'react';

import { api, describeError } from './api';
import { Results } from './components/Results';
import { Review } from './components/Review';
import { Start } from './components/Start';
import { UPLOAD } from './components/UploadForm';
import { CODE_URL } from './config';
import type { Health, Review as ReviewData, RunResult, Sample } from './types';

type Screen = 'start' | 'review' | 'results';

// log.debug('Names the screen that lists the documents')
const START: Screen = 'start';
// log.debug('Names the screen that reviews one record')
const REVIEW: Screen = 'review';
// log.debug('Names the screen that shows the evaluation')
const RESULTS: Screen = 'results';
// log.debug('Sets the class of each link in the top bar')
const LINK = 'ec-bar__link';
// log.debug('Lists the sections the top bar offers, with the screen each opens')
const SECTIONS: readonly { screen: Screen; label: string }[] = [
  { screen: START, label: 'Review' },
  { screen: RESULTS, label: 'Evaluation' },
];

// log.debug('Defines the app')
export function App() {
  // log.debug('Keeps the screen on show')
  const [screen, setScreen] = useState<Screen>(START);
  // log.debug('Keeps the health report')
  const [health, setHealth] = useState<Health | null>(null);
  // log.debug('Keeps the generated samples')
  const [samples, setSamples] = useState<Sample[]>([]);
  // log.debug('Keeps what is being extracted: a sample id, the upload, or nothing')
  const [busy, setBusy] = useState<string | null>(null);
  // log.debug('Keeps a problem to show on the start screen')
  const [problem, setProblem] = useState<string | null>(null);
  // log.debug('Keeps the review being worked on')
  const [review, setReview] = useState<ReviewData | null>(null);
  // log.debug('Keeps the latest evaluation run')
  const [run, setRun] = useState<RunResult | null>(null);
  // log.debug('Keeps a problem loading the evaluation run')
  const [runProblem, setRunProblem] = useState<string | null>(null);

  // log.debug('Loads the health report and the samples once')
  useEffect(() => {
    // log.debug('Fetches the health report, or says why it could not')
    api
      .health()
      .then(setHealth)
      .catch((error: unknown) => setProblem(describeError(error)));
    // log.debug('Fetches the samples, or shows none')
    api
      .samples()
      .then(setSamples)
      .catch(() => setSamples([]));
  }, []);

  // log.debug('Defines how a review is opened from an extraction')
  const open = (extract: () => Promise<ReviewData>, key: string): void => {
    // log.debug('Marks the extraction as started')
    setBusy(key);
    // log.debug('Clears any problem')
    setProblem(null);
    // log.debug('Runs the extraction, then shows the review or the problem')
    extract()
      .then((opened) => {
        // log.debug('Keeps the review')
        setReview(opened);
        // log.debug('Shows the review screen')
        setScreen(REVIEW);
      })
      .catch((error: unknown) => setProblem(describeError(error)))
      .finally(() => setBusy(null));
  };

  // log.debug('Defines how a decision updates the review being worked on')
  const change = (update: (current: ReviewData) => ReviewData): void => {
    // log.debug('Applies the update to the latest review, if there is one')
    setReview((current) => (current === null ? null : update(current)));
  };

  // log.debug('Defines how a section of the top bar is opened')
  const show = (next: Screen): void => {
    // log.debug('Shows the screen')
    setScreen(next);
    // log.debug('Loads the evaluation run when it is shown and not loaded yet')
    if (next === RESULTS && run === null) {
      // log.debug('Clears the last problem loading it')
      setRunProblem(null);
      // log.debug('Fetches the latest run, or says why there is none')
      api
        .latestEval()
        .then(setRun)
        .catch((error: unknown) => setRunProblem(describeError(error)));
    }
  };

  // log.debug('Notes the section the top bar marks: evaluation, or review for the rest')
  const section = screen === RESULTS ? RESULTS : START;

  // log.debug('Returns the page')
  return (
    <div className="ec-app">
      <nav className="ec-bar" aria-label="Sections">
        <span className="ec-bar__name">EEOC charge intake</span>
        <div className="ec-bar__links">
          {SECTIONS.map((item) => (
            <button
              key={item.screen}
              type="button"
              className={LINK}
              aria-current={section === item.screen ? 'page' : undefined}
              onClick={() => show(item.screen)}
            >
              {item.label}
            </button>
          ))}
          <a className={LINK} href={CODE_URL}>
            Code
          </a>
        </div>
        {health?.demo === true && <span className="ec-badge">Demo</span>}
      </nav>
      <main className="ec-main">
        {screen === START && (
          <Start
            health={health}
            samples={samples}
            busy={busy}
            error={problem}
            onSample={(id) => open(() => api.extractSample(id), id)}
            onUpload={(charge, notice) => open(() => api.extractUpload(charge, notice), UPLOAD)}
          />
        )}
        {screen === REVIEW && review !== null && (
          <Review review={review} onChange={change} onBack={() => setScreen(START)} />
        )}
        {screen === RESULTS && <Results run={run} error={runProblem} />}
      </main>
    </div>
  );
}

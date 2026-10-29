// ########################################################################
// #                         frontend/src/App.tsx                         #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The app shell: the top bar, and the start, review and evaluation
 * screens, one at a time. It keeps the screen on show; the state the
 * screens share comes from the session's hooks.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { useState } from 'react';

// Local
import { Results } from './components/Results';
import { Review } from './components/Review';
import { Start } from './components/Start';
import { TopBar } from './components/TopBar';
import { required } from './lib/required';
import { useEvaluation, useReviewing, useStart } from './session';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
/** The three screens the app shows. */
type Screen = 'start' | 'review' | 'results';

// log.debug('Names the screen that lists the documents')
const START: Screen = 'start';
// log.debug('Names the screen that reviews one record')
const REVIEW: Screen = 'review';
// log.debug('Names the screen that shows the evaluation')
const RESULTS: Screen = 'results';
// log.debug('Lists the sections the top bar offers, with the screen each opens')
const SECTIONS: readonly { screen: Screen; label: string }[] = [
  { screen: START, label: 'Review' },
  { screen: RESULTS, label: 'Evaluation' },
];

// ########################################################################
// #                              App shell                               #
// ########################################################################
/** The screen on show, and how another is shown. */
interface Navigation {
  screen: Screen;
  show: (next: Screen) => void;
}

// log.debug('Defines the hook that keeps the screen on show')
/**
 * Keeps the screen on show, and loads the evaluation run when its screen
 * is shown.
 *
 * @param onResults - Loads the evaluation run, unless it has loaded.
 *   Required.
 * @returns The screen on show, and what shows another.
 */
function useScreen(onResults: (() => void) | null = null): Navigation {
  // log.debug('Takes what loads the evaluation run, which the caller must give')
  onResults = required({ onResults });
  // log.debug('Keeps the screen on show')
  const [screen, setScreen] = useState<Screen>(START);

  // log.debug('Defines how a screen is shown')
  /**
   * Shows a screen, loading the evaluation run with its screen.
   *
   * @param next - The screen to show. Required.
   */
  const show = (next: Screen | null = null): void => {
    // log.debug('Takes the screen, which the caller must give')
    next = required({ next });
    // log.debug('Shows the screen')
    setScreen(next);
    // log.debug('Loads the evaluation run when its screen is shown')
    if (next === RESULTS) {
      // log.debug('Loads it, unless it has loaded already')
      onResults();
    }
  };

  // log.debug('Returns the screen on show and what shows another')
  return { screen, show };
}

// log.debug('Defines the app')
/**
 * Renders the app: the top bar and the screen on show.
 *
 * @returns The top bar, then the start, review or evaluation screen.
 */
export function App(): React.JSX.Element {
  // log.debug('Holds the latest evaluation run')
  const evaluation = useEvaluation();
  // log.debug('Holds the screen on show, loading the evaluation run with its screen')
  const nav = useScreen(evaluation.load);
  // log.debug('Holds the review being worked on')
  const reviewing = useReviewing();
  // log.debug('Holds what the start screen shows, opening the review each extraction makes')
  const start = useStart((opened) => {
    // log.debug('Keeps the review')
    reviewing.open(opened);
    // log.debug('Shows the review screen')
    nav.show(REVIEW);
  });
  // log.debug('Notes the section the top bar marks: evaluation, or review for the rest')
  const section = nav.screen === RESULTS ? RESULTS : START;

  // log.debug('Returns the page')
  return (
    <div className="ec-app">
      <TopBar
        sections={SECTIONS}
        current={section}
        demo={start.health?.demo === true}
        onShow={nav.show}
      />
      <main className="ec-main">
        {nav.screen === START && (
          <Start
            health={start.health}
            samples={start.samples}
            busy={start.busy}
            error={start.problem}
            onSample={start.onSample}
            onUpload={start.onUpload}
          />
        )}
        {nav.screen === REVIEW && reviewing.review !== null && (
          <Review
            review={reviewing.review}
            onChange={reviewing.change}
            onBack={() => nav.show(START)}
          />
        )}
        {nav.screen === RESULTS && <Results run={evaluation.run} error={evaluation.problem} />}
      </main>
    </div>
  );
}

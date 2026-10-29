// ########################################################################
// #                       frontend/src/session.ts                        #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The app's state, as React hooks: what the service reports when the
 * app opens, the extraction under way, the review being worked on, and
 * the latest evaluation run, loaded the first time it is asked for.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { useEffect, useState } from 'react';

// Local
import { api, describeError } from './api';
import { CONFIG } from './config';
import { required } from './lib/required';
import type { Health, Review, RunResult, Sample } from './types';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes what an upload is called while it is extracted from the config')
const UPLOAD = CONFIG.ui.upload_key;

// ########################################################################
// #                            Session state                             #
// ########################################################################
/** What the service reports when the app opens: its health and the samples. */
interface Service {
  health: Health | null;
  samples: Sample[];
}

/** What the start screen shows, and the extractions it starts. */
export interface StartScreen extends Service {
  /** What is being extracted: a sample id, the upload, or nothing. */
  busy: string | null;
  problem: string | null;
  onSample: (id: string) => void;
  onUpload: (charge: File, notice: File) => void;
}

/** The review being worked on, and how a decision changes it. */
export interface Reviewing {
  review: Review | null;
  open: (review: Review) => void;
  /** Applies a change to the latest review, so two quick decisions both count. */
  change: (update: (current: Review) => Review) => void;
}

/** The latest evaluation run, any problem loading it, and how it is loaded. */
export interface Evaluation {
  run: RunResult | null;
  problem: string | null;
  load: () => void;
}

// log.debug('Defines the hook that loads what the service reports when the app opens')
/**
 * Loads the service's health report and the samples, once.
 *
 * @param setProblem - Shows why the health report could not be read.
 *   Required.
 * @returns The health report and the samples; null and none until they
 *   arrive.
 */
function useService(setProblem: ((problem: string) => void) | null = null): Service {
  // log.debug('Takes what shows a problem, which the caller must give')
  setProblem = required({ setProblem });
  // log.debug('Keeps the health report')
  const [health, setHealth] = useState<Health | null>(null);
  // log.debug('Keeps the generated samples')
  const [samples, setSamples] = useState<Sample[]>([]);

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
  }, [setProblem]);

  // log.debug('Returns the health report and the samples')
  return { health, samples };
}

// log.debug('Defines the hook that holds what the start screen shows and starts')
/**
 * Holds what the start screen shows, and runs the extractions it starts.
 *
 * @param onOpened - Opens the review an extraction makes. Required.
 * @returns The health report, the samples, what is being extracted, any
 *   problem, and a handler for each kind of extraction.
 */
export function useStart(onOpened: ((review: Review) => void) | null = null): StartScreen {
  // log.debug('Takes what opens a review, which the caller must give')
  onOpened = required({ onOpened });
  // log.debug('Keeps what is being extracted: a sample id, the upload, or nothing')
  const [busy, setBusy] = useState<string | null>(null);
  // log.debug('Keeps a problem to show on the start screen')
  const [problem, setProblem] = useState<string | null>(null);
  // log.debug('Loads the health report and the samples')
  const { health, samples } = useService(setProblem);

  // log.debug('Defines how a review is opened from an extraction')
  /**
   * Runs an extraction, then opens its review, or shows why it failed.
   *
   * @param extract - The call that extracts the fields: of a sample or
   *   of an upload. Required.
   * @param key - What is being extracted, which the start screen marks
   *   as busy: the sample's id, or the upload's key. Required.
   */
  const open = (
    extract: (() => Promise<Review>) | null = null,
    key: string | null = null,
  ): void => {
    // log.debug('Takes the extraction, which the caller must give')
    extract = required({ extract });
    // log.debug('Takes the key, which the caller must give')
    key = required({ key });
    // log.debug('Marks the extraction as started')
    setBusy(key);
    // log.debug('Clears any problem')
    setProblem(null);
    // log.debug('Runs the extraction, then opens the review or shows the problem')
    extract()
      .then(onOpened)
      .catch((error: unknown) => setProblem(describeError(error)))
      .finally(() => setBusy(null));
  };

  // log.debug('Returns the state, with a handler for a sample and one for an upload')
  return {
    health,
    samples,
    busy,
    problem,
    onSample: (id) => open(() => api.extractSample(id), id),
    onUpload: (charge, notice) => open(() => api.extractUpload(charge, notice), UPLOAD),
  };
}

// log.debug('Defines the hook that holds the review being worked on')
/**
 * Holds the review being worked on.
 *
 * @returns The review, or null before one is opened; what opens one;
 *   and what applies a decision to it.
 */
export function useReviewing(): Reviewing {
  // log.debug('Keeps the review being worked on')
  const [review, setReview] = useState<Review | null>(null);

  // log.debug('Defines how a decision updates the review being worked on')
  /**
   * Applies a change to the latest review, if there is one.
   *
   * @param update - The change: the new review made from the current
   *   one. Required.
   */
  const change = (update: ((current: Review) => Review) | null = null): void => {
    // log.debug('Takes the update, which the caller must give')
    update = required({ update });
    // log.debug('Applies the update to the latest review, if there is one')
    setReview((current) => (current === null ? null : update(current)));
  };

  // log.debug('Returns the review, what opens one, and what changes it')
  return { review, open: setReview, change };
}

// log.debug('Defines the hook that holds the latest evaluation run')
/**
 * Holds the latest evaluation run, loaded the first time it is asked for.
 *
 * @returns The run, or null until it has loaded; why it could not be
 *   loaded; and what loads it.
 */
export function useEvaluation(): Evaluation {
  // log.debug('Keeps the latest evaluation run')
  const [run, setRun] = useState<RunResult | null>(null);
  // log.debug('Keeps a problem loading the evaluation run')
  const [problem, setProblem] = useState<string | null>(null);

  // log.debug('Defines how the run is loaded, once')
  /** Loads the latest run, unless it has loaded already. */
  const load = (): void => {
    // log.debug('Leaves a run that has loaded as it is')
    if (run !== null) {
      // log.debug('Returns without loading it again')
      return;
    }
    // log.debug('Clears the last problem loading it')
    setProblem(null);
    // log.debug('Fetches the latest run, or says why there is none')
    api
      .latestEval()
      .then(setRun)
      .catch((error: unknown) => setProblem(describeError(error)));
  };

  // log.debug('Returns the run, any problem, and what loads it')
  return { run, problem, load };
}

// ########################################################################
// #                 frontend/src/components/Results.tsx                  #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The evaluation screen: which run is shown, its headline numbers, the
 * accuracy of each field, and the averages by kind of case.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from '../config';
import { money, rate, share, tagLabel } from '../format';
import { required } from '../lib/required';
import { average, finished, kinds, metric, ofKind } from '../scores';
import type { RunResult } from '../types';
import { FieldBars } from './FieldBars';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the score for fields left empty that had an answer from the config')
const ABSTENTIONS = CONFIG.scores.false_abstentions;
// log.debug('Takes the score for fields filled that had no answer from the config')
const GUESSES = CONFIG.scores.guesses;
// log.debug('Takes the provider that means the offline stand-in from the config')
const OFFLINE_PROVIDER = CONFIG.demo.provider;
// log.debug('Takes the command for the offline evaluation from the config')
const SMOKE_COMMAND = CONFIG.ui.smoke_command;
// log.debug('Takes the class of the quieter notes from the config')
const META = CONFIG.ui.note_class;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
/** One number in the row of numbers at the top. */
interface Stat {
  label: string;
  value: (run: RunResult) => string;
  note?: (run: RunResult) => string;
}

/** One column of the table by kind of case: the score it averages and how it is written. */
interface Column {
  label: string;
  key: string;
  show: (value: number) => string;
}

// log.debug('Names the score for the share of fields right')
const ACCURACY = 'field_accuracy';
// log.debug('Names the label for the share of fields right')
const ACCURACY_LABEL = 'Field accuracy';
// log.debug('Sets the characters of a timestamp up to the minute')
const MINUTE = 16;
// log.debug('Lists the numbers at the top, each read from the run')
const STATS: readonly Stat[] = [
  { label: ACCURACY_LABEL, value: (run) => share(metric(run.summary, ACCURACY)) },
  {
    label: 'Unsupported outputs removed',
    value: (run) => share(metric(run.summary, 'unsupported_rate')),
    note: () => 'share of filled fields whose quoted text was not on the cited page',
  },
  { label: 'False abstentions per case', value: (run) => rate(metric(run.summary, ABSTENTIONS)) },
  { label: 'Guesses per case', value: (run) => rate(metric(run.summary, GUESSES)) },
  {
    label: 'Latency p50 / p95',
    value: (run) =>
      `${metric(run.summary, 'latency_p50_ms')} / ${metric(run.summary, 'latency_p95_ms')} ms`,
  },
  {
    label: 'Cost per case',
    value: (run) => money(metric(run.summary, 'cost_per_case_usd')),
    note: (run) => `prices as of ${run.prices_as_of}`,
  },
];
// log.debug('Lists the averaged columns of the table by kind of case')
const COLUMNS: readonly Column[] = [
  { label: ACCURACY_LABEL, key: ACCURACY, show: share },
  { label: 'Unsupported removed', key: 'unsupported_removed', show: rate },
  { label: 'False abstentions', key: ABSTENTIONS, show: rate },
  { label: 'Guesses', key: GUESSES, show: rate },
];

// ########################################################################
// #                          Evaluation screen                           #
// ########################################################################
interface Props {
  run?: RunResult | null;
  error?: string | null;
}

interface StatProps {
  stat?: Stat | null;
  run?: RunResult | null;
}

interface KindProps {
  run?: RunResult | null;
}

// log.debug('Defines the line that says which run this is')
/**
 * Returns the line that says which run this is.
 *
 * @param run - The run. Required.
 * @returns Its name, model and provider, how many cases and failures,
 *   and when it started, to the minute in UTC.
 */
function about(run: RunResult | null = null): string {
  // log.debug('Takes the run, which the caller must give')
  run = required({ run });
  // log.debug('Writes the start time to the minute')
  const started = run.started_at.slice(0, MINUTE).replace('T', ' ');
  // log.debug('Returns who ran, how many cases, and when')
  return [
    `${run.name}, model ${run.model} (${run.provider})`,
    `${run.cases} cases`,
    `${run.failures} failures`,
    `run ${started} UTC.`,
  ].join(', ');
}

// log.debug('Defines one number at the top')
/**
 * Renders one headline number, with its label and any note.
 *
 * @param props - The component's props.
 * @param props.stat - The number to show and how to read it. Required.
 * @param props.run - The run it is read from. Required.
 * @returns The number, its label, and its note when it has one.
 */
function StatTile({ stat = null, run = null }: StatProps = {}): React.JSX.Element {
  // log.debug('Takes the number to show, which the caller must give')
  stat = required({ stat });
  // log.debug('Takes the run, which the caller must give')
  run = required({ run });
  // log.debug('Returns the number, its label, and its note when it has one')
  return (
    <div className="ec-stat">
      <div className="ec-stat__value">{stat.value(run)}</div>
      <div className="ec-stat__label">{stat.label}</div>
      {stat.note && <div className="ec-stat__note">{stat.note(run)}</div>}
    </div>
  );
}

// log.debug('Defines the table of averages by kind of case')
/**
 * Renders the table of averages by kind of case.
 *
 * @param props - The component's props.
 * @param props.run - The run whose cases are averaged. Required.
 * @returns One row per kind of case, with its count and averages.
 */
function KindTable({ run = null }: KindProps = {}): React.JSX.Element {
  // log.debug('Takes the run, which the caller must give')
  run = required({ run });
  // log.debug('Returns one row per kind of case, with its count and averages')
  return (
    <table className="ec-ledger">
      <thead>
        <tr>
          <th scope="col">Case kind</th>
          <th scope="col">Cases</th>
          {COLUMNS.map((column) => (
            <th key={column.key} scope="col">
              {column.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {kinds(run.results).map((tag) => (
          <tr key={tag}>
            <td>{tagLabel(tag)}</td>
            <td>{finished(ofKind(run.results, tag)).length}</td>
            {COLUMNS.map((column) => (
              <td key={column.key}>
                {column.show(average(ofKind(run.results, tag), column.key))}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// log.debug('Defines the evaluation screen')
/**
 * Renders the evaluation screen: the latest run, or how to make one.
 *
 * @param props - The component's props.
 * @param props.run - The latest run; null until it has loaded.
 * @param props.error - Why there is no run to show; null when there is
 *   no problem.
 * @returns The heading, then the run's numbers, or how to get some.
 */
export function Results({ run = null, error = null }: Props = {}): React.JSX.Element {
  // log.debug('Returns the heading, then what there is: no results yet, or the run')
  return (
    <div className="ec-results">
      <h1>Evaluation</h1>
      {error !== null && (
        <p className={META}>
          No results yet. Run <code>{SMOKE_COMMAND}</code> for the offline check or the live
          evaluation workflow for a real model, then reload.
        </p>
      )}
      {error === null && run !== null && (
        <>
          <p className={META}>
            {about(run)}
            {run.provider === OFFLINE_PROVIDER && (
              <>
                {' '}
                This is the offline smoke run: answers come from ground truth, so it checks the
                pipeline, not a model.
              </>
            )}
          </p>
          <div className="ec-stats">
            {STATS.map((stat) => (
              <StatTile key={stat.label} stat={stat} run={run} />
            ))}
          </div>
          <h2>Accuracy by field</h2>
          <FieldBars results={run.results} />
          <h2>By case kind</h2>
          <KindTable run={run} />
        </>
      )}
    </div>
  );
}

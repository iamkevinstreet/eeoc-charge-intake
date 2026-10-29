// ########################################################################
// #                        frontend/src/scores.ts                        #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Reads an evaluation run for the evaluation screen: its summary
 * numbers, the cases that finished, the kinds of case, and each score
 * averaged over the cases, overall, by field and by kind.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from './config';
import { required } from './lib/required';
import type { CaseResult } from './types';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes each field, in the order the record shows them, from the config')
const FIELD_LABELS = CONFIG.labels.fields;
// log.debug('Takes the field the model paraphrases instead of quoting from the config')
const SUMMARY_FIELD = CONFIG.record.summary_field;
// log.debug('Takes what comes before a field name in the score that field earns, from the config')
const FIELD_SCORE = CONFIG.scores.field_prefix;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Lists the fields scored against the known answers; a summary is a paraphrase')
export const SCORED: readonly string[] = Object.keys(FIELD_LABELS).filter(
  (name) => name !== SUMMARY_FIELD,
);

// ########################################################################
// #                              Run scores                              #
// ########################################################################
// log.debug('Defines one number from the summary of a run')
/**
 * Returns one number from the summary of a run.
 *
 * @param summary - The run's summary numbers, by name. Required.
 * @param key - The number's name. Required.
 * @returns The number, or zero when the run did not record it.
 */
export function metric(
  summary: Readonly<Record<string, number>> | null = null,
  key: string | null = null,
): number {
  // log.debug('Takes the summary, which the caller must give')
  summary = required({ summary });
  // log.debug('Takes the key, which the caller must give')
  key = required({ key });
  // log.debug('Returns the number, or zero when the run did not record it')
  return summary[key] ?? 0;
}

// log.debug('Defines the cases that ran to the end')
/**
 * Returns the cases that ran to the end, leaving out those that failed.
 *
 * @param results - The run's cases. Required.
 * @returns The cases that did not fail, in order.
 */
export function finished(results: readonly CaseResult[] | null = null): CaseResult[] {
  // log.debug('Takes the results, which the caller must give')
  results = required({ results });
  // log.debug('Returns the cases that did not fail')
  return results.filter((result) => result.ok);
}

// log.debug('Defines the cases of one kind')
/**
 * Returns the cases of one kind.
 *
 * @param results - The run's cases. Required.
 * @param tag - The kind's tag. Required.
 * @returns The cases that carry the tag, in order.
 */
export function ofKind(
  results: readonly CaseResult[] | null = null,
  tag: string | null = null,
): CaseResult[] {
  // log.debug('Takes the results, which the caller must give')
  results = required({ results });
  // log.debug('Takes the tag, which the caller must give')
  tag = required({ tag });
  // log.debug('Returns the cases that carry the tag')
  return results.filter((result) => result.tags.includes(tag));
}

// log.debug('Defines the kinds of case in a run, in order')
/**
 * Returns the kinds of case in a run.
 *
 * @param results - The run's cases. Required.
 * @returns Each tag the cases carry, once, sorted.
 */
export function kinds(results: readonly CaseResult[] | null = null): string[] {
  // log.debug('Takes the results, which the caller must give')
  results = required({ results });
  // log.debug('Returns each tag once, sorted')
  return [...new Set(results.flatMap((result) => result.tags))].sort((a, b) => a.localeCompare(b));
}

// log.debug('Defines the average of some numbers')
/**
 * Returns the average of some numbers.
 *
 * @param values - The numbers. Required.
 * @returns Their sum over their count, or zero when there are none.
 */
export function mean(values: readonly number[] | null = null): number {
  // log.debug('Takes the values, which the caller must give')
  values = required({ values });
  // log.debug('Returns zero for no numbers, else their sum over their count')
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

// log.debug('Defines one score of one case')
/**
 * Returns one score of one case.
 *
 * @param result - The case. Required.
 * @param key - The score's name. Required.
 * @returns The score, or zero when the case has no number by that name.
 */
export function score(result: CaseResult | null = null, key: string | null = null): number {
  // log.debug('Takes the result, which the caller must give')
  result = required({ result });
  // log.debug('Takes the key, which the caller must give')
  key = required({ key });
  // log.debug('Reads the score')
  const value = result.scores[key];
  // log.debug('Returns it when it is a number, or zero')
  return typeof value === 'number' ? value : 0;
}

// log.debug('Defines the average of one score over the cases that finished')
/**
 * Returns the average of one score over the cases that finished.
 *
 * @param results - The cases to average over. Required.
 * @param key - The score's name. Required.
 * @returns The mean of the score over the cases that did not fail.
 */
export function average(
  results: readonly CaseResult[] | null = null,
  key: string | null = null,
): number {
  // log.debug('Takes the results, which the caller must give')
  results = required({ results });
  // log.debug('Takes the key, which the caller must give')
  key = required({ key });
  // log.debug('Returns the mean of the score over those cases')
  return mean(finished(results).map((result) => score(result, key)));
}

// log.debug('Defines how often a field was right over a run')
/**
 * Returns the share of cases in which a field was right.
 *
 * @param results - The run's cases. Required.
 * @param name - The field's name. Required.
 * @returns The field's own score averaged over the cases that finished.
 */
export function fieldAccuracy(
  results: readonly CaseResult[] | null = null,
  name: string | null = null,
): number {
  // log.debug('Takes the results, which the caller must give')
  results = required({ results });
  // log.debug('Takes the name, which the caller must give')
  name = required({ name });
  // log.debug('Returns the average of the score of the field')
  return average(results, `${FIELD_SCORE}${name}`);
}

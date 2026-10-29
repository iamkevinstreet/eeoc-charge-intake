// ########################################################################
// #                        frontend/src/scores.ts                        #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           Reads an evaluation run: summary numbers, case   #
// #                     scores, averages, and accuracy by field and      #
// #                     kind.                                            #
// ########################################################################
/** Reads an evaluation run: summary numbers, case scores, and averages by field and by kind. */

import { SUMMARY_FIELD } from './config';
import { FIELD_LABELS } from './format';
import type { CaseResult } from './types';

// log.debug('Sets the prefix of the score each field earns in a case')
const FIELD_SCORE = 'f_';

// log.debug('Lists the fields scored against the known answers; a summary is a paraphrase')
export const SCORED: readonly string[] = Object.keys(FIELD_LABELS).filter(
  (name) => name !== SUMMARY_FIELD,
);

// log.debug('Defines one number from the summary of a run')
export function metric(summary: Readonly<Record<string, number>>, key: string): number {
  // log.debug('Returns the number, or zero when the run did not record it')
  return summary[key] ?? 0;
}

// log.debug('Defines the cases that ran to the end')
export function finished(results: readonly CaseResult[]): CaseResult[] {
  // log.debug('Returns the cases that did not fail')
  return results.filter((result) => result.ok);
}

// log.debug('Defines the cases of one kind')
export function ofKind(results: readonly CaseResult[], tag: string): CaseResult[] {
  // log.debug('Returns the cases that carry the tag')
  return results.filter((result) => result.tags.includes(tag));
}

// log.debug('Defines the kinds of case in a run, in order')
export function kinds(results: readonly CaseResult[]): string[] {
  // log.debug('Returns each tag once, sorted')
  return [...new Set(results.flatMap((result) => result.tags))].sort((a, b) => a.localeCompare(b));
}

// log.debug('Defines the average of some numbers')
export function mean(values: readonly number[]): number {
  // log.debug('Returns zero for no numbers, else their sum over their count')
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

// log.debug('Defines one score of one case')
export function score(result: CaseResult, key: string): number {
  // log.debug('Reads the score')
  const value = result.scores[key];
  // log.debug('Returns it when it is a number, or zero')
  return typeof value === 'number' ? value : 0;
}

// log.debug('Defines the average of one score over the cases that finished')
export function average(results: readonly CaseResult[], key: string): number {
  // log.debug('Returns the mean of the score over those cases')
  return mean(finished(results).map((result) => score(result, key)));
}

// log.debug('Defines how often a field was right over a run')
export function fieldAccuracy(results: readonly CaseResult[], name: string): number {
  // log.debug('Returns the average of the score of the field')
  return average(results, `${FIELD_SCORE}${name}`);
}

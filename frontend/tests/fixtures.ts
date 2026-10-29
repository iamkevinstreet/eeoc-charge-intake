// ########################################################################
// #                      frontend/tests/fixtures.ts                      #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Made-up samples, a review and an evaluation run that the tests render
 * and stub fetch with. The record is built from the quotes on its page,
 * so every quote is there to be found.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { required } from '../src/lib/required';
import type { Health, Review, RunResult, Sample, Sourced, Value } from '../src/types';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the quote behind each field, as the charge page has it')
const QUOTES = {
  number: 'EEOC Charge No. 451-2026-01234',
  party: 'Charging Party: Dana Whitfield',
  respondent: 'Respondent: Harbor Freightways LLC',
  office: 'Phoenix District Office',
  bases: 'Bases: Race, Retaliation',
  issues: 'Issues: Discharge',
  earliest: 'Earliest: 03/02/2026',
  latest: 'Latest: 06/15/2026',
  notice: 'Date: October 1, 2026',
};
// log.debug('Sets the charge page, built from the quotes so that each is on it')
const CHARGE_PAGE = [
  'CHARGE OF DISCRIMINATION',
  QUOTES.number,
  QUOTES.party,
  QUOTES.respondent,
  QUOTES.office,
  QUOTES.bases,
  QUOTES.issues,
  `${QUOTES.earliest}    ${QUOTES.latest}`,
].join('\n');
// log.debug('Sets the notice page the notice date comes from')
const NOTICE_PAGE = `NOTICE OF CHARGE OF DISCRIMINATION\n${QUOTES.notice}`;
// log.debug('Sets the confidence the model gave every field')
const CONFIDENCE = 0.92;
// log.debug('Sets the model the offline stand-in reports')
const MODEL = 'fake-model';
// log.debug('Sets the id of the first sample, a clean case')
const FIRST = 'charge-000';
// log.debug('Sets the id of the second sample, a hard case')
const SECOND = 'charge-001';
// log.debug('Sets the tag of a clean case')
const CLEAN = 'clean';
// log.debug('Sets the tag of a case with no charge number')
const MISSING = 'missing_number';
// log.debug('Sets the extracted record, one field per line of the charge')
export const RECORD: Record<string, Sourced> = {
  charge_number: field('451-2026-01234', QUOTES.number),
  charging_party: field('Dana Whitfield', QUOTES.party),
  respondent: field('Harbor Freightways LLC', QUOTES.respondent),
  eeoc_office: field(QUOTES.office, QUOTES.office),
  bases: field(['Race', 'Retaliation'], QUOTES.bases),
  issues: field(['Discharge'], QUOTES.issues),
  earliest_date: field('2026-03-02', QUOTES.earliest),
  latest_date: field('2026-06-15', QUOTES.latest),
  continuing_action: field(false, null),
  notice_date: field('2026-10-01', QUOTES.notice),
  summary: field('The charging party says she was dismissed after reporting harassment.', null),
};
// log.debug('Lists the fields in the order the record shows them')
export const FIELDS = Object.keys(RECORD);
// log.debug('Sets a review of a generated sample with no decisions yet')
export const REVIEW: Review = {
  review_id: 'r-0123456789',
  source: `sample:${FIRST}`,
  demo: true,
  created_at: '2026-10-29T12:00:00+00:00',
  request_id: 'req-1',
  model: MODEL,
  cost_usd: 0,
  latency_ms: 1200,
  fields: FIELDS,
  record: RECORD,
  raw: RECORD,
  removed: [],
  pages: { charge: [CHARGE_PAGE], notice: [NOTICE_PAGE] },
  decisions: {},
  decided: 0,
  total: FIELDS.length,
};
// log.debug('Sets the health report of the offline stand-in')
export const HEALTH: Health = { ok: true, provider: 'fake', model: MODEL, demo: true };
// log.debug('Sets two generated samples, the second a hard case')
export const SAMPLES: Sample[] = [
  { id: FIRST, tags: [CLEAN], charge_pdf: `${FIRST}.pdf`, notice_pdf: 'notice-000.pdf' },
  {
    id: SECOND,
    tags: [MISSING, 'rotated'],
    charge_pdf: `${SECOND}.pdf`,
    notice_pdf: 'notice-001.pdf',
  },
];
// log.debug('Sets an evaluation run of two cases, one with the charge number wrong')
export const RUN: RunResult = {
  name: 'live-test-model',
  model: 'test-model',
  provider: 'anthropic',
  started_at: '2026-10-26T15:39:06+00:00',
  finished_at: '2026-10-26T15:55:08+00:00',
  prices_as_of: '2026-10-15',
  cases: 2,
  failures: 0,
  summary: {
    field_accuracy: 0.95,
    unsupported_rate: 0.004,
    false_abstentions: 0.5,
    guesses: 0,
    latency_p50_ms: 4510,
    latency_p95_ms: 5572,
    cost_per_case_usd: 0.013375,
  },
  results: [
    {
      case_id: FIRST,
      tags: [CLEAN],
      ok: true,
      scores: scores([], { field_accuracy: 1, unsupported_removed: 0, false_abstentions: 0 }),
      error: null,
      latency_ms: 4522,
      cost_usd: 0.012,
      calls: 1,
    },
    {
      case_id: SECOND,
      tags: [MISSING],
      ok: true,
      scores: scores(['charge_number'], { field_accuracy: 0.9, false_abstentions: 1 }),
      error: null,
      latency_ms: 4498,
      cost_usd: 0.0147,
      calls: 1,
    },
  ],
};

// ########################################################################
// #                            Test fixtures                             #
// ########################################################################
// log.debug('Defines one extracted field, quoted from the first page of its document')
/**
 * Returns one extracted field, quoted from the first page of its
 * document.
 *
 * @param value - The field's value; null for an empty field.
 * @param span - The text it quotes; null for a field with no quote.
 * @returns The field, on page 1 when it has a quote, with the model's
 *   confidence.
 */
function field(value: Value = null, span: string | null = null): Sourced {
  // log.debug('Returns the field with its confidence')
  return { value, page: span === null ? null : 1, span, confidence: CONFIDENCE, reason: null };
}

// log.debug('Defines the scores of one case: every field right except those named')
/**
 * Returns the scores of one case: every field right except those named,
 * with the case's totals.
 *
 * @param wrong - The fields the case got wrong. Required.
 * @param totals - The case's headline scores, by name. Required.
 * @returns A one or a zero for each field's own score, with the totals.
 */
function scores(
  wrong: readonly string[] | null = null,
  totals: Record<string, number> | null = null,
): Record<string, number> {
  // log.debug('Takes the fields it got wrong, which the caller must give')
  wrong = required({ wrong });
  // log.debug('Takes the totals, which the caller must give')
  totals = required({ totals });
  // log.debug('Scores each field one, or zero when it is among the wrong ones')
  const fields = FIELDS.map((name): [string, number] => [
    `f_${name}`,
    wrong.includes(name) ? 0 : 1,
  ]);
  // log.debug('Returns the field scores with the totals of the case')
  return { ...Object.fromEntries(fields), ...totals };
}

// ########################################################################
// #                        frontend/src/format.ts                        #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           How values are written for people: field, tag    #
// #                     and decision names, shares, money, time,         #
// #                     classes.                                         #
// ########################################################################
/** How values are written for people: field, tag and decision names, shares, money, time. */

import type { Action } from './types';

// log.debug('Sets the percent in a whole')
const PERCENT = 100;
// log.debug('Sets the share, in percent, under which a share keeps one decimal')
const FINE_SHARE = 10;
// log.debug('Sets the milliseconds in a second')
const MS = 1000;
// log.debug('Sets the decimal places dollar amounts are shown with')
const CENTS_PLACES = 4;
// log.debug('Sets the decimal places counts per case are shown with')
const RATE_PLACES = 2;
// log.debug('Sets what separates the classes of an element')
const SPACE = ' ';

// log.debug('Lists the name of each field, in the order the record shows them')
export const FIELD_LABELS: Readonly<Record<string, string>> = {
  charge_number: 'Charge number',
  charging_party: 'Charging party',
  respondent: 'Respondent',
  eeoc_office: 'EEOC office',
  bases: 'Bases',
  issues: 'Issues',
  earliest_date: 'Earliest date',
  latest_date: 'Latest date',
  continuing_action: 'Continuing action',
  notice_date: 'Notice date',
  summary: 'Summary',
};

// log.debug('Lists the name of each kind of generated case')
export const TAG_LABELS: Readonly<Record<string, string>> = {
  clean: 'Clean',
  missing_number: 'Missing charge number',
  rotated: 'Rotated page',
  long: 'Long particulars',
  two_respondents: 'Two respondents',
};

// log.debug('Lists the decisions, in the order the buttons show them')
export const ACTIONS: readonly Action[] = ['accept', 'edit', 'reject'];

// log.debug('Lists the button that makes each decision')
export const ACTION_VERBS: Readonly<Record<Action, string>> = {
  accept: 'Accept',
  edit: 'Edit',
  reject: 'Reject',
};

// log.debug('Lists the label a field carries once decided')
export const ACTION_LABELS: Readonly<Record<Action, string>> = {
  accept: 'Accepted',
  edit: 'Edited',
  reject: 'Rejected',
};

// log.debug('Defines the name people see for a field')
export function fieldLabel(name: string): string {
  // log.debug('Returns the label, or the field name when there is none')
  return FIELD_LABELS[name] ?? name;
}

// log.debug('Defines the name people see for a kind of case')
export function tagLabel(tag: string): string {
  // log.debug('Returns the label, or the tag when there is none')
  return TAG_LABELS[tag] ?? tag;
}

// log.debug('Defines a fraction as a whole percent')
export function percent(fraction: number): number {
  // log.debug('Returns the rounded percent')
  return Math.round(fraction * PERCENT);
}

// log.debug('Defines how a share is written: whole percents, one decimal under ten')
export function share(fraction: number): string {
  // log.debug('Turns the fraction into a percent')
  const value = fraction * PERCENT;
  // log.debug('Keeps one decimal for a small share that is not zero')
  const fine = value > 0 && value < FINE_SHARE;
  // log.debug('Returns the percent with its sign')
  return `${fine ? value.toFixed(1) : Math.round(value)}%`;
}

// log.debug('Defines how a cost is written')
export function money(usd: number): string {
  // log.debug('Returns the dollars to four places, since a document costs cents')
  return `$${usd.toFixed(CENTS_PLACES)}`;
}

// log.debug('Defines how a duration is written')
export function seconds(ms: number): string {
  // log.debug('Returns the seconds to one place')
  return `${(ms / MS).toFixed(1)} s`;
}

// log.debug('Defines how a count per case is written')
export function rate(count: number): string {
  // log.debug('Returns the count to two places')
  return count.toFixed(RATE_PLACES);
}

// log.debug('Defines how the classes of an element are joined, leaving out those switched off')
export function classes(...names: (string | false | null | undefined)[]): string {
  // log.debug('Returns the classes that are on, separated by spaces')
  return names.filter(Boolean).join(SPACE);
}

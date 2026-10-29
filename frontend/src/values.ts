// ########################################################################
// #                        frontend/src/values.ts                        #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           What a field holds: the empty field, how a value #
// #                     is shown, and how a typed value is read back.    #
// ########################################################################
/** What a field holds: the empty field, how a value is shown, how a typed value is read back. */

import { LIST_FIELDS, YES_NO_FIELD } from './config';
import type { Sourced, Value } from './types';

// log.debug('Sets the word shown for a true value')
export const YES = 'Yes';
// log.debug('Sets the word shown for a false value')
export const NO = 'No';
// log.debug('Sets what joins the items of a list value')
const JOIN = ', ';
// log.debug('Sets what separates the items a reviewer types')
const SPLIT = ',';
// log.debug('Matches the answers that mean yes, whatever their case')
const SAYS_YES = /^(?:y|yes|true|1)$/i;
// log.debug('Sets the field shown when a record lacks one: empty, unquoted, with no confidence')
export const EMPTY: Sourced = { value: null, page: null, span: null, confidence: 0, reason: null };

// log.debug('Defines how one field is found in a record')
export function fieldOf(record: Readonly<Record<string, Sourced>>, name: string): Sourced {
  // log.debug('Returns the field, or the empty field when the record lacks it')
  return record[name] ?? EMPTY;
}

// log.debug('Defines the test for a value with nothing in it')
export function isEmpty(value: Value): boolean {
  // log.debug('Returns true for null, an empty string or an empty list')
  return value === null || value === '' || (Array.isArray(value) && value.length === 0);
}

// log.debug('Defines how a value is written for people')
export function formatValue(value: Value): string {
  // log.debug('Writes nothing for an empty value')
  if (value === null) {
    // log.debug('Returns an empty string')
    return '';
  }
  // log.debug('Writes a list with commas between its items')
  if (Array.isArray(value)) {
    // log.debug('Returns the joined items')
    return value.join(JOIN);
  }
  // log.debug('Writes a true or false value as a word')
  if (typeof value === 'boolean') {
    // log.debug('Returns the word for yes or for no')
    return value ? YES : NO;
  }
  // log.debug('Returns text as it is')
  return value;
}

// log.debug('Defines how what a reviewer typed is read back into the shape of the field')
export function parseValue(name: string, text: string, original: Value): Value {
  // log.debug('Removes the space around what was typed')
  const typed = text.trim();
  // log.debug('Reads a yes or no field as true or false')
  if (name === YES_NO_FIELD || typeof original === 'boolean') {
    // log.debug('Returns true only for an answer that means yes')
    return SAYS_YES.test(typed);
  }
  // log.debug('Reads a list field as its comma separated items')
  if (LIST_FIELDS.includes(name) || Array.isArray(original)) {
    // log.debug('Returns the trimmed items, leaving out blanks')
    return typed
      .split(SPLIT)
      .map((item) => item.trim())
      .filter((item) => item !== '');
  }
  // log.debug('Returns the text, or null when nothing was typed')
  return typed === '' ? null : typed;
}

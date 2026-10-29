// ########################################################################
// #                        frontend/src/values.ts                        #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * What a field holds: the empty field, how a value is shown, and how a
 * value a reviewer types is read back into the field's shape.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from './config';
import { required } from './lib/required';
import type { Sourced, Value } from './types';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the word shown for a true value from the config')
const YES = CONFIG.labels.yes;
// log.debug('Takes the word shown for a false value from the config')
const NO = CONFIG.labels.no;
// log.debug('Takes what joins the items of a list value from the config')
const JOIN = CONFIG.labels.join;
// log.debug('Takes the field that holds a yes or a no from the config')
const YES_NO_FIELD = CONFIG.record.yes_no_field;
// log.debug('Takes the fields that hold lists from the config')
const LIST_FIELDS = CONFIG.record.list_fields;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets what separates the items a reviewer types')
const SPLIT = ',';
// log.debug('Matches the answers that mean yes, whatever their case')
const SAYS_YES = /^(?:y|yes|true|1)$/i;
// log.debug('Sets the field shown when a record lacks one: empty, unquoted, with no confidence')
export const EMPTY: Sourced = { value: null, page: null, span: null, confidence: 0, reason: null };

// ########################################################################
// #                             Field values                             #
// ########################################################################
// log.debug('Defines how one field is found in a record')
/**
 * Returns one field of a record, or the empty field when it lacks it.
 *
 * @param record - The record, each field by its name. Required.
 * @param name - The field's name. Required.
 * @returns The field with its evidence, or the empty field.
 */
export function fieldOf(
  record: Readonly<Record<string, Sourced>> | null = null,
  name: string | null = null,
): Sourced {
  // log.debug('Takes the record, which the caller must give')
  record = required({ record });
  // log.debug('Takes the name, which the caller must give')
  name = required({ name });
  // log.debug('Returns the field, or the empty field when the record lacks it')
  return record[name] ?? EMPTY;
}

// log.debug('Defines the test for a value with nothing in it')
/**
 * Tells whether a value holds nothing.
 *
 * @param value - The value; null is a field with no value.
 * @returns True for null, an empty string or an empty list.
 */
export function isEmpty(value: Value = null): boolean {
  // log.debug('Returns true for null, an empty string or an empty list')
  return value === null || value === '' || (Array.isArray(value) && value.length === 0);
}

// log.debug('Defines how a value is written for people')
/**
 * Returns a value as people read it.
 *
 * @param value - The value; null is a field with no value.
 * @returns A list's items joined, yes or no in words, text as it is,
 *   and nothing for null.
 */
export function formatValue(value: Value = null): string {
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
/**
 * Returns what a reviewer typed in the shape the field holds.
 *
 * @param name - The field's name. Required.
 * @param text - What the reviewer typed. Required.
 * @param original - The value the field held before the edit, whose
 *   shape the typed value takes; null when the field was empty.
 * @returns True or false for a yes or no field, a list for a list
 *   field, else the text, or null when nothing was typed.
 */
export function parseValue(
  name: string | null = null,
  text: string | null = null,
  original: Value = null,
): Value {
  // log.debug('Takes the name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the text, which the caller must give')
  text = required({ text });
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

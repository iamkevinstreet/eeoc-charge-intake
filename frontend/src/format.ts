// ########################################################################
// #                        frontend/src/format.ts                        #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * How values are written for people: the names of fields and kinds of
 * case, shares, money, time, counts per case, and an element's classes.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from './config';
import { required } from './lib/required';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the percent in a whole from the config')
const PERCENT = CONFIG.units.percent;
// log.debug('Takes the milliseconds in a second from the config')
const MS = CONFIG.units.ms_per_second;
// log.debug('Takes the name of each field, in the order the record shows them, from the config')
const FIELD_LABELS = CONFIG.labels.fields;
// log.debug('Takes the name of each kind of generated case from the config')
const TAG_LABELS = CONFIG.labels.kinds;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the share, in percent, under which a share keeps one decimal')
const FINE_SHARE = 10;
// log.debug('Sets the decimal places dollar amounts are shown with')
const CENTS_PLACES = 4;
// log.debug('Sets the decimal places counts per case are shown with')
const RATE_PLACES = 2;
// log.debug('Sets what separates the classes of an element')
const SPACE = ' ';

// ########################################################################
// #                            Written values                            #
// ########################################################################
// log.debug('Defines the name people see for a field')
/**
 * Returns the name people see for a field.
 *
 * @param name - The field's name in the record. Required.
 * @returns The field's label, or its name when it has none.
 */
export function fieldLabel(name: string | null = null): string {
  // log.debug('Takes the name, which the caller must give')
  name = required({ name });
  // log.debug('Returns the label, or the field name when there is none')
  return FIELD_LABELS[name] ?? name;
}

// log.debug('Defines the name people see for a kind of case')
/**
 * Returns the name people see for a kind of case.
 *
 * @param tag - The kind's tag, as a sample or a result carries it.
 *   Required.
 * @returns The kind's label, or its tag when it has none.
 */
export function tagLabel(tag: string | null = null): string {
  // log.debug('Takes the tag, which the caller must give')
  tag = required({ tag });
  // log.debug('Returns the label, or the tag when there is none')
  return TAG_LABELS[tag] ?? tag;
}

// log.debug('Defines a fraction as a whole percent')
/**
 * Returns a fraction as a whole percent.
 *
 * @param fraction - The share, from 0 to 1. Required.
 * @returns The percent, rounded to a whole number.
 */
export function percent(fraction: number | null = null): number {
  // log.debug('Takes the fraction, which the caller must give')
  fraction = required({ fraction });
  // log.debug('Returns the rounded percent')
  return Math.round(fraction * PERCENT);
}

// log.debug('Defines how a share is written: whole percents, one decimal under ten')
/**
 * Returns a share as a percent, with one decimal for a small share.
 *
 * @param fraction - The share, from 0 to 1. Required.
 * @returns The percent with its sign: one decimal for a share above 0
 *   and under 10%, whole otherwise.
 */
export function share(fraction: number | null = null): string {
  // log.debug('Takes the fraction, which the caller must give')
  fraction = required({ fraction });
  // log.debug('Turns the fraction into a percent')
  const value = fraction * PERCENT;
  // log.debug('Keeps one decimal for a small share that is not zero')
  const fine = value > 0 && value < FINE_SHARE;
  // log.debug('Returns the percent with its sign')
  return `${fine ? value.toFixed(1) : Math.round(value)}%`;
}

// log.debug('Defines how a cost is written')
/**
 * Returns a cost in dollars to four places, since a document costs
 * cents.
 *
 * @param usd - The cost in US dollars. Required.
 * @returns The cost with its dollar sign.
 */
export function money(usd: number | null = null): string {
  // log.debug('Takes the cost, which the caller must give')
  usd = required({ usd });
  // log.debug('Returns the dollars to four places, since a document costs cents')
  return `$${usd.toFixed(CENTS_PLACES)}`;
}

// log.debug('Defines how a duration is written')
/**
 * Returns a duration in seconds, to one place.
 *
 * @param ms - The duration in milliseconds. Required.
 * @returns The seconds with their unit.
 */
export function seconds(ms: number | null = null): string {
  // log.debug('Takes the duration, which the caller must give')
  ms = required({ ms });
  // log.debug('Returns the seconds to one place')
  return `${(ms / MS).toFixed(1)} s`;
}

// log.debug('Defines how a count per case is written')
/**
 * Returns an average count per case, to two places.
 *
 * @param count - The count per case. Required.
 * @returns The count to two decimal places.
 */
export function rate(count: number | null = null): string {
  // log.debug('Takes the count, which the caller must give')
  count = required({ count });
  // log.debug('Returns the count to two places')
  return count.toFixed(RATE_PLACES);
}

// log.debug('Defines how the classes of an element are joined, leaving out those switched off')
/**
 * Returns an element's class attribute from the classes that are on.
 *
 * @param names - Each class, or false, null or undefined for one that
 *   is off.
 * @returns The classes that are on, separated by spaces.
 */
export function classes(...names: (string | false | null | undefined)[]): string {
  // log.debug('Returns the classes that are on, separated by spaces')
  return names.filter(Boolean).join(SPACE);
}

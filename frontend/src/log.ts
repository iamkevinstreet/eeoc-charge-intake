// ########################################################################
// #                         frontend/src/log.ts                          #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The trace logger: each line it prints is the time since the page
 * loaded as HH:MM:SS, a dash, and what the traced line does. Importing
 * this module makes it the global log every logger line calls once it is
 * switched on.
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
// log.debug('Takes the milliseconds in a second from the config')
const MS = CONFIG.units.ms_per_second;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Notes when the page started, so each line shows elapsed time')
const STARTED = performance.now();
// log.debug('Sets the seconds in a minute and the minutes in an hour')
const SIXTY = 60;
// log.debug('Sets the seconds in an hour')
const HOUR_S = 3600;
// log.debug('Sets the digits in each part of the time')
const DIGITS = 2;

// ########################################################################
// #                             Trace logger                             #
// ########################################################################
// log.debug('Defines how elapsed time is written as HH:MM:SS')
/**
 * Returns the time since the page loaded, as HH:MM:SS.
 *
 * @param now - The moment to measure to, in milliseconds since the page
 *   started loading; by default, now.
 * @returns The hours, minutes and seconds, two digits each, joined by
 *   colons.
 */
export function elapsed(now: number = performance.now()): string {
  // log.debug('Converts the elapsed time to whole seconds')
  const total = Math.floor((now - STARTED) / MS);
  // log.debug('Splits it into hours, minutes and seconds')
  const parts = [Math.floor(total / HOUR_S), Math.floor((total % HOUR_S) / SIXTY), total % SIXTY];
  // log.debug('Returns the parts padded to two digits, joined by colons')
  return parts.map((part) => String(part).padStart(DIGITS, '0')).join(':');
}

// log.debug('Defines the logger the trace lines call')
export const logger = {
  /**
   * Prints one trace line: the time since the page loaded, a dash, and
   * the message.
   *
   * @param message - What the traced line does. Required.
   */
  debug(message: string | null = null): void {
    // log.debug('Takes the message, which the caller must give')
    message = required({ message });
    // log.debug('Prints the time, a dash and the message')
    console.debug(`${elapsed()} - ${message}`);
  },
};

// log.debug('Makes the logger global, so a trace line needs no import')
Object.assign(globalThis, { log: logger });

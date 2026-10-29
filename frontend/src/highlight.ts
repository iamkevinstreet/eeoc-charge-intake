// ########################################################################
// #                      frontend/src/highlight.ts                       #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Finds a quote in a page the way the service checks it, whatever its
 * case and the runs of space inside it, and splits the page around it
 * so the document pane can mark it.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { required } from './lib/required';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Matches the runs of space between the words of a quote')
const SPACES = /\s+/;
// log.debug('Matches the characters a regular expression treats as special')
const SPECIAL = /[.*+?^${}()|[\]\\]/g;
// log.debug('Sets the replacement that escapes each special character')
const ESCAPED = '\\$&';
// log.debug('Sets the pattern that allows any run of space between two words')
const GAP = '\\s+';
// log.debug('Sets the flag that ignores case')
const IGNORE_CASE = 'i';

// ########################################################################
// #                            Quote marking                             #
// ########################################################################
/** A page split around a quote: the text before it, the quote as the page has it, the rest. */
export interface Marked {
  before: string;
  quote: string;
  after: string;
}

// log.debug('Defines how a word is made safe to use in a pattern')
/**
 * Returns a word with every character a pattern treats as special
 * escaped.
 *
 * @param word - One word of the quote. Required.
 * @returns The word, safe to put in a regular expression.
 */
function escapeWord(word: string | null = null): string {
  // log.debug('Takes the word, which the caller must give')
  word = required({ word });
  // log.debug('Returns the word with each special character escaped')
  return word.replace(SPECIAL, ESCAPED);
}

// log.debug('Defines how a quote is found in a page, ignoring case and runs of space')
/**
 * Returns where a quote is in a page, ignoring case and runs of space.
 *
 * @param text - The page's text. Required.
 * @param quote - The quote to find; null or blank finds nothing.
 * @returns Where the quote starts and ends in the page, or null when it
 *   is not there.
 */
export function locate(
  text: string | null = null,
  quote: string | null = null,
): [number, number] | null {
  // log.debug('Takes the text, which the caller must give')
  text = required({ text });
  // log.debug('Takes the quote without the space around it')
  const words = quote?.trim() ?? '';
  // log.debug('Finds nothing for a missing or blank quote')
  if (words === '') {
    // log.debug('Returns no match')
    return null;
  }
  // log.debug('Builds a pattern of the escaped words with any run of space between them')
  const pattern = new RegExp(words.split(SPACES).map(escapeWord).join(GAP), IGNORE_CASE);
  // log.debug('Looks for the pattern in the page')
  const match = pattern.exec(text);
  // log.debug('Returns where the quote starts and ends, or no match')
  return match === null ? null : [match.index, match.index + match[0].length];
}

// log.debug('Defines how a page is split around a quote, so the quote can be marked')
/**
 * Returns a page split around a quote, so the quote can be marked.
 *
 * @param text - The page's text. Required.
 * @param quote - The quote to mark; null or blank marks nothing.
 * @returns The text before the quote, the quote as the page has it, and
 *   the text after it; null when the quote is not on the page.
 */
export function mark(text: string | null = null, quote: string | null = null): Marked | null {
  // log.debug('Takes the text, which the caller must give')
  text = required({ text });
  // log.debug('Finds the quote')
  const found = locate(text, quote);
  // log.debug('Marks nothing when the quote is not on the page')
  if (found === null) {
    // log.debug('Returns no marks')
    return null;
  }
  // log.debug('Takes where the quote starts and ends')
  const [start, end] = found;
  // log.debug('Returns the text before the quote, the quote, and the text after it')
  return { before: text.slice(0, start), quote: text.slice(start, end), after: text.slice(end) };
}

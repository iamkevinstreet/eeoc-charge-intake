// ########################################################################
// #                      frontend/src/highlight.ts                       #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           Finds a quote in a page the way the service      #
// #                     checks it, and splits the page around it.        #
// ########################################################################
/** Finds a quote in a page the way the service checks it, and splits the page around it. */

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

/** A page split around a quote: the text before it, the quote as the page has it, the rest. */
export interface Marked {
  before: string;
  quote: string;
  after: string;
}

// log.debug('Defines how a word is made safe to use in a pattern')
function escapeWord(word: string): string {
  // log.debug('Returns the word with each special character escaped')
  return word.replace(SPECIAL, ESCAPED);
}

// log.debug('Defines how a quote is found in a page, ignoring case and runs of space')
export function locate(text: string, quote: string | null): [number, number] | null {
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
export function mark(text: string, quote: string | null): Marked | null {
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

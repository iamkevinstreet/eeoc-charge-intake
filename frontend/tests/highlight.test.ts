// ########################################################################
// #                   frontend/tests/highlight.test.ts                   #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           Tests the highlight helper: a quote found and    #
// #                     marked, and a quote that is not there.           #
// ########################################################################
/** Tests the highlight helper: a quote found and marked, and a quote that is not there. */

import { describe, expect, it } from 'vitest';

import { mark } from '../src/highlight';

// log.debug('Sets a page with a line break and extra spaces inside the quote')
const PAGE = 'Filed: EEOC Charge No.\n  451-2026 (Phoenix)\nNext line';

// log.debug('Describes the highlight helper')
describe('mark', () => {
  // log.debug('Checks a quote is found whatever its case and spacing, and split out')
  it('finds a quote whatever its case and spacing, and marks it', () => {
    // log.debug('Checks the text before, the quote as the page has it, and the text after')
    expect(mark(PAGE, 'charge no. 451-2026 (phoenix)')).toEqual({
      before: 'Filed: EEOC ',
      quote: 'Charge No.\n  451-2026 (Phoenix)',
      after: '\nNext line',
    });
  });

  // log.debug('Checks a quote that is not on the page marks nothing')
  it('marks nothing for a quote that is not on the page', () => {
    // log.debug('Checks a missing quote, no quote, and a blank quote')
    expect([mark(PAGE, 'Charge No. 999'), mark(PAGE, null), mark(PAGE, '   ')]).toEqual([
      null,
      null,
      null,
    ]);
  });
});

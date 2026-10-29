// ########################################################################
// #                   frontend/tests/Results.test.tsx                    #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           Tests the evaluation screen renders a run's      #
// #                     numbers.                                         #
// ########################################################################
/** Tests the evaluation screen renders a run's numbers. */

import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Results } from '../src/components/Results';
import { RUN } from './fixtures';

// log.debug('Lists the numbers the run should show: accuracy, removed, abstentions, time, cost')
const NUMBERS = ['95%', '0.4%', '0.50', '4510 / 5572 ms', '$0.0134'];

// log.debug('Sets how a count of zero per case is written')
const NONE = '0.00';

// log.debug('Describes the evaluation screen')
describe('Results', () => {
  // log.debug('Checks the headline numbers and the table by kind of case')
  it('renders the numbers of a run', () => {
    // log.debug('Renders the screen with the run')
    render(<Results run={RUN} error={null} />);
    // log.debug('Checks each headline number')
    for (const value of NUMBERS) {
      // log.debug('Checks the number is shown')
      expect(screen.getByText(value)).toBeVisible();
    }
    // log.debug('Finds the row of the hard case in the table by kind')
    const row = screen.getByRole('row', { name: /Missing charge number/ });
    // log.debug('Checks its count, accuracy, removed outputs, false abstentions and guesses')
    expect(
      within(row)
        .getAllByRole('cell')
        .map((cell) => cell.textContent),
    ).toEqual(['Missing charge number', '1', '90%', NONE, '1.00', NONE]);
  });
});

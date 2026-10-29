// ########################################################################
// #                    frontend/tests/Start.test.tsx                     #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Tests that the start screen lists the samples it is given, each with
 * its kinds of case and a button to review it.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

// Local
import { Start } from '../src/components/Start';
import { HEALTH, SAMPLES } from './fixtures';

// ########################################################################
// #                          Start screen tests                          #
// ########################################################################
// log.debug('Describes the start screen')
describe('Start', () => {
  // log.debug('Checks each sample is listed with its kinds and a button to review it')
  it('lists the samples it is given', () => {
    // log.debug('Renders the screen with two samples')
    render(
      <Start
        health={HEALTH}
        samples={SAMPLES}
        busy={null}
        error={null}
        onSample={vi.fn()}
        onUpload={vi.fn()}
      />,
    );
    // log.debug('Checks there is a row for each sample under the header')
    expect(screen.getAllByRole('row')).toHaveLength(SAMPLES.length + 1);
    // log.debug('Checks the first sample can be reviewed')
    expect(screen.getByRole('button', { name: 'Review charge-000.pdf' })).toBeEnabled();
    // log.debug('Checks the second sample names its kinds in words')
    expect(screen.getByText('Missing charge number, Rotated page')).toBeVisible();
  });
});

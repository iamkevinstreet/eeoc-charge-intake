// ########################################################################
// #                    frontend/tests/Review.test.tsx                    #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Tests the review screen: the evidence it shows, each decision it
 * records, and the export it holds until every field has a decision.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { Mock } from 'vitest';

// Local
import { Review } from '../src/components/Review';
import { required } from '../src/lib/required';
import type { Action, Decision, Review as ReviewData } from '../src/types';
import { FIELDS, REVIEW } from './fixtures';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the address decisions are sent to')
const DECISIONS = `/api/v1/reviews/${REVIEW.review_id}/decisions`;
// log.debug('Sets the quote behind the charge number')
const QUOTE = 'EEOC Charge No. 451-2026-01234';
// log.debug('Sets the name people see for the first field')
const CHARGE_NUMBER = 'Charge number';
// log.debug('Sets the button that accepts a field')
const ACCEPT = 'Accept';
// log.debug('Sets the decision an accept sends')
const ACCEPTED: Action = 'accept';
// log.debug('Sets the corrected respondent the edit types')
const CORRECTED = 'Harbor Freightways Inc.';

// ########################################################################
// #                         Review screen tests                          #
// ########################################################################
interface ScreenProps {
  initial?: ReviewData | null;
}

/** The fetch stub the decision tests make, answering with the progress. */
type FetchStub = Mock<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>;

// log.debug('Defines the screen with its state held above it, as the app holds it')
/**
 * Renders the review screen with its review held in state above it, as
 * the app holds it.
 *
 * @param props - The component's props.
 * @param props.initial - The review the screen starts from. Required.
 * @returns The review screen.
 */
function Screen({ initial = null }: ScreenProps = {}): React.JSX.Element {
  // log.debug('Takes the review to start from, which the caller must give')
  initial = required({ initial });
  // log.debug('Keeps the review the screen changes')
  const [review, setReview] = useState(initial);
  // log.debug('Returns the screen')
  return <Review review={review} onChange={setReview} onBack={vi.fn()} />;
}

// log.debug('Defines a fetch stub that answers each decision with the count so far')
/**
 * Stubs fetch to answer each decision with the number decided so far.
 *
 * @param already - The fields decided before the test starts. Required.
 * @returns The stub, which records each call.
 */
function stubDecisions(already: number | null = null): FetchStub {
  // log.debug('Takes the fields already decided, which the caller must give')
  already = required({ already });
  // log.debug('Counts the decisions made')
  let decided = already;
  // log.debug('Returns the stub')
  return vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
    // log.debug('Counts this decision')
    decided += 1;
    // log.debug('Answers with the progress')
    return Promise.resolve(new Response(JSON.stringify({ decided, total: FIELDS.length })));
  });
}

// log.debug('Defines what a stubbed fetch was sent: each address and decision')
/**
 * Returns what a stubbed fetch was sent.
 *
 * @param fetcher - The stub. Required.
 * @returns Each call's address, with its body read back from JSON, or
 *   null for a call with no body.
 */
function sent(fetcher: FetchStub | null = null): [unknown, unknown][] {
  // log.debug('Takes the stub, which the caller must give')
  fetcher = required({ fetcher });
  // log.debug('Returns each address with its body read back from JSON')
  return fetcher.mock.calls.map(([url, init]) => [
    url,
    typeof init?.body === 'string' ? (JSON.parse(init.body) as Decision) : null,
  ]);
}

// log.debug('Defines a button found by its name, among the buttons of one field if one is named')
/**
 * Finds a button by its name, among one field's decision buttons when a
 * field is named.
 *
 * @param name - The button's name. Required.
 * @param field - The name people see for the field whose buttons to
 *   look in; null looks in the whole page.
 * @returns The button.
 */
function button(name: string | null = null, field: string | null = null): HTMLElement {
  // log.debug('Takes the name, which the caller must give')
  name = required({ name });
  // log.debug('Looks in the decision buttons of the field, or in the whole page')
  const scope =
    field === null ? document.body : screen.getByRole('group', { name: `Decide ${field}` });
  // log.debug('Returns the button')
  return within(scope).getByRole('button', { name });
}

// log.debug('Describes what the review screen shows and holds back')
describe('Review', () => {
  // log.debug('Checks the selected field quotes its evidence and the document marks it')
  it('shows the quoted evidence of a field', () => {
    // log.debug('Renders the screen')
    render(<Screen initial={REVIEW} />);
    // log.debug('Checks the field row quotes the text')
    expect(screen.getByText(QUOTE, { selector: 'q' })).toBeVisible();
    // log.debug('Checks the document marks the same text')
    expect(screen.getByText(QUOTE, { selector: 'mark' })).toBeVisible();
  });

  // log.debug('Checks the export stays off until the last field is decided')
  it('keeps export disabled until every field has a decision', async () => {
    // log.debug('Accepts every field but the first')
    const decisions = Object.fromEntries(
      FIELDS.slice(1).map((name): [string, Decision] => [name, { field: name, action: ACCEPTED }]),
    );
    // log.debug('Stubs the decision route, counting from the fields already decided')
    stubDecisions(FIELDS.length - 1);
    // log.debug('Renders the screen with one field left')
    render(<Screen initial={{ ...REVIEW, decisions, decided: FIELDS.length - 1 }} />);
    // log.debug('Finds the export button')
    const exporter = button('Export record');
    // log.debug('Checks it is off with one field left')
    expect(exporter).toBeDisabled();
    // log.debug('Accepts the last field')
    await userEvent.click(button(ACCEPT, CHARGE_NUMBER));
    // log.debug('Checks the export turns on')
    await waitFor(() => expect(exporter).toBeEnabled());
  });
});

// log.debug('Describes the decisions the review screen sends and shows')
describe('Review decisions', () => {
  // log.debug('Checks accepting a field sends and shows the decision')
  it('records an accept', async () => {
    // log.debug('Stubs the decision route')
    const fetcher = stubDecisions(0);
    // log.debug('Renders the screen')
    render(<Screen initial={REVIEW} />);
    // log.debug('Accepts the charge number')
    await userEvent.click(button(ACCEPT, CHARGE_NUMBER));
    // log.debug('Checks the field now says it was accepted')
    expect(await screen.findByText('Accepted')).toBeVisible();
    // log.debug('Checks the decision sent')
    expect(sent(fetcher)).toEqual([[DECISIONS, { field: 'charge_number', action: ACCEPTED }]]);
  });

  // log.debug('Checks editing a field sends and shows the new value')
  it('records an edit with its new value', async () => {
    // log.debug('Stubs the decision route')
    const fetcher = stubDecisions(0);
    // log.debug('Renders the screen')
    render(<Screen initial={REVIEW} />);
    // log.debug('Opens the edit form on the respondent')
    await userEvent.click(button('Edit', 'Respondent'));
    // log.debug('Finds the edit box')
    const box = screen.getByRole('textbox', { name: 'New value for Respondent' });
    // log.debug('Clears the extracted value')
    await userEvent.clear(box);
    // log.debug('Types the corrected name')
    await userEvent.type(box, CORRECTED);
    // log.debug('Saves the edit')
    await userEvent.click(button('Save'));
    // log.debug('Checks the field now says it was edited')
    expect(await screen.findByText('Edited')).toBeVisible();
    // log.debug('Checks the decision sent carries the new value')
    expect(sent(fetcher)).toEqual([
      [DECISIONS, { field: 'respondent', action: 'edit', value: CORRECTED }],
    ]);
  });

  // log.debug('Checks rejecting a field sends and shows the decision')
  it('records a reject', async () => {
    // log.debug('Stubs the decision route')
    const fetcher = stubDecisions(0);
    // log.debug('Renders the screen')
    render(<Screen initial={REVIEW} />);
    // log.debug('Rejects the summary')
    await userEvent.click(button('Reject', 'Summary'));
    // log.debug('Checks the field now says it was rejected')
    expect(await screen.findByText('Rejected')).toBeVisible();
    // log.debug('Checks the decision sent')
    expect(sent(fetcher)).toEqual([[DECISIONS, { field: 'summary', action: 'reject' }]]);
  });
});

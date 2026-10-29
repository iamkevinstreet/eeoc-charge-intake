// ########################################################################
// #                      frontend/tests/api.test.ts                      #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Tests the API client: the URL of each route, and the message from a
 * failed response.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { describe, expect, it, vi } from 'vitest';

// Local
import { ApiError, api, describeError } from '../src/api';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the review the calls name')
const ID = 'r-0123456789';
// log.debug('Sets the method of the routes that only read')
const GET = 'GET';
// log.debug('Sets the method of the routes that change something')
const POST = 'POST';
// log.debug('Names the function the tests stub')
const FETCH = 'fetch';

// ########################################################################
// #                           API client tests                           #
// ########################################################################
// log.debug('Describes the client')
describe('api', () => {
  // log.debug('Checks every route goes to the right address under /api/v1 with its method')
  it('builds the URL of each route under /api/v1', async () => {
    // log.debug('Stubs fetch to answer every call with an empty object')
    const fetcher = vi
      .spyOn(globalThis, FETCH)
      .mockImplementation(() => Promise.resolve(new Response('{}')));
    // log.debug('Makes a small PDF to upload')
    const pdf = new File(['%PDF-1.7'], 'charge.pdf', { type: 'application/pdf' });
    // log.debug('Calls the health route')
    await api.health();
    // log.debug('Calls the samples route')
    await api.samples();
    // log.debug('Calls the upload route')
    await api.extractUpload(pdf, pdf);
    // log.debug('Calls the sample extraction route')
    await api.extractSample('charge-000');
    // log.debug('Calls the review route')
    await api.review(ID);
    // log.debug('Calls the decision route')
    await api.decide(ID, { field: 'bases', action: 'accept' });
    // log.debug('Calls the export route')
    await api.exportReview(ID);
    // log.debug('Calls the evaluation route')
    await api.latestEval();
    // log.debug('Checks each address and method, in order')
    expect(fetcher.mock.calls.map(([url, init]) => [url, init?.method ?? GET])).toEqual([
      ['/api/v1/health', GET],
      ['/api/v1/samples', GET],
      ['/api/v1/extract', POST],
      ['/api/v1/extract/sample/charge-000', POST],
      [`/api/v1/reviews/${ID}`, GET],
      [`/api/v1/reviews/${ID}/decisions`, POST],
      [`/api/v1/reviews/${ID}/export`, GET],
      ['/api/v1/evals/latest', GET],
    ]);
  });

  // log.debug('Checks a refusal carries the message the service gave, with its request id')
  it('surfaces the error message from a failed response', async () => {
    // log.debug('Stubs fetch to refuse the export')
    vi.spyOn(globalThis, FETCH).mockResolvedValue(
      new Response(JSON.stringify({ detail: 'undecided fields: summary' }), {
        status: 409,
        headers: { 'X-Request-ID': 'req-9' },
      }),
    );
    // log.debug('Tries the export and keeps the error')
    const error = await api.exportReview(ID).catch((caught: unknown) => caught);
    // log.debug('Checks the error and the sentence shown for it')
    expect([error instanceof ApiError, describeError(error)]).toEqual([
      true,
      'undecided fields: summary (request req-9)',
    ]);
  });
});

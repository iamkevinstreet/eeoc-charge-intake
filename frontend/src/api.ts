// ########################################################################
// #                         frontend/src/api.ts                          #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The API client: one function per route under the API prefix, and
 * errors that say what went wrong, with the request id the service
 * gave the call.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from './config';
import { required } from './lib/required';
import type { Decision, Export, Health, Progress, Review, RunResult, Sample } from './types';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the address every route starts with from the config')
const BASE = CONFIG.api.base;
// log.debug('Takes the header that carries the request id from the config')
const REQUEST_ID = CONFIG.api.request_id_header;
// log.debug('Takes the port the backend listens on from the config, for the hint')
const PORT = CONFIG.api.port;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the method of the routes that change something')
const POST = 'POST';
// log.debug('Sets the path every review route starts with')
const REVIEWS = '/reviews';
// log.debug('Sets the headers of a JSON body')
const JSON_HEADERS = { 'Content-Type': 'application/json' };

// ########################################################################
// #                              API client                              #
// ########################################################################
// log.debug('Defines the error every failed call raises')
/** A call the service refused or could not answer, with what it said. */
export class ApiError extends Error {
  // log.debug('Holds the HTTP status of the response')
  readonly status: number;
  // log.debug('Holds the id the service gave the request, when it sent one')
  readonly requestId: string | null;

  // log.debug('Defines the constructor with the status and request id')
  /**
   * Builds the error from a failed response.
   *
   * @param status - The response's HTTP status. Required.
   * @param message - What went wrong, in the service's words. Required.
   * @param requestId - The id the service gave the request; null when
   *   it sent none.
   */
  constructor(
    status: number | null = null,
    message: string | null = null,
    requestId: string | null = null,
  ) {
    // log.debug('Takes the status, which the caller must give')
    status = required({ status });
    // log.debug('Takes the message, which the caller must give')
    message = required({ message });
    // log.debug('Passes the message to Error')
    super(message);
    // log.debug('Names the error for logs and tests')
    this.name = 'ApiError';
    // log.debug('Keeps the status')
    this.status = status;
    // log.debug('Keeps the request id')
    this.requestId = requestId;
  }
}

// log.debug('Defines one call to the API')
/**
 * Calls one route and returns its parsed body.
 *
 * @param path - The route's path below the API's address. Required.
 * @param init - The request's method, headers and body; by default a
 *   plain GET.
 * @returns The response's body, parsed from JSON.
 * @throws {ApiError} When the service refuses the call.
 */
async function call<T>(path: string | null = null, init: RequestInit = {}): Promise<T> {
  // log.debug('Takes the path, which the caller must give')
  path = required({ path });
  // log.debug('Sends the request')
  const response = await fetch(`${BASE}${path}`, init);
  // log.debug('Throws with the server explanation when the call failed')
  if (!response.ok) {
    // log.debug('Throws the error with its status and request id')
    throw new ApiError(response.status, await detail(response), response.headers.get(REQUEST_ID));
  }
  // log.debug('Returns the parsed body')
  return (await response.json()) as T;
}

// log.debug('Defines how a failed response is explained')
/**
 * Returns what a failed response says went wrong.
 *
 * @param response - The failed response. Required.
 * @returns The service's message, its validation messages joined, or a
 *   sentence naming the status when the body says nothing readable.
 */
async function detail(response: Response | null = null): Promise<string> {
  // log.debug('Takes the response, which the caller must give')
  response = required({ response });
  // log.debug('Sets the fallback explanation')
  const fallback = `The request failed with status ${response.status}.`;
  // log.debug('Reads the body, which may not be JSON')
  try {
    // log.debug('Parses the body')
    const body = (await response.json()) as { detail?: unknown };
    // log.debug('Returns a plain message as it is')
    if (typeof body.detail === 'string') {
      // log.debug('Returns it')
      return body.detail;
    }
    // log.debug('Joins a list of validation messages')
    if (Array.isArray(body.detail)) {
      // log.debug('Returns each message, joined')
      return body.detail.map((item: { msg?: string }) => item.msg ?? '').join('; ');
    }
    // log.debug('Returns the fallback for any other body')
    return fallback;
  } catch {
    // log.debug('Returns the fallback when the body is not JSON')
    return fallback;
  }
}

// log.debug('Defines the path of one review, or of a route below it')
/**
 * Returns the path of one review, or of a route below it.
 *
 * @param id - The review's id. Required.
 * @param below - The route below the review, if any, such as
 *   /decisions.
 * @returns The path, with the review id made safe for a URL.
 */
function reviewPath(id: string | null = null, below = ''): string {
  // log.debug('Takes the id, which the caller must give')
  id = required({ id });
  // log.debug('Returns the path with the review id made safe')
  return `${REVIEWS}/${encodeURIComponent(id)}${below}`;
}

// log.debug('Defines the form an upload sends: the charge and the notice')
/**
 * Returns the form an upload sends.
 *
 * @param charge - The charge form, a PDF. Required.
 * @param notice - The notice letter, a PDF. Required.
 * @returns The form, holding both files.
 */
function uploadForm(charge: File | null = null, notice: File | null = null): FormData {
  // log.debug('Takes the charge form, which the caller must give')
  charge = required({ charge });
  // log.debug('Takes the notice letter, which the caller must give')
  notice = required({ notice });
  // log.debug('Starts an empty form')
  const form = new FormData();
  // log.debug('Adds the charge form')
  form.append('charge', charge);
  // log.debug('Adds the notice letter')
  form.append('notice', notice);
  // log.debug('Returns the form')
  return form;
}

// log.debug('Defines one function per route')
export const api = {
  health: (): Promise<Health> => call('/health'),
  samples: (): Promise<Sample[]> => call('/samples'),
  extractUpload: (charge: File, notice: File): Promise<Review> =>
    call('/extract', { method: POST, body: uploadForm(charge, notice) }),
  extractSample: (id: string): Promise<Review> =>
    call(`/extract/sample/${encodeURIComponent(id)}`, { method: POST }),
  review: (id: string): Promise<Review> => call(reviewPath(id)),
  decide: (id: string, decision: Decision): Promise<Progress> =>
    call(reviewPath(id, '/decisions'), {
      method: POST,
      headers: JSON_HEADERS,
      body: JSON.stringify(decision),
    }),
  exportReview: (id: string): Promise<Export> => call(reviewPath(id, '/export')),
  latestEval: (): Promise<RunResult> => call('/evals/latest'),
};

// log.debug('Defines the sentence shown when a call fails')
/**
 * Returns the sentence shown when a call fails.
 *
 * @param error - What the call threw; anything but an API error means
 *   the service did not answer.
 * @returns The service's explanation with its request id, or a hint to
 *   check that the backend is running.
 */
export function describeError(error: unknown = null): string {
  // log.debug('Explains an API error with its request id, when there is one')
  if (error instanceof ApiError) {
    // log.debug('Returns the server explanation and the request id')
    return error.requestId ? `${error.message} (request ${error.requestId})` : error.message;
  }
  // log.debug('Explains a network failure: the service did not answer')
  return `The service did not answer. Check that the backend is running on port ${PORT}.`;
}

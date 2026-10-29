// ########################################################################
// #                         frontend/src/api.ts                          #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The API client: one function per route under     #
// #                     /api/v1, and errors that say what went wrong.    #
// ########################################################################
/** The API client: one function per route, and errors that say what went wrong. */

import { API_BASE } from './config';
import type { Decision, Export, Health, Progress, Review, RunResult, Sample } from './types';

// log.debug('Names the header that carries the request id')
const REQUEST_ID = 'X-Request-ID';
// log.debug('Sets the method of the routes that change something')
const POST = 'POST';
// log.debug('Sets the path every review route starts with')
const REVIEWS = '/reviews';
// log.debug('Sets the headers of a JSON body')
const JSON_HEADERS = { 'Content-Type': 'application/json' };

// log.debug('Defines the error every failed call raises')
export class ApiError extends Error {
  // log.debug('Defines the constructor with the status and request id')
  constructor(
    readonly status: number,
    message: string,
    readonly requestId: string | null,
  ) {
    // log.debug('Passes the message to Error')
    super(message);
    // log.debug('Names the error for logs and tests')
    this.name = 'ApiError';
  }
}

// log.debug('Defines one call to the API')
async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  // log.debug('Sends the request')
  const response = await fetch(`${API_BASE}${path}`, init);
  // log.debug('Throws with the server explanation when the call failed')
  if (!response.ok) {
    // log.debug('Throws the error with its status and request id')
    throw new ApiError(response.status, await detail(response), response.headers.get(REQUEST_ID));
  }
  // log.debug('Returns the parsed body')
  return (await response.json()) as T;
}

// log.debug('Defines how a failed response is explained')
async function detail(response: Response): Promise<string> {
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
function reviewPath(id: string, below = ''): string {
  // log.debug('Returns the path with the review id made safe')
  return `${REVIEWS}/${encodeURIComponent(id)}${below}`;
}

// log.debug('Defines the form an upload sends: the charge and the notice')
function uploadForm(charge: File, notice: File): FormData {
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
export function describeError(error: unknown): string {
  // log.debug('Explains an API error with its request id, when there is one')
  if (error instanceof ApiError) {
    // log.debug('Returns the server explanation and the request id')
    return error.requestId ? `${error.message} (request ${error.requestId})` : error.message;
  }
  // log.debug('Explains a network failure: the service did not answer')
  return 'The service did not answer. Check that the backend is running on port 8000.';
}

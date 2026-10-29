// ########################################################################
// #                        frontend/src/types.ts                         #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The API's shapes in TypeScript, as the backend   #
// #                     returns them.                                    #
// ########################################################################
/** The API's shapes, as the backend returns them. */

/** What a field may hold: text, a list, a yes or no, or nothing. */
export type Value = string | string[] | boolean | null;
/** What a reviewer may do with a field. */
export type Action = 'accept' | 'edit' | 'reject';
/** The two documents a charge comes with. */
export type DocKind = 'charge' | 'notice';

/** One extracted field with its evidence. */
export interface Sourced {
  value: Value;
  /** The page the quote is on, counted from 1. */
  page: number | null;
  /** The text quoted from that page. */
  span: string | null;
  confidence: number;
  /** Why the field is empty, when it is. */
  reason: string | null;
}

/** A reviewer's decision on one field; an edit carries the new value. */
export interface Decision {
  field: string;
  action: Action;
  value?: Value;
}

/** How many fields have a decision, out of how many. */
export interface Progress {
  decided: number;
  total: number;
}

/** One extraction under review, with the decisions made so far. */
export interface Review {
  review_id: string;
  source: string;
  demo: boolean;
  created_at: string;
  request_id: string;
  model: string;
  cost_usd: number;
  latency_ms: number;
  fields: string[];
  record: Record<string, Sourced>;
  /** The record as the model gave it, before verification emptied any field. */
  raw: Record<string, Sourced>;
  removed: string[];
  pages: Record<DocKind, string[]>;
  decisions: Record<string, Decision>;
  decided: number;
  total: number;
}

/** A generated charge form and notice letter with known answers. */
export interface Sample {
  id: string;
  tags: string[];
  charge_pdf: string;
  notice_pdf: string;
}

/** The service's health report. */
export interface Health {
  ok: boolean;
  provider: string;
  model: string;
  demo: boolean;
}

/** The record exported once every field has a decision. */
export interface Export {
  review_id: string;
  exported_at: string;
  record: Record<string, Value>;
  response_due: string | null;
  decisions: Record<string, Action>;
}

/** One case of an evaluation run and its scores. */
export interface CaseResult {
  case_id: string;
  tags: string[];
  ok: boolean;
  scores: Record<string, unknown>;
  error: string | null;
  latency_ms: number;
  cost_usd: number;
  calls: number;
}

/** An evaluation run: its setup, its summary numbers and every case. */
export interface RunResult {
  name: string;
  model: string;
  provider: string;
  started_at: string;
  finished_at: string;
  prices_as_of: string;
  cases: number;
  failures: number;
  summary: Record<string, number>;
  results: CaseResult[];
}

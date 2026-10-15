export type Value = string | string[] | boolean | null;

export interface Sourced {
  value: Value;
  page: number | null;
  span: string | null;
  confidence: number;
  reason: string | null;
}

export type Action = 'accept' | 'edit' | 'reject';

export interface Decision {
  field: string;
  action: Action;
  value?: Value;
}

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
  raw: Record<string, Sourced>;
  removed: string[];
  pages: { charge: string[]; notice: string[] };
  decisions: Record<string, Decision>;
  decided: number;
  total: number;
}

export interface Sample {
  id: string;
  tags: string[];
  charge_pdf: string;
  notice_pdf: string;
}

export interface Health {
  ok: boolean;
  provider: string;
  model: string;
  demo: boolean;
}

export interface Export {
  review_id: string;
  exported_at: string;
  record: Record<string, Value>;
  response_due: string | null;
  decisions: Record<string, Action>;
}

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

export const FIELD_LABELS: Record<string, string> = {
  charge_number: 'Charge number',
  charging_party: 'Charging party',
  respondent: 'Respondent',
  eeoc_office: 'EEOC office',
  bases: 'Bases',
  issues: 'Issues',
  earliest_date: 'Earliest date',
  latest_date: 'Latest date',
  continuing_action: 'Continuing action',
  notice_date: 'Notice date',
  summary: 'Summary',
};

export const TAG_LABELS: Record<string, string> = {
  clean: 'Clean',
  missing_number: 'Missing charge number',
  rotated: 'Rotated page',
  long: 'Long particulars',
  two_respondents: 'Two respondents',
};

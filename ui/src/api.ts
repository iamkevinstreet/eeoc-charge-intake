import type { Decision, Export, Health, Review, RunResult, Sample } from './types';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* no JSON body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>('/health'),
  samples: () => request<Sample[]>('/samples'),
  extractSample: (id: string) => request<Review>(`/extract/sample/${id}`, { method: 'POST' }),
  extractUpload: (charge: File, notice: File) => {
    const form = new FormData();
    form.append('charge', charge);
    form.append('notice', notice);
    return request<Review>('/extract', { method: 'POST', body: form });
  },
  review: (id: string) => request<Review>(`/reviews/${id}`),
  decide: (id: string, decision: Decision) =>
    request<{ decided: number; total: number }>(`/reviews/${id}/decisions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(decision),
    }),
  exportReview: (id: string) => request<Export>(`/reviews/${id}/export`),
  latestEval: () => request<RunResult>('/evals/latest'),
};

import type { CaseResult, RunResult } from '../types';
import { FIELD_LABELS, TAG_LABELS } from '../types';

interface Props {
  run: RunResult | null;
  error: string | null;
}

const SCORED = Object.keys(FIELD_LABELS).filter((f) => f !== 'summary');

function mean(xs: number[]): number {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0;
}

function fieldAccuracy(results: CaseResult[], field: string): number {
  const ok = results.filter((r) => r.ok);
  return mean(ok.map((r) => Number(r.scores[`f_${field}`] ?? 0)));
}

function pct(x: number): string {
  const v = x * 100;
  return `${v > 0 && v < 10 ? v.toFixed(1) : Math.round(v)}%`;
}

export function Results({ run, error }: Props) {
  if (error) {
    return (
      <div className="results">
        <h1>Evaluation</h1>
        <p className="meta">
          No results yet. Run <code>make smoke</code> for the offline check or the live evaluation workflow for a
          real model, then reload.
        </p>
      </div>
    );
  }
  if (!run) return null;

  const tags = Array.from(new Set(run.results.flatMap((r) => r.tags))).sort();
  const s = run.summary;

  return (
    <div className="results">
      <h1>Evaluation</h1>
      <p className="meta">
        {run.name}, model {run.model} ({run.provider}), {run.cases} cases, {run.failures} failures, run{' '}
        {run.started_at.slice(0, 16).replace('T', ' ')} UTC.
        {run.provider === 'fake' && ' This is the offline smoke run: answers come from ground truth, so it checks the pipeline, not a model.'}
      </p>

      <div className="stats">
        <Stat label="Field accuracy" value={pct(s.field_accuracy ?? 0)} />
        <Stat label="Unsupported outputs removed" value={pct(s.unsupported_rate ?? 0)} note="share of filled fields whose quoted text was not on the cited page" />
        <Stat label="False abstentions per case" value={(s.false_abstentions ?? 0).toFixed(2)} />
        <Stat label="Guesses per case" value={(s.guesses ?? 0).toFixed(2)} />
        <Stat label="Latency p50 / p95" value={`${s.latency_p50_ms ?? 0} / ${s.latency_p95_ms ?? 0} ms`} />
        <Stat label="Cost per case" value={`$${(s.cost_per_case_usd ?? 0).toFixed(4)}`} note={`prices as of ${run.prices_as_of}`} />
      </div>

      <h2>Accuracy by field</h2>
      <svg className="bars" viewBox={`0 0 600 ${SCORED.length * 26 + 8}`} role="img" aria-label="Accuracy by field">
        {SCORED.map((f, i) => {
          const v = fieldAccuracy(run.results, f);
          const y = i * 26 + 4;
          return (
            <g key={f} transform={`translate(0 ${y})`}>
              <text x="0" y="14" className="bar-label">
                {FIELD_LABELS[f]}
              </text>
              <rect x="170" y="4" width="340" height="14" className="bar-track" />
              <rect x="170" y="4" width={340 * v} height="14" className="bar-fill" />
              <text x="520" y="15" className="bar-value">
                {pct(v)}
              </text>
            </g>
          );
        })}
      </svg>

      <h2>By case kind</h2>
      <table className="ledger">
        <thead>
          <tr>
            <th>Case kind</th>
            <th>Cases</th>
            <th>Field accuracy</th>
            <th>Unsupported removed</th>
            <th>False abstentions</th>
            <th>Guesses</th>
          </tr>
        </thead>
        <tbody>
          {tags.map((t) => {
            const rs = run.results.filter((r) => r.tags.includes(t) && r.ok);
            return (
              <tr key={t}>
                <td>{TAG_LABELS[t] ?? t}</td>
                <td>{rs.length}</td>
                <td>{pct(mean(rs.map((r) => Number(r.scores.field_accuracy ?? 0))))}</td>
                <td>{mean(rs.map((r) => Number(r.scores.unsupported_removed ?? 0))).toFixed(2)}</td>
                <td>{mean(rs.map((r) => Number(r.scores.false_abstentions ?? 0))).toFixed(2)}</td>
                <td>{mean(rs.map((r) => Number(r.scores.guesses ?? 0))).toFixed(2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {note && <div className="meta">{note}</div>}
    </div>
  );
}

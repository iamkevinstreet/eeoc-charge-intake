import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { formatValue, locate, parseValue } from '../highlight';
import type { Action, Export, Review as ReviewT, Sourced, Value } from '../types';
import { FIELD_LABELS } from '../types';
import { Document } from './Document';

interface Props {
  review: ReviewT;
  onChange: (update: (r: ReviewT) => ReviewT) => void;
  onBack: () => void;
}

export function Review({ review, onChange, onBack }: Props) {
  const fields = review.fields;
  const [selected, setSelected] = useState(0);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [doc, setDoc] = useState<'charge' | 'notice'>('charge');
  const [exported, setExported] = useState<Export | null>(null);
  const [error, setError] = useState<string | null>(null);

  const field = fields[selected];
  const current: Sourced = review.record[field];
  const pages = doc === 'charge' ? review.pages.charge : review.pages.notice;

  // Selecting a field moves the document pane to the document it cites.
  useEffect(() => {
    setDoc(field === 'notice_date' ? 'notice' : 'charge');
  }, [field]);

  const found = useMemo(() => {
    if (!current.span || !current.page) return null;
    const p = (field === 'notice_date' ? review.pages.notice : review.pages.charge)[current.page - 1] ?? '';
    return locate(p, current.span) !== null;
  }, [current, field, review.pages]);

  const decide = useCallback(
    async (f: string, action: Action, value?: Value) => {
      setError(null);
      try {
        const progress = await api.decide(review.review_id, { field: f, action, value });
        // Functional update: two quick decisions must not overwrite each other.
        onChange((r) => ({
          ...r,
          decisions: { ...r.decisions, [f]: { field: f, action, value } },
          decided: progress.decided,
        }));
        setEditing(null);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [review.review_id, onChange],
  );

  const startEdit = useCallback(
    (f: string) => {
      const d = review.decisions[f];
      const base = d?.action === 'edit' ? d.value ?? null : review.record[f].value;
      setDraft(formatValue(base ?? null));
      setEditing(f);
      setSelected(fields.indexOf(f));
    },
    [review, fields],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (editing || exported) return;
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      if (e.key === 'j' || e.key === 'ArrowDown') setSelected((s) => Math.min(fields.length - 1, s + 1));
      else if (e.key === 'k' || e.key === 'ArrowUp') setSelected((s) => Math.max(0, s - 1));
      else if (e.key === 'a') void decide(field, 'accept');
      else if (e.key === 'r') void decide(field, 'reject');
      else if (e.key === 'e') startEdit(field);
      else return;
      e.preventDefault();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [editing, exported, fields.length, field, decide, startEdit]);

  async function doExport() {
    setError(null);
    try {
      setExported(await api.exportReview(review.review_id));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const complete = review.decided === review.total;

  return (
    <div className="review">
      <header className="review-head">
        <div>
          <button className="link" onClick={onBack}>
            All documents
          </button>
          <h1>{review.source.replace('sample:', '').replace('upload:', '')}</h1>
          <p className="meta">
            {review.demo ? 'Demo mode, answers from ground truth' : `Model ${review.model}`}
            {review.latency_ms ? `, ${(review.latency_ms / 1000).toFixed(1)} s` : ''}
            {review.cost_usd ? `, $${review.cost_usd.toFixed(4)}` : ''}
            {review.removed.length > 0 &&
              `. Verification emptied ${review.removed.length} ${review.removed.length === 1 ? 'field' : 'fields'} whose cited text was not on the cited page.`}
          </p>
        </div>
        <div className="progress" aria-live="polite">
          <div className="progress-bar" aria-hidden="true">
            <span style={{ width: `${(review.decided / review.total) * 100}%` }} />
          </div>
          <span>
            {review.decided} of {review.total} decided
          </span>
          <button className="btn primary" disabled={!complete} onClick={doExport} title={complete ? '' : 'Decide every field first'}>
            Export record
          </button>
        </div>
      </header>

      {error && <p className="error">{error}</p>}

      <div className="review-body">
        <ol className="fields" aria-label="Extracted fields">
          {fields.map((f, i) => {
            const s = review.record[f];
            const raw = review.raw[f];
            const d = review.decisions[f];
            const removed = review.removed.includes(f);
            const empty = s.value === null || s.value === '' || (Array.isArray(s.value) && s.value.length === 0);
            const shown = d?.action === 'edit' ? d.value ?? null : s.value;
            return (
              <li
                key={f}
                className={`field ${i === selected ? 'is-selected' : ''} ${d ? `is-${d.action}` : ''}`}
                onClick={() => setSelected(i)}
              >
                <div className="field-main">
                  <div className="field-name">
                    {FIELD_LABELS[f] ?? f}
                    {d && <span className={`chip chip-${d.action}`}>{d.action === 'edit' ? 'Edited' : d.action === 'accept' ? 'Accepted' : 'Rejected'}</span>}
                  </div>
                  {editing === f ? (
                    <form
                      className="edit"
                      onSubmit={(e) => {
                        e.preventDefault();
                        void decide(f, 'edit', parseValue(f, draft, s.value));
                      }}
                    >
                      {f === 'continuing_action' ? (
                        <select value={draft} onChange={(e) => setDraft(e.target.value)} autoFocus>
                          <option value="Yes">Yes</option>
                          <option value="No">No</option>
                        </select>
                      ) : (
                        <input
                          value={draft}
                          onChange={(e) => setDraft(e.target.value)}
                          autoFocus
                          placeholder={f === 'bases' || f === 'issues' ? 'Comma separated' : ''}
                        />
                      )}
                      <button className="btn primary" type="submit">
                        Save
                      </button>
                      <button className="btn" type="button" onClick={() => setEditing(null)}>
                        Cancel
                      </button>
                    </form>
                  ) : (
                    <div className={`field-value ${empty && d?.action !== 'edit' ? 'is-empty' : ''} ${d?.action === 'reject' ? 'is-struck' : ''}`}>
                      {d?.action === 'edit' || !empty ? formatValue(shown) : s.reason ?? 'Not found'}
                    </div>
                  )}
                  <div className="field-evidence">
                    {!empty && s.span && (
                      <>
                        <span className="meta">Page {s.page}: </span>
                        <q>{s.span}</q>
                      </>
                    )}
                    {!empty && !s.span && f === 'summary' && <span className="meta">Paraphrased from the particulars; no single span.</span>}
                    {!empty && !s.span && f === 'continuing_action' && s.value === false && (
                      <span className="meta">Box not marked on the form.</span>
                    )}
                    {removed && raw.value !== null && (
                      <span className="meta removed">
                        The model proposed <q>{formatValue(raw.value)}</q> citing page {raw.page}, but that text is not on page {raw.page}.
                        Left empty.
                      </span>
                    )}
                    {!empty && (
                      <span className="confidence" title="The model's own confidence">
                        <span className="confidence-bar" aria-hidden="true">
                          <span style={{ width: `${Math.round(s.confidence * 100)}%` }} />
                        </span>
                        {Math.round(s.confidence * 100)}%
                      </span>
                    )}
                  </div>
                </div>
                <div className="field-actions" role="group" aria-label={`Decide ${FIELD_LABELS[f] ?? f}`}>
                  <button className={`btn ${d?.action === 'accept' ? 'is-on' : ''}`} onClick={() => void decide(f, 'accept')}>
                    Accept
                  </button>
                  <button className={`btn ${d?.action === 'edit' ? 'is-on' : ''}`} onClick={() => startEdit(f)}>
                    Edit
                  </button>
                  <button className={`btn ${d?.action === 'reject' ? 'is-on' : ''}`} onClick={() => void decide(f, 'reject')}>
                    Reject
                  </button>
                </div>
              </li>
            );
          })}
        </ol>

        <Document doc={doc} pages={pages} page={current.page} span={current.span} onDoc={setDoc} found={found} />
      </div>

      <p className="meta keys">Keys: j and k move, a accepts, e edits, r rejects.</p>

      {exported && (
        <div className="sheet" role="dialog" aria-label="Exported record">
          <div className="sheet-head">
            <h2>Exported record</h2>
            <button className="btn" onClick={() => setExported(null)}>
              Close
            </button>
          </div>
          <p className="meta">
            Every field carries a decision. {exported.response_due ? `Position statement due ${exported.response_due} (notice date plus 30 days).` : ''}
          </p>
          <pre className="json">{JSON.stringify(exported, null, 2)}</pre>
          <div className="sheet-actions">
            <a
              className="btn primary"
              href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(exported, null, 2))}`}
              download={`${exported.review_id}.json`}
            >
              Download JSON
            </a>
            <button className="btn" onClick={() => void navigator.clipboard?.writeText(JSON.stringify(exported, null, 2))}>
              Copy
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

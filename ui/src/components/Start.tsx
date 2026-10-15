import { useState } from 'react';
import type { Health, Sample } from '../types';
import { TAG_LABELS } from '../types';

interface Props {
  health: Health | null;
  samples: Sample[];
  busy: string | null;
  error: string | null;
  onSample: (id: string) => void;
  onUpload: (charge: File, notice: File) => void;
}

export function Start({ health, samples, busy, error, onSample, onUpload }: Props) {
  const [charge, setCharge] = useState<File | null>(null);
  const [notice, setNotice] = useState<File | null>(null);
  const demo = health?.demo ?? true;

  return (
    <div className="start">
      <section className="start-intro">
        <h1>Review a charge</h1>
        <p>
          The service reads an EEOC charge form and its notice letter, fills eleven intake fields, and quotes the
          page and text behind each one. A field the documents do not support comes back empty with a reason.
          Nothing leaves this screen until a person has accepted, edited or rejected every field.
        </p>
        {health && (
          <p className="meta">
            {demo
              ? 'Demo mode: answers come from the ground truth of the generated documents, not from a model, so the review flow can be tried without an API key.'
              : `Model: ${health.model} (${health.provider}).`}
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="start-samples">
        <h2>Generated documents</h2>
        {samples.length === 0 ? (
          <p className="meta">
            No samples yet. Run <code>python -m eeoc_intake.generate --n 30</code> and reload.
          </p>
        ) : (
          <table className="ledger">
            <thead>
              <tr>
                <th>Document</th>
                <th>Case kind</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {samples.map((s) => (
                <tr key={s.id}>
                  <td>
                    <span className="serif">{s.charge_pdf}</span>
                    <span className="meta"> with {s.notice_pdf}</span>
                  </td>
                  <td>{s.tags.map((t) => TAG_LABELS[t] ?? t).join(', ')}</td>
                  <td className="right">
                    <button className="btn" disabled={busy !== null} onClick={() => onSample(s.id)}>
                      {busy === s.id ? 'Extracting' : 'Review'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="start-upload">
        <h2>Your own documents</h2>
        {demo ? (
          <p className="meta">
            Uploads need a model. Set <code>LLM_PROVIDER</code> and an API key in <code>.env</code>, restart the
            service, and this form turns on.
          </p>
        ) : (
          <form
            className="upload"
            onSubmit={(e) => {
              e.preventDefault();
              if (charge && notice) onUpload(charge, notice);
            }}
          >
            <label>
              Charge form (PDF)
              <input type="file" accept="application/pdf" onChange={(e) => setCharge(e.target.files?.[0] ?? null)} />
            </label>
            <label>
              Notice letter (PDF)
              <input type="file" accept="application/pdf" onChange={(e) => setNotice(e.target.files?.[0] ?? null)} />
            </label>
            <button className="btn primary" type="submit" disabled={!charge || !notice || busy !== null}>
              {busy === 'upload' ? 'Extracting' : 'Extract fields'}
            </button>
          </form>
        )}
      </section>
    </div>
  );
}

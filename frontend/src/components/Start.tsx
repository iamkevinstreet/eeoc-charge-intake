// ########################################################################
// #                  frontend/src/components/Start.tsx                   #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The start screen: what the service does, the     #
// #                     generated samples, and the upload form.          #
// ########################################################################
/** The start screen: what the service does, the generated samples, and the upload form. */

import { GENERATE_COMMAND } from '../config';
import { tagLabel } from '../format';
import type { Health, Sample } from '../types';
import { UploadForm } from './UploadForm';

interface Props {
  health: Health | null;
  samples: Sample[];
  /** What is being extracted: a sample id, the upload, or nothing. */
  busy: string | null;
  error: string | null;
  onSample: (id: string) => void;
  onUpload: (charge: File, notice: File) => void;
}

interface TableProps {
  samples: Sample[];
  busy: string | null;
  onSample: (id: string) => void;
}

// log.debug('Sets the class of the quieter notes')
const META = 'ec-meta';
// log.debug('Sets what joins the kinds of a sample')
const JOIN = ', ';
// log.debug('Sets the class of text only a screen reader reads')
const HIDDEN = 'ec-visually-hidden';

// log.debug('Defines the table of generated samples')
function SampleTable({ samples, busy, onSample }: TableProps) {
  // log.debug('Returns one row per sample, each with its review button')
  return (
    <table className="ec-ledger">
      <thead>
        <tr>
          <th scope="col">Document</th>
          <th scope="col">Case kind</th>
          <th scope="col">
            <span className={HIDDEN}>Review</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {samples.map((sample) => (
          <tr key={sample.id}>
            <td>
              <span className="ec-serif">{sample.charge_pdf}</span>
              <span className={META}> with {sample.notice_pdf}</span>
            </td>
            <td>{sample.tags.map((tag) => tagLabel(tag)).join(JOIN)}</td>
            <td className="ec-ledger__action">
              <button
                type="button"
                className="ec-button"
                disabled={busy !== null}
                onClick={() => onSample(sample.id)}
              >
                {busy === sample.id ? 'Extracting' : 'Review'}{' '}
                <span className={HIDDEN}>{sample.charge_pdf}</span>
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// log.debug('Defines the start screen')
export function Start({ health, samples, busy, error, onSample, onUpload }: Props) {
  // log.debug('Treats the service as offline until it says otherwise')
  const demo = health?.demo ?? true;
  // log.debug('Returns the screen')
  return (
    <div className="ec-start">
      <section>
        <h1>Review a charge</h1>
        <p>
          The service reads an EEOC charge form and its notice letter, fills eleven intake fields,
          and quotes the page and text behind each one. A field the documents do not support comes
          back empty with a reason. Nothing leaves this screen until a person has accepted, edited
          or rejected every field.
        </p>
        {health !== null && demo && (
          <p className={META}>
            Demo mode: answers come from the ground truth of the generated documents, not from a
            model, so the review flow can be tried without an API key.
          </p>
        )}
        {health !== null && !demo && (
          <p className={META}>
            Model: {health.model} ({health.provider}).
          </p>
        )}
        {error !== null && (
          <p className="ec-error" role="alert">
            {error}
          </p>
        )}
      </section>
      <section>
        <h2>Generated documents</h2>
        {samples.length === 0 ? (
          <p className={META}>
            No samples yet. Run <code>{GENERATE_COMMAND}</code> and reload.
          </p>
        ) : (
          <SampleTable samples={samples} busy={busy} onSample={onSample} />
        )}
      </section>
      <section>
        <h2>Your own documents</h2>
        {demo ? (
          <p className={META}>
            Uploads need a model. Set <code>LLM_PROVIDER</code> and an API key in <code>.env</code>
            , restart the service, and this form turns on.
          </p>
        ) : (
          <UploadForm busy={busy} onUpload={onUpload} />
        )}
      </section>
    </div>
  );
}

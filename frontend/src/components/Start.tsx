// ########################################################################
// #                  frontend/src/components/Start.tsx                   #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The start screen: what the service does, the generated samples, each
 * with a button to review it, and the upload form, which turns on once
 * the service calls a model.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from '../config';
import { tagLabel } from '../format';
import { required } from '../lib/required';
import type { Health, Sample } from '../types';
import { UploadForm } from './UploadForm';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the class of the quieter notes from the config')
const META = CONFIG.ui.note_class;
// log.debug('Takes what joins the kinds of a sample from the config')
const JOIN = CONFIG.labels.join;
// log.debug('Takes the command that generates sample documents from the config')
const GENERATE_COMMAND = CONFIG.ui.generate_command;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the class of text only a screen reader reads')
const HIDDEN = 'ec-visually-hidden';

// ########################################################################
// #                             Start screen                             #
// ########################################################################
interface Props {
  health?: Health | null;
  samples?: Sample[];
  /** What is being extracted: a sample id, the upload, or nothing. */
  busy?: string | null;
  error?: string | null;
  onSample?: ((id: string) => void) | null;
  onUpload?: ((charge: File, notice: File) => void) | null;
}

interface TableProps {
  samples?: Sample[];
  busy?: string | null;
  onSample?: ((id: string) => void) | null;
}

interface OwnProps {
  demo?: boolean;
  busy?: string | null;
  onUpload?: ((charge: File, notice: File) => void) | null;
}

// log.debug('Defines the table of generated samples')
/**
 * Renders the table of generated samples, each with its review button.
 *
 * @param props - The component's props.
 * @param props.samples - The samples, in the order to list them.
 * @param props.busy - What is being extracted: a sample id, the upload,
 *   or null for nothing; every button waits while anything is.
 * @param props.onSample - Starts the extraction of a sample, by its id.
 *   Required.
 * @returns The table, one row per sample.
 */
function SampleTable({
  samples = [],
  busy = null,
  onSample = null,
}: TableProps = {}): React.JSX.Element {
  // log.debug('Takes the sample handler, which the caller must give')
  onSample = required({ onSample });
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

// log.debug('Defines the section for documents of your own')
/**
 * Renders the section for documents of your own: the upload form once
 * the service calls a model, else what it takes to turn the form on.
 *
 * @param props - The component's props.
 * @param props.demo - Whether the service answers from the known
 *   answers instead of a model, which leaves uploads off.
 * @param props.busy - What is being extracted: a sample id, the upload,
 *   or null for nothing.
 * @param props.onUpload - Starts the extraction of an upload. Required.
 * @returns The section.
 */
function OwnDocuments({
  demo = true,
  busy = null,
  onUpload = null,
}: OwnProps = {}): React.JSX.Element {
  // log.debug('Takes the upload handler, which the caller must give')
  onUpload = required({ onUpload });
  // log.debug('Returns the heading, then the form or what turns it on')
  return (
    <section>
      <h2>Your own documents</h2>
      {demo ? (
        <p className={META}>
          Uploads need a model. Set <code>[llm] provider</code> in <code>config/config.toml</code>{' '}
          and its API key in <code>config/.env</code>, restart the service, and this form turns on.
        </p>
      ) : (
        <UploadForm busy={busy} onUpload={onUpload} />
      )}
    </section>
  );
}

// log.debug('Defines the start screen')
/**
 * Renders the start screen: what the service does, the samples and the
 * upload form.
 *
 * @param props - The component's props.
 * @param props.health - The service's health report; null until it
 *   answers, which counts as demo mode.
 * @param props.samples - The generated samples; none shows how to make
 *   them.
 * @param props.busy - What is being extracted: a sample id, the upload,
 *   or null for nothing.
 * @param props.error - A problem to show, or null for none.
 * @param props.onSample - Starts the extraction of a sample, by its id.
 *   Required.
 * @param props.onUpload - Starts the extraction of an upload. Required.
 * @returns The screen.
 */
export function Start({
  health = null,
  samples = [],
  busy = null,
  error = null,
  onSample = null,
  onUpload = null,
}: Props = {}): React.JSX.Element {
  // log.debug('Takes the sample handler, which the caller must give')
  onSample = required({ onSample });
  // log.debug('Takes the upload handler, which the caller must give')
  onUpload = required({ onUpload });
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
      <OwnDocuments demo={demo} busy={busy} onUpload={onUpload} />
    </div>
  );
}

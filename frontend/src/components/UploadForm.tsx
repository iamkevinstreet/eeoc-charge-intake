// ########################################################################
// #                frontend/src/components/UploadForm.tsx                #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The upload form: a charge form and its notice letter, both PDFs, and
 * the button that extracts their fields once both are picked.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { useState } from 'react';

// Local
import { CONFIG } from '../config';
import { required } from '../lib/required';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes what an upload is called while it is extracted from the config')
const UPLOAD = CONFIG.ui.upload_key;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the only kind of file the form takes')
const PDF = 'application/pdf';

// ########################################################################
// #                             Upload form                              #
// ########################################################################
interface Props {
  /** What is being extracted: a sample id, the upload, or nothing. */
  busy?: string | null;
  onUpload?: ((charge: File, notice: File) => void) | null;
}

interface PickerProps {
  label?: string | null;
  onPick?: ((file: File | null) => void) | null;
}

// log.debug('Defines one file picker that takes a PDF')
/**
 * Renders one labelled file picker that takes a PDF.
 *
 * @param props - The component's props.
 * @param props.label - What the picker asks for. Required.
 * @param props.onPick - Takes the file picked, or null when none is.
 *   Required.
 * @returns The labelled picker.
 */
function PdfPicker({ label = null, onPick = null }: PickerProps = {}): React.JSX.Element {
  // log.debug('Takes the label, which the caller must give')
  label = required({ label });
  // log.debug('Takes the pick handler, which the caller must give')
  onPick = required({ onPick });
  // log.debug('Returns the labelled picker, handing up the first file chosen')
  return (
    <label className="ec-upload__label">
      {label}
      <input
        type="file"
        accept={PDF}
        onChange={(event) => onPick(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}

// log.debug('Defines the upload form')
/**
 * Renders the upload form: a picker for each document and the button
 * that extracts their fields.
 *
 * @param props - The component's props.
 * @param props.busy - What is being extracted: a sample id, the upload,
 *   or null for nothing; the button waits while anything is.
 * @param props.onUpload - Starts the extraction of the two files.
 *   Required.
 * @returns The form.
 */
export function UploadForm({ busy = null, onUpload = null }: Props = {}): React.JSX.Element {
  // log.debug('Takes the upload handler, which the caller must give')
  onUpload = required({ onUpload });
  // log.debug('Keeps the charge form picked')
  const [charge, setCharge] = useState<File | null>(null);
  // log.debug('Keeps the notice letter picked')
  const [notice, setNotice] = useState<File | null>(null);
  // log.debug('Allows an upload only with both files and nothing else running')
  const ready = charge !== null && notice !== null && busy === null;

  // log.debug('Defines the submit handler')
  /**
   * Hands both files up for extraction, instead of reloading the page.
   *
   * @param event - The form's submit event. Required.
   */
  const submit = (event: React.SubmitEvent<HTMLFormElement> | null = null): void => {
    // log.debug('Takes the event, which the caller must give')
    event = required({ event });
    // log.debug('Stops the page reloading')
    event.preventDefault();
    // log.debug('Hands both files up once both are picked')
    if (charge !== null && notice !== null) {
      // log.debug('Starts the extraction')
      onUpload(charge, notice);
    }
  };

  // log.debug('Returns the form')
  return (
    <form className="ec-upload" onSubmit={submit}>
      <PdfPicker label="Charge form (PDF)" onPick={setCharge} />
      <PdfPicker label="Notice letter (PDF)" onPick={setNotice} />
      <button className="ec-button ec-button--primary" type="submit" disabled={!ready}>
        {busy === UPLOAD ? 'Extracting' : 'Extract fields'}
      </button>
    </form>
  );
}

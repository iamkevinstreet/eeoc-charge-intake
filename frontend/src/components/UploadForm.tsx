// ########################################################################
// #                frontend/src/components/UploadForm.tsx                #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The upload form: a charge form and its notice    #
// #                     letter, both PDFs.                               #
// ########################################################################
/** The upload form: a charge form and its notice letter, both PDFs. */

import { useState } from 'react';

interface Props {
  /** What is being extracted: a sample id, the upload, or nothing. */
  busy: string | null;
  onUpload: (charge: File, notice: File) => void;
}

interface PickerProps {
  label: string;
  onPick: (file: File | null) => void;
}

// log.debug('Names the busy state of an upload, beside the sample ids')
export const UPLOAD = 'upload';
// log.debug('Sets the only kind of file the form takes')
const PDF = 'application/pdf';

// log.debug('Defines one file picker that takes a PDF')
function PdfPicker({ label, onPick }: PickerProps) {
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
export function UploadForm({ busy, onUpload }: Props) {
  // log.debug('Keeps the charge form picked')
  const [charge, setCharge] = useState<File | null>(null);
  // log.debug('Keeps the notice letter picked')
  const [notice, setNotice] = useState<File | null>(null);
  // log.debug('Allows an upload only with both files and nothing else running')
  const ready = charge !== null && notice !== null && busy === null;

  // log.debug('Defines the submit handler')
  const submit = (event: React.SubmitEvent<HTMLFormElement>): void => {
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

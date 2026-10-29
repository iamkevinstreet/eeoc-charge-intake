// ########################################################################
// #               frontend/src/components/ExportSheet.tsx                #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The exported record: every decided field as      #
// #                     JSON, to download or copy.                       #
// ########################################################################
/** The exported record: every decided field as JSON, to download or copy. */

import type { Export } from '../types';

interface Props {
  exported: Export;
  onClose: () => void;
}

// log.debug('Sets the spaces each level of the JSON is indented by')
const INDENT = 2;
// log.debug('Sets the start of a link that downloads JSON')
const JSON_LINK = 'data:application/json;charset=utf-8,';
// log.debug('Sets the class of a plain button')
const BUTTON = 'ec-button';

// log.debug('Defines the sheet that shows the exported record')
export function ExportSheet({ exported, onClose }: Props) {
  // log.debug('Writes the record as indented JSON')
  const json = JSON.stringify(exported, null, INDENT);

  // log.debug('Defines the copy button handler')
  const copy = (): void => {
    // log.debug('Copies the JSON when the browser offers a clipboard on this page')
    if ('clipboard' in navigator) {
      // log.debug('Writes the JSON, ignoring a browser that refuses')
      navigator.clipboard.writeText(json).catch(() => undefined);
    }
  };

  // log.debug('Returns the sheet: the due date, the JSON, and the download and copy buttons')
  return (
    <div className="ec-sheet" role="dialog" aria-label="Exported record">
      <div className="ec-sheet__head">
        <h2>Exported record</h2>
        <button type="button" className={BUTTON} onClick={onClose}>
          Close
        </button>
      </div>
      <p className="ec-meta">
        Every field carries a decision.
        {exported.response_due !== null &&
          ` Position statement due ${exported.response_due} (notice date plus 30 days).`}
      </p>
      <pre className="ec-sheet__json">{json}</pre>
      <div className="ec-sheet__actions">
        <a
          className="ec-button ec-button--primary"
          href={`${JSON_LINK}${encodeURIComponent(json)}`}
          download={`${exported.review_id}.json`}
        >
          Download JSON
        </a>
        <button type="button" className={BUTTON} onClick={copy}>
          Copy
        </button>
      </div>
    </div>
  );
}

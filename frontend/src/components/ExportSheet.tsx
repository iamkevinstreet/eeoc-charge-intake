// ########################################################################
// #               frontend/src/components/ExportSheet.tsx                #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The exported record: every decided field as JSON, with the day the
 * position statement is due, to download or copy.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from '../config';
import { required } from '../lib/required';
import type { Export } from '../types';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the days after the notice a response is due from the config')
const RESPONSE_DAYS = CONFIG.extract.response_days;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the spaces each level of the JSON is indented by')
const INDENT = 2;
// log.debug('Sets the start of a link that downloads JSON')
const JSON_LINK = 'data:application/json;charset=utf-8,';
// log.debug('Sets the class of a plain button')
const BUTTON = 'ec-button';

// ########################################################################
// #                             Export sheet                             #
// ########################################################################
interface Props {
  exported?: Export | null;
  onClose?: (() => void) | null;
}

// log.debug('Defines the sheet that shows the exported record')
/**
 * Renders the exported record, with buttons to download or copy it.
 *
 * @param props - The component's props.
 * @param props.exported - The exported record. Required.
 * @param props.onClose - Closes the sheet. Required.
 * @returns The sheet: the due date, the JSON, and the download and copy
 *   buttons.
 */
export function ExportSheet({ exported = null, onClose = null }: Props = {}): React.JSX.Element {
  // log.debug('Takes the exported record, which the caller must give')
  exported = required({ exported });
  // log.debug('Takes the close handler, which the caller must give')
  onClose = required({ onClose });
  // log.debug('Writes the record as indented JSON')
  const json = JSON.stringify(exported, null, INDENT);
  // log.debug('Says how the due date is counted: the notice date plus the days allowed')
  const counted = `notice date plus ${RESPONSE_DAYS} days`;

  // log.debug('Defines the copy button handler')
  /** Copies the JSON, when the browser offers a clipboard on this page. */
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
          ` Position statement due ${exported.response_due} (${counted}).`}
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

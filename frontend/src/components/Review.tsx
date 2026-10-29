// ########################################################################
// #                  frontend/src/components/Review.tsx                  #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The review screen: the record beside the document, one decision per
 * field, and the export once every field has one. The state it keeps
 * and the keys it listens for come from the review hooks.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { api as liveApi } from '../api';
import { CONFIG } from '../config';
import { required } from '../lib/required';
import { exportRecord, useDecisions, useReviewKeys, useSelection } from '../reviewing';
import type { ReviewApi } from '../reviewing';
import type { Review as ReviewData } from '../types';
import { Document } from './Document';
import { ExportSheet } from './ExportSheet';
import { FieldList } from './FieldList';
import { ReviewHead } from './ReviewHead';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the keys that move through the fields and decide them from the config')
const KEYS = CONFIG.ui.keys;

// ########################################################################
// #                            Review screen                             #
// ########################################################################
interface Props {
  review?: ReviewData | null;
  /** Applies a change to the latest review, so two quick decisions both count. */
  onChange?: ((update: (current: ReviewData) => ReviewData) => void) | null;
  onBack?: (() => void) | null;
  api?: ReviewApi;
  backLabel?: string;
}

// log.debug('Defines the review screen')
/**
 * Renders the review screen: the head, the fields beside the document,
 * the keys, and the exported record once there is one.
 *
 * @param props - The component's props.
 * @param props.review - The review to work on. Required.
 * @param props.onChange - Applies a change to the latest review.
 *   Required.
 * @param props.onBack - Goes back to the list of documents. Required.
 * @param props.api - The calls that send a decision and fetch the
 *   export; the live service unless a demo supplies its own.
 * @param props.backLabel - What the way back is called.
 * @returns The screen.
 */
export function Review({
  review = null,
  onChange = null,
  onBack = null,
  api = liveApi,
  backLabel = 'All documents',
}: Props = {}): React.JSX.Element {
  // log.debug('Takes the review, which the caller must give')
  review = required({ review });
  // log.debug('Takes the change handler, which the caller must give')
  onChange = required({ onChange });
  // log.debug('Takes the back handler, which the caller must give')
  onBack = required({ onBack });
  // log.debug('Keeps the selected field and the document on show')
  const selection = useSelection(review);
  // log.debug('Keeps the decisions in progress: the edit, the export and any problem')
  const work = useDecisions(review, onChange, api, selection.select);
  // log.debug('Moves through the fields and decides them from the keyboard')
  useReviewKeys(selection, work);
  // log.debug('Takes the selected field and whether the document on show is the one it cites')
  const { current, citing } = selection;

  // log.debug('Returns the screen')
  return (
    <div className="ec-review">
      <ReviewHead
        review={review}
        backLabel={backLabel}
        onBack={onBack}
        onExport={() => exportRecord(work)}
      />
      {work.problem !== null && (
        <p className="ec-error" role="alert">
          {work.problem}
        </p>
      )}
      <div className="ec-review__body">
        <FieldList selection={selection} work={work} />
        <Document
          doc={selection.doc}
          pages={review.pages[selection.doc]}
          page={citing ? current.page : null}
          quote={citing ? current.span : null}
          onDoc={selection.pick}
        />
      </div>
      <p className="ec-meta ec-review__keys">
        Keys: {KEYS.next} and {KEYS.previous} move, {KEYS.accept} accepts, {KEYS.edit} edits,{' '}
        {KEYS.reject} rejects.
      </p>
      {work.exported !== null && (
        <ExportSheet exported={work.exported} onClose={() => work.setExported(null)} />
      )}
    </div>
  );
}

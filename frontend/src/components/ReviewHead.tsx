// ########################################################################
// #                frontend/src/components/ReviewHead.tsx                #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The head of the review screen: the way back, the document's name, who
 * answered and at what cost, how many fields have a decision, and the
 * export, which waits until every field has one.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { money, percent, seconds } from '../format';
import { required } from '../lib/required';
import type { Review } from '../types';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Matches the prefix that says where a document came from')
const SOURCE = /^(?:sample|upload):/;

// ########################################################################
// #                             Review head                              #
// ########################################################################
interface Props {
  review?: Review | null;
  backLabel?: string | null;
  onBack?: (() => void) | null;
  onExport?: (() => void) | null;
}

// log.debug('Defines the line under the title: who answered, how long it took, what it cost')
/**
 * Returns the line under the title: who answered, how long it took and
 * what it cost.
 *
 * @param review - The review on screen. Required.
 * @returns The model, or demo mode; the seconds and the cost when there
 *   were any; and how many fields verification emptied, if any.
 */
function summary(review: Review | null = null): string {
  // log.debug('Takes the review, which the caller must give')
  review = required({ review });
  // log.debug('Starts with the model, or says the answers are the known ones')
  const parts = [review.demo ? 'Demo mode, answers from ground truth' : `Model ${review.model}`];
  // log.debug('Adds the time the extraction took, when it was measured')
  if (review.latency_ms > 0) {
    // log.debug('Adds the seconds')
    parts.push(seconds(review.latency_ms));
  }
  // log.debug('Adds the cost, when there was one')
  if (review.cost_usd > 0) {
    // log.debug('Adds the dollars')
    parts.push(money(review.cost_usd));
  }
  // log.debug('Joins the parts')
  const line = parts.join(', ');
  // log.debug('Counts the fields verification emptied')
  const removed = review.removed.length;
  // log.debug('Returns the line alone when verification emptied nothing')
  if (removed === 0) {
    // log.debug('Returns the line')
    return line;
  }
  // log.debug('Says how many fields verification emptied, in the singular or plural')
  const emptied = `Verification emptied ${removed} ${removed === 1 ? 'field' : 'fields'}`;
  // log.debug('Returns the line and the emptied fields')
  return `${line}. ${emptied} whose cited text was not on the cited page.`;
}

// log.debug('Defines the head of the review screen')
/**
 * Renders the head of the review screen: the way back, the title and
 * its summary line, the progress bar and the export button.
 *
 * @param props - The component's props.
 * @param props.review - The review on screen. Required.
 * @param props.backLabel - What the way back is called. Required.
 * @param props.onBack - Goes back. Required.
 * @param props.onExport - Fetches the exported record. Required.
 * @returns The head.
 */
export function ReviewHead({
  review = null,
  backLabel = null,
  onBack = null,
  onExport = null,
}: Props = {}): React.JSX.Element {
  // log.debug('Takes the review, which the caller must give')
  review = required({ review });
  // log.debug('Takes the label of the way back, which the caller must give')
  backLabel = required({ backLabel });
  // log.debug('Takes the back handler, which the caller must give')
  onBack = required({ onBack });
  // log.debug('Takes the export handler, which the caller must give')
  onExport = required({ onExport });
  // log.debug('Notes whether every field has a decision')
  const complete = review.decided === review.total;
  // log.debug('Takes the share of fields decided, for the progress bar')
  const progress = percent(review.total === 0 ? 0 : review.decided / review.total);
  // log.debug('Returns the head')
  return (
    <header className="ec-review__head">
      <div>
        <button type="button" className="ec-link" onClick={onBack}>
          {backLabel}
        </button>
        <h1 className="ec-review__title">{review.source.replace(SOURCE, '')}</h1>
        <p className="ec-meta ec-review__summary">{summary(review)}</p>
      </div>
      <div className="ec-progress" aria-live="polite">
        <div className="ec-progress__bar" aria-hidden="true">
          <span className="ec-progress__fill" style={{ width: `${progress}%` }} />
        </div>
        <span>
          {review.decided} of {review.total} decided
        </span>
        <button
          type="button"
          className="ec-button ec-button--primary"
          disabled={!complete}
          title={complete ? undefined : 'Decide every field first'}
          onClick={onExport}
        >
          Export record
        </button>
      </div>
    </header>
  );
}

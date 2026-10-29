// ########################################################################
// #                  frontend/src/components/Review.tsx                  #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The review screen: the record beside the         #
// #                     document, one decision per field, export when    #
// #                     done.                                            #
// ########################################################################
/** The review screen: the record beside the document, one decision per field, export when done. */

import { useEffect, useEffectEvent, useState } from 'react';

import { api as liveApi, describeError } from '../api';
import { KEYS, NOTICE_FIELD } from '../config';
import { money, percent, seconds } from '../format';
import type { Action, Decision, DocKind, Export, Progress, Review as ReviewData } from '../types';
import { fieldOf, formatValue, parseValue } from '../values';
import { Document } from './Document';
import { ExportSheet } from './ExportSheet';
import { FieldRow } from './FieldRow';

/** The two calls the screen makes while a person reviews; a demo can supply its own. */
export interface ReviewApi {
  decide: (id: string, decision: Decision) => Promise<Progress>;
  exportReview: (id: string) => Promise<Export>;
}

interface Props {
  review: ReviewData;
  /** Applies a change to the latest review, so two quick decisions both count. */
  onChange: (update: (current: ReviewData) => ReviewData) => void;
  onBack: () => void;
  api?: ReviewApi;
  backLabel?: string;
}

/** The document a reviewer picked, and the field it was picked for. */
interface Picked {
  field: string;
  doc: DocKind;
}

// log.debug('Names the decision that opens the edit form instead of deciding at once')
const EDIT: Action = 'edit';
// log.debug('Names the event that carries key presses')
const KEYDOWN = 'keydown';
// log.debug('Lists the keys that move the selection, with the step each takes')
const MOVES: Readonly<Record<string, number>> = {
  [KEYS.next]: 1,
  ArrowDown: 1,
  [KEYS.previous]: -1,
  ArrowUp: -1,
};
// log.debug('Lists the keys that decide the selected field')
const DECIDES: Readonly<Record<string, Action>> = {
  [KEYS.accept]: 'accept',
  [KEYS.edit]: EDIT,
  [KEYS.reject]: 'reject',
};
// log.debug('Matches the controls where a key types instead of deciding')
const TYPING = 'input, textarea, select';
// log.debug('Matches the prefix that says where a document came from')
const SOURCE = /^(?:sample|upload):/;

// log.debug('Defines which document a field cites')
function citedIn(name: string): DocKind {
  // log.debug('Returns the notice for the notice date, the charge for the rest')
  return name === NOTICE_FIELD ? 'notice' : 'charge';
}

// log.debug('Defines the line under the title: who answered, how long it took, what it cost')
function summary(review: ReviewData): string {
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

// log.debug('Defines the review screen')
export function Review({
  review,
  onChange,
  onBack,
  api = liveApi,
  backLabel = 'All documents',
}: Props) {
  // log.debug('Keeps the place of the selected field')
  const [selected, setSelected] = useState(0);
  // log.debug('Keeps the field being edited, if any')
  const [editing, setEditing] = useState<string | null>(null);
  // log.debug('Keeps the text of the edit')
  const [draft, setDraft] = useState('');
  // log.debug('Keeps the document the reviewer picked, and for which field')
  const [picked, setPicked] = useState<Picked | null>(null);
  // log.debug('Keeps the exported record, once there is one')
  const [exported, setExported] = useState<Export | null>(null);
  // log.debug('Keeps a problem to show')
  const [problem, setProblem] = useState<string | null>(null);

  // log.debug('Takes the fields in the order the record shows them')
  const { fields } = review;
  // log.debug('Takes the name of the selected field')
  const field = fields[selected] ?? '';
  // log.debug('Takes the selected field as extracted')
  const current = fieldOf(review.record, field);
  // log.debug('Finds the document the selected field cites')
  const cited = citedIn(field);
  // log.debug('Shows the document picked for this field, else the one it cites')
  const doc = picked?.field === field ? picked.doc : cited;
  // log.debug('Notes whether the document on show is the one the field cites')
  const citing = doc === cited;
  // log.debug('Notes whether every field has a decision')
  const complete = review.decided === review.total;
  // log.debug('Takes the share of fields decided, for the progress bar')
  const progress = percent(review.total === 0 ? 0 : review.decided / review.total);

  // log.debug('Defines how a decision is sent and recorded')
  const record = (decision: Decision): void => {
    // log.debug('Clears any problem')
    setProblem(null);
    // log.debug('Sends the decision, then records it with the progress the service reports')
    api
      .decide(review.review_id, decision)
      .then((done) => {
        // log.debug('Records the decision on the latest review, so quick decisions all count')
        onChange((latest) => ({
          ...latest,
          decisions: { ...latest.decisions, [decision.field]: decision },
          decided: done.decided,
        }));
        // log.debug('Closes any edit form')
        setEditing(null);
      })
      .catch((error: unknown) => setProblem(describeError(error)));
  };

  // log.debug('Defines how editing a field starts')
  const startEdit = (name: string): void => {
    // log.debug('Takes the decision already made on the field, if any')
    const earlier = review.decisions[name];
    // log.debug('Starts from the edited value, else the extracted one')
    const base =
      earlier?.action === EDIT ? (earlier.value ?? null) : fieldOf(review.record, name).value;
    // log.debug('Puts the value in the edit box')
    setDraft(formatValue(base));
    // log.debug('Opens the edit form on the field')
    setEditing(name);
    // log.debug('Selects the field')
    setSelected(fields.indexOf(name));
  };

  // log.debug('Defines what a decision button or key does to a field')
  const act = (name: string, action: Action): void => {
    // log.debug('Opens the edit form for an edit')
    if (action === EDIT) {
      // log.debug('Starts editing')
      startEdit(name);
      // log.debug('Leaves the handler')
      return;
    }
    // log.debug('Records an accept or a reject at once')
    record({ field: name, action });
  };

  // log.debug('Defines how an edit is saved')
  const save = (name: string): void => {
    // log.debug('Reads the typed text back into the shape of the field')
    const value = parseValue(name, draft, fieldOf(review.record, name).value);
    // log.debug('Records the edit with its new value')
    record({ field: name, action: EDIT, value });
  };

  // log.debug('Defines the export')
  const exportRecord = (): void => {
    // log.debug('Clears any problem')
    setProblem(null);
    // log.debug('Fetches the exported record, or says why it could not')
    api
      .exportReview(review.review_id)
      .then(setExported)
      .catch((error: unknown) => setProblem(describeError(error)));
  };

  // log.debug('Defines what a key press does, with the latest state')
  const onKey = useEffectEvent((event: KeyboardEvent) => {
    // log.debug('Ignores keys while editing, while the export shows, and with modifiers')
    if (editing !== null || exported !== null || event.ctrlKey || event.metaKey || event.altKey) {
      // log.debug('Leaves the key alone')
      return;
    }
    // log.debug('Ignores keys typed into a form control')
    if (event.target instanceof Element && event.target.closest(TYPING) !== null) {
      // log.debug('Leaves the key alone')
      return;
    }
    // log.debug('Looks up the step the key moves by, if any')
    const step = MOVES[event.key];
    // log.debug('Looks up the decision the key makes, if any')
    const action = DECIDES[event.key];
    // log.debug('Moves the selection, staying within the fields')
    if (step !== undefined) {
      // log.debug('Selects the next or previous field')
      setSelected((index) => Math.min(fields.length - 1, Math.max(0, index + step)));
    } else if (action !== undefined) {
      // log.debug('Decides the selected field')
      act(field, action);
    } else {
      // log.debug('Leaves any other key alone')
      return;
    }
    // log.debug('Stops the browser acting on the key too')
    event.preventDefault();
  });

  // log.debug('Listens for keys while the screen is open')
  useEffect(() => {
    // log.debug('Defines the listener, which hands each key to the handler')
    const listen = (event: KeyboardEvent): void => onKey(event);
    // log.debug('Starts listening')
    window.addEventListener(KEYDOWN, listen);
    // log.debug('Stops listening when the screen closes')
    return () => window.removeEventListener(KEYDOWN, listen);
  }, []);

  // log.debug('Returns the screen')
  return (
    <div className="ec-review">
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
            onClick={exportRecord}
          >
            Export record
          </button>
        </div>
      </header>
      {problem !== null && (
        <p className="ec-error" role="alert">
          {problem}
        </p>
      )}
      <div className="ec-review__body">
        <ol className="ec-fields" aria-label="Extracted fields">
          {fields.map((name, index) => (
            <FieldRow
              key={name}
              name={name}
              sourced={fieldOf(review.record, name)}
              raw={fieldOf(review.raw, name)}
              decision={review.decisions[name]}
              removed={review.removed.includes(name)}
              selected={index === selected}
              draft={editing === name ? draft : null}
              onSelect={() => setSelected(index)}
              onAction={(action) => act(name, action)}
              onDraft={setDraft}
              onSave={() => save(name)}
              onCancel={() => setEditing(null)}
            />
          ))}
        </ol>
        <Document
          doc={doc}
          pages={review.pages[doc]}
          page={citing ? current.page : null}
          quote={citing ? current.span : null}
          onDoc={(next) => setPicked({ field, doc: next })}
        />
      </div>
      <p className="ec-meta ec-review__keys">
        Keys: {KEYS.next} and {KEYS.previous} move, {KEYS.accept} accepts, {KEYS.edit} edits,{' '}
        {KEYS.reject} rejects.
      </p>
      {exported !== null && <ExportSheet exported={exported} onClose={() => setExported(null)} />}
    </div>
  );
}

// ########################################################################
// #                      frontend/src/reviewing.ts                       #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The review screen's state and what changes it: the field selected and
 * the document on show, the decisions sent as a reviewer accepts, edits
 * or rejects each field, the export once every field has one, and the
 * keys that move through the fields and decide them.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { useEffect, useEffectEvent, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

// Local
import { describeError } from './api';
import { CONFIG } from './config';
import { required } from './lib/required';
import type { Action, Decision, DocKind, Export, Progress, Review, Sourced } from './types';
import { fieldOf, formatValue, parseValue } from './values';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the one field read from the notice letter from the config')
const NOTICE_FIELD = CONFIG.record.notice_field;
// log.debug('Takes the keys that move through the fields and decide them from the config')
const KEYS = CONFIG.ui.keys;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
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

// ########################################################################
// #                             Review state                             #
// ########################################################################
/** The two calls the screen makes while a person reviews; a demo can supply its own. */
export interface ReviewApi {
  decide: (id: string, decision: Decision) => Promise<Progress>;
  exportReview: (id: string) => Promise<Export>;
}

/** The document a reviewer picked, and the field it was picked for. */
interface Picked {
  field: string;
  doc: DocKind;
}

/** The field selected, and the document on show beside it. */
export interface Selection {
  /** The place of the selected field in the record. */
  selected: number;
  select: Dispatch<SetStateAction<number>>;
  /** The selected field's name. */
  field: string;
  /** The selected field as extracted. */
  current: Sourced;
  doc: DocKind;
  /** Whether the document on show is the one the selected field cites. */
  citing: boolean;
  pick: (doc: DocKind) => void;
}

/** The review's decisions in progress: the edit, the export and any problem. */
export interface Decisions {
  review: Review;
  /** Applies a change to the latest review, so two quick decisions both count. */
  onChange: (update: (current: Review) => Review) => void;
  api: ReviewApi;
  select: (index: number) => void;
  /** The field being edited, if any. */
  editing: string | null;
  setEditing: (name: string | null) => void;
  /** The text of the edit. */
  draft: string;
  setDraft: (text: string) => void;
  /** The exported record, once there is one. */
  exported: Export | null;
  setExported: (exported: Export | null) => void;
  problem: string | null;
  setProblem: (problem: string | null) => void;
}

// log.debug('Defines which document a field cites')
/**
 * Returns the document a field's quote comes from.
 *
 * @param name - The field's name. Required.
 * @returns The notice for the notice date, the charge for the rest.
 */
function citedIn(name: string | null = null): DocKind {
  // log.debug('Takes the name, which the caller must give')
  name = required({ name });
  // log.debug('Returns the notice for the notice date, the charge for the rest')
  return name === NOTICE_FIELD ? 'notice' : 'charge';
}

// log.debug('Defines the hook that keeps the selected field and the document on show')
/**
 * Keeps the selected field, and shows the document it cites unless the
 * reviewer picked the other one for it.
 *
 * @param review - The review on screen. Required.
 * @returns The selected field and the document on show, with what
 *   changes them.
 */
export function useSelection(review: Review | null = null): Selection {
  // log.debug('Takes the review, which the caller must give')
  review = required({ review });
  // log.debug('Keeps the place of the selected field')
  const [selected, setSelected] = useState(0);
  // log.debug('Keeps the document the reviewer picked, and for which field')
  const [picked, setPicked] = useState<Picked | null>(null);
  // log.debug('Takes the name of the selected field')
  const field = review.fields[selected] ?? '';
  // log.debug('Finds the document the selected field cites')
  const cited = citedIn(field);
  // log.debug('Shows the document picked for this field, else the one it cites')
  const doc = picked?.field === field ? picked.doc : cited;

  // log.debug('Defines how a reviewer picks the document on show')
  /**
   * Shows a document beside the selected field.
   *
   * @param next - The document to show. Required.
   */
  const pick = (next: DocKind | null = null): void => {
    // log.debug('Takes the document, which the caller must give')
    next = required({ next });
    // log.debug('Keeps it, for the field it was picked for')
    setPicked({ field, doc: next });
  };

  // log.debug('Returns the selection, the document on show, and what changes them')
  return {
    selected,
    select: setSelected,
    field,
    current: fieldOf(review.record, field),
    doc,
    citing: doc === cited,
    pick,
  };
}

// log.debug('Defines the hook that keeps the decisions in progress')
/**
 * Keeps the edit, the export and any problem, with what the decisions
 * need to be sent.
 *
 * @param review - The review on screen. Required.
 * @param onChange - Applies a change to the latest review. Required.
 * @param api - The calls that send a decision and fetch the export.
 *   Required.
 * @param select - Selects a field by its place in the record. Required.
 * @returns The decisions in progress, each part with its setter.
 */
export function useDecisions(
  review: Review | null = null,
  onChange: ((update: (current: Review) => Review) => void) | null = null,
  api: ReviewApi | null = null,
  select: ((index: number) => void) | null = null,
): Decisions {
  // log.debug('Takes the review, which the caller must give')
  review = required({ review });
  // log.debug('Takes the change handler, which the caller must give')
  onChange = required({ onChange });
  // log.debug('Takes the calls, which the caller must give')
  api = required({ api });
  // log.debug('Takes what selects a field, which the caller must give')
  select = required({ select });
  // log.debug('Keeps the field being edited, if any')
  const [editing, setEditing] = useState<string | null>(null);
  // log.debug('Keeps the text of the edit')
  const [draft, setDraft] = useState('');
  // log.debug('Keeps the exported record, once there is one')
  const [exported, setExported] = useState<Export | null>(null);
  // log.debug('Keeps a problem to show')
  const [problem, setProblem] = useState<string | null>(null);
  // log.debug('Returns the decisions in progress')
  return {
    review,
    onChange,
    api,
    select,
    editing,
    setEditing,
    draft,
    setDraft,
    exported,
    setExported,
    problem,
    setProblem,
  };
}

// log.debug('Defines how a decision is sent and recorded')
/**
 * Sends a decision, then records it on the latest review with the
 * progress the service reports, or shows why it failed.
 *
 * @param work - The decisions in progress. Required.
 * @param decision - The decision to send. Required.
 */
export function record(work: Decisions | null = null, decision: Decision | null = null): void {
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });
  // log.debug('Takes the decision, which the caller must give')
  decision = required({ decision });
  // log.debug('Clears any problem')
  work.setProblem(null);
  // log.debug('Sends the decision, then records it with the progress the service reports')
  work.api
    .decide(work.review.review_id, decision)
    .then((done) => {
      // log.debug('Records the decision on the latest review, so quick decisions all count')
      work.onChange((latest) => ({
        ...latest,
        decisions: { ...latest.decisions, [decision.field]: decision },
        decided: done.decided,
      }));
      // log.debug('Closes any edit form')
      work.setEditing(null);
    })
    .catch((error: unknown) => work.setProblem(describeError(error)));
}

// log.debug('Defines how editing a field starts')
/**
 * Opens the edit form on a field, starting from its value, and selects
 * the field.
 *
 * @param work - The decisions in progress. Required.
 * @param name - The field's name. Required.
 */
function startEdit(work: Decisions | null = null, name: string | null = null): void {
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the decision already made on the field, if any')
  const earlier = work.review.decisions[name];
  // log.debug('Starts from the edited value, else the extracted one')
  const base =
    earlier?.action === EDIT ? (earlier.value ?? null) : fieldOf(work.review.record, name).value;
  // log.debug('Puts the value in the edit box')
  work.setDraft(formatValue(base));
  // log.debug('Opens the edit form on the field')
  work.setEditing(name);
  // log.debug('Selects the field')
  work.select(work.review.fields.indexOf(name));
}

// log.debug('Defines what a decision button or key does to a field')
/**
 * Opens the edit form for an edit, and sends an accept or a reject at
 * once.
 *
 * @param work - The decisions in progress. Required.
 * @param name - The field's name. Required.
 * @param action - The decision. Required.
 */
export function act(
  work: Decisions | null = null,
  name: string | null = null,
  action: Action | null = null,
): void {
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the decision, which the caller must give')
  action = required({ action });
  // log.debug('Opens the edit form for an edit')
  if (action === EDIT) {
    // log.debug('Starts editing')
    startEdit(work, name);
    // log.debug('Leaves the handler')
    return;
  }
  // log.debug('Records an accept or a reject at once')
  record(work, { field: name, action });
}

// log.debug('Defines how an edit is saved')
/**
 * Reads the typed text back into the shape of the field, and sends it
 * as an edit.
 *
 * @param work - The decisions in progress. Required.
 * @param name - The field's name. Required.
 */
export function save(work: Decisions | null = null, name: string | null = null): void {
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Reads the typed text back into the shape of the field')
  const value = parseValue(name, work.draft, fieldOf(work.review.record, name).value);
  // log.debug('Records the edit with its new value')
  record(work, { field: name, action: EDIT, value });
}

// log.debug('Defines the export')
/**
 * Fetches the exported record, or shows why it could not.
 *
 * @param work - The decisions in progress. Required.
 */
export function exportRecord(work: Decisions | null = null): void {
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });
  // log.debug('Clears any problem')
  work.setProblem(null);
  // log.debug('Fetches the exported record, or says why it could not')
  work.api
    .exportReview(work.review.review_id)
    .then(work.setExported)
    .catch((error: unknown) => work.setProblem(describeError(error)));
}

// log.debug('Defines which key presses the screen leaves alone')
/**
 * Tells whether the screen leaves a key press alone.
 *
 * @param work - The decisions in progress. Required.
 * @param event - The key press. Required.
 * @returns True while an edit or the export is open, for a key pressed
 *   with a modifier, and for one typed into a form control.
 */
function ignored(work: Decisions | null = null, event: KeyboardEvent | null = null): boolean {
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });
  // log.debug('Takes the key press, which the caller must give')
  event = required({ event });
  // log.debug('Ignores keys while editing, while the export shows, and with modifiers')
  if (
    work.editing !== null ||
    work.exported !== null ||
    event.ctrlKey ||
    event.metaKey ||
    event.altKey
  ) {
    // log.debug('Returns yes')
    return true;
  }
  // log.debug('Returns whether the key was typed into a form control')
  return event.target instanceof Element && event.target.closest(TYPING) !== null;
}

// log.debug('Defines the hook that moves through the fields and decides them from the keyboard')
/**
 * Listens for keys while the screen is open: j and k move, a accepts, e
 * edits, r rejects, unless an edit or the export is open.
 *
 * @param selection - The field selected. Required.
 * @param work - The decisions in progress. Required.
 */
export function useReviewKeys(
  selection: Selection | null = null,
  work: Decisions | null = null,
): void {
  // log.debug('Takes the selection, which the caller must give')
  selection = required({ selection });
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });

  // log.debug('Defines what a key press does, with the latest state')
  const onKey = useEffectEvent((event: KeyboardEvent) => {
    // log.debug('Ignores keys while editing, while the export shows, with modifiers or in a form')
    if (ignored(work, event)) {
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
      selection.select((index) =>
        Math.min(work.review.fields.length - 1, Math.max(0, index + step)),
      );
    } else if (action !== undefined) {
      // log.debug('Decides the selected field')
      act(work, selection.field, action);
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
    /**
     * Hands a key press to the handler, which sees the latest state.
     *
     * @param event - The key press. Required.
     */
    const listen = (event: KeyboardEvent | null = null): void => {
      // log.debug('Takes the key press, which the browser gives')
      event = required({ event });
      // log.debug('Hands it to the handler')
      onKey(event);
    };
    // log.debug('Starts listening')
    window.addEventListener(KEYDOWN, listen);
    // log.debug('Stops listening when the screen closes')
    return () => window.removeEventListener(KEYDOWN, listen);
  }, []);
}

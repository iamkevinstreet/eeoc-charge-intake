// ########################################################################
// #                 frontend/src/components/FieldRow.tsx                 #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           One field of the record: its value or edit form, #
// #                     the quoted evidence, confidence, decisions.      #
// ########################################################################
/** One field of the record: its value or edit form, the quoted evidence, its confidence, decisions. */

import { LIST_FIELDS, SUMMARY_FIELD, YES_NO_FIELD } from '../config';
import { ACTIONS, ACTION_LABELS, ACTION_VERBS, classes, fieldLabel, percent } from '../format';
import type { Action, Decision, Sourced, Value } from '../types';
import { NO, YES, formatValue, isEmpty } from '../values';

interface Props {
  name: string;
  sourced: Sourced;
  /** The field as the model gave it, before verification. */
  raw: Sourced;
  decision: Decision | undefined;
  /** Whether verification emptied the field because its quote was not on its page. */
  removed: boolean;
  selected: boolean;
  /** The text of the edit when the field is being edited, else null. */
  draft: string | null;
  onSelect: () => void;
  onAction: (action: Action) => void;
  onDraft: (text: string) => void;
  onSave: () => void;
  onCancel: () => void;
}

interface ValueProps {
  sourced: Sourced;
  decision: Decision | undefined;
}

interface EditProps {
  name: string;
  label: string;
  draft: string;
  onDraft: (text: string) => void;
  onSave: () => void;
  onCancel: () => void;
}

interface EvidenceProps {
  name: string;
  sourced: Sourced;
  raw: Sourced;
  removed: boolean;
}

// log.debug('Sets the class of the quieter notes')
const META = 'ec-meta';
// log.debug('Sets the class of a quoted passage')
const QUOTE = 'ec-quote';
// log.debug('Sets the class of the edit controls')
const INPUT = 'ec-edit__input';
// log.debug('Lists the two answers a yes or no field offers')
const YES_NO: readonly string[] = [YES, NO];

// log.debug('Defines how the value of a field is shown')
function FieldValue({ sourced, decision }: ValueProps) {
  // log.debug('Notes whether the reviewer gave the field a new value')
  const edited = decision?.action === 'edit';
  // log.debug('Notes whether there is no value to show')
  const empty = !edited && isEmpty(sourced.value);
  // log.debug('Takes the value to show: the edited one, else the extracted one')
  const shown = edited ? (decision.value ?? null) : sourced.value;
  // log.debug('Returns the value, struck through when rejected, or why the field is empty')
  return (
    <div
      className={classes(
        'ec-field__value',
        empty && 'ec-field__value--empty',
        decision?.action === 'reject' && 'ec-field__value--struck',
      )}
    >
      {empty ? (sourced.reason ?? 'Not found') : formatValue(shown)}
    </div>
  );
}

// log.debug('Defines the edit form of a field')
function EditForm({ name, label, draft, onDraft, onSave, onCancel }: EditProps) {
  // log.debug('Names the control for people using a screen reader')
  const control = `New value for ${label}`;

  // log.debug('Defines the submit handler')
  const submit = (event: React.SubmitEvent<HTMLFormElement>): void => {
    // log.debug('Stops the page reloading')
    event.preventDefault();
    // log.debug('Saves the edit')
    onSave();
  };

  // log.debug('Returns a yes or no choice for that field, else a text box, and the buttons')
  return (
    <form className="ec-edit" onSubmit={submit}>
      {name === YES_NO_FIELD ? (
        <select
          className={INPUT}
          value={draft}
          aria-label={control}
          autoFocus
          onChange={(event) => onDraft(event.target.value)}
        >
          {YES_NO.map((choice) => (
            <option key={choice} value={choice}>
              {choice}
            </option>
          ))}
        </select>
      ) : (
        <input
          className={INPUT}
          value={draft}
          aria-label={control}
          autoFocus
          placeholder={LIST_FIELDS.includes(name) ? 'Comma separated' : undefined}
          onChange={(event) => onDraft(event.target.value)}
        />
      )}
      <button className="ec-button ec-button--primary" type="submit">
        Save
      </button>
      <button className="ec-button" type="button" onClick={onCancel}>
        Cancel
      </button>
    </form>
  );
}

// log.debug('Defines the note for a value that has no single quote behind it')
function unquoted(name: string, value: Value): string | null {
  // log.debug('Explains a summary, which paraphrases the particulars')
  if (name === SUMMARY_FIELD) {
    // log.debug('Returns the note for a summary')
    return 'Paraphrased from the particulars; no single span.';
  }
  // log.debug('Explains a box left unmarked')
  if (name === YES_NO_FIELD && value === false) {
    // log.debug('Returns the note for an unmarked box')
    return 'Box not marked on the form.';
  }
  // log.debug('Returns no note for any other field')
  return null;
}

// log.debug('Defines the confidence the model gave, as a small bar and a percent')
function Confidence({ value }: { value: number }) {
  // log.debug('Turns the confidence into a whole percent')
  const share = percent(value);
  // log.debug('Returns the bar and the number')
  return (
    <span className="ec-confidence" title="The confidence the model reported">
      <span className="ec-confidence__bar" aria-hidden="true">
        <span className="ec-confidence__fill" style={{ width: `${share}%` }} />
      </span>
      {share}%
    </span>
  );
}

// log.debug('Defines the evidence under a value: the quote and its page, a note, the confidence')
function Evidence({ name, sourced, raw, removed }: EvidenceProps) {
  // log.debug('Notes whether the field has a value')
  const filled = !isEmpty(sourced.value);
  // log.debug('Finds the note for a value with no quote behind it')
  const note = filled && sourced.span === null ? unquoted(name, sourced.value) : null;
  // log.debug('Returns whatever evidence the field has')
  return (
    <div className="ec-field__evidence">
      {filled && sourced.span !== null && (
        <>
          <span className={META}>Page {sourced.page}: </span>
          <q className={QUOTE}>{sourced.span}</q>
        </>
      )}
      {note !== null && <span className={META}>{note}</span>}
      {removed && raw.value !== null && (
        <span className={META}>
          The model proposed{' '}
          <q className={classes(QUOTE, 'ec-quote--struck')}>{formatValue(raw.value)}</q> citing
          page {raw.page}, but that text is not on page {raw.page}. Left empty.
        </span>
      )}
      {filled && <Confidence value={sourced.confidence} />}
    </div>
  );
}

// log.debug('Defines one row of the field list')
export function FieldRow({
  name,
  sourced,
  raw,
  decision,
  removed,
  selected,
  draft,
  onSelect,
  onAction,
  onDraft,
  onSave,
  onCancel,
}: Props) {
  // log.debug('Takes the name people see')
  const label = fieldLabel(name);
  // log.debug('Returns the row: name and decision, value or edit form, evidence, buttons')
  return (
    <li
      className={classes(
        'ec-field',
        selected && 'ec-field--selected',
        decision && `ec-field--${decision.action}`,
      )}
      onClick={onSelect}
    >
      <div className="ec-field__main">
        <div className="ec-field__name">
          {label}
          {decision !== undefined && (
            <span className={`ec-chip ec-chip--${decision.action}`}>
              {ACTION_LABELS[decision.action]}
            </span>
          )}
        </div>
        {draft === null ? (
          <FieldValue sourced={sourced} decision={decision} />
        ) : (
          <EditForm
            name={name}
            label={label}
            draft={draft}
            onDraft={onDraft}
            onSave={onSave}
            onCancel={onCancel}
          />
        )}
        <Evidence name={name} sourced={sourced} raw={raw} removed={removed} />
      </div>
      <div className="ec-field__actions" role="group" aria-label={`Decide ${label}`}>
        {ACTIONS.map((action) => (
          <button
            key={action}
            type="button"
            className="ec-button ec-button--small"
            aria-pressed={decision?.action === action}
            onClick={() => onAction(action)}
          >
            {ACTION_VERBS[action]}
          </button>
        ))}
      </div>
    </li>
  );
}

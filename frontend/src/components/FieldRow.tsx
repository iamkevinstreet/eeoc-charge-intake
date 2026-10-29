// ########################################################################
// #                 frontend/src/components/FieldRow.tsx                 #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * One field of the record: its value or its edit form, the quoted
 * evidence and the confidence behind it, and the buttons that accept,
 * edit or reject it.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from '../config';
import { classes, fieldLabel, percent } from '../format';
import { required } from '../lib/required';
import type { Action, Decision, Sourced, Value } from '../types';
import { formatValue, isEmpty } from '../values';
import { EditForm } from './EditForm';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the field that holds a yes or a no from the config')
const YES_NO_FIELD = CONFIG.record.yes_no_field;
// log.debug('Takes the field the model paraphrases instead of quoting from the config')
const SUMMARY_FIELD = CONFIG.record.summary_field;
// log.debug('Takes the class of the quieter notes from the config')
const META = CONFIG.ui.note_class;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the class of a quoted passage')
const QUOTE = 'ec-quote';
// log.debug('Lists the decisions, in the order the buttons show them')
const ACTIONS: readonly Action[] = ['accept', 'edit', 'reject'];
// log.debug('Lists the button that makes each decision')
const ACTION_VERBS: Readonly<Record<Action, string>> = {
  accept: 'Accept',
  edit: 'Edit',
  reject: 'Reject',
};
// log.debug('Lists the label a field carries once decided')
const ACTION_LABELS: Readonly<Record<Action, string>> = {
  accept: 'Accepted',
  edit: 'Edited',
  reject: 'Rejected',
};

// ########################################################################
// #                              Field row                               #
// ########################################################################
interface Props {
  name?: string | null;
  sourced?: Sourced | null;
  /** The field as the model gave it, before verification. */
  raw?: Sourced | null;
  decision?: Decision | null;
  /** Whether verification emptied the field because its quote was not on its page. */
  removed?: boolean;
  selected?: boolean;
  /** The text of the edit when the field is being edited, else null. */
  draft?: string | null;
  onSelect?: (() => void) | null;
  onAction?: ((action: Action) => void) | null;
  onDraft?: ((text: string) => void) | null;
  onSave?: (() => void) | null;
  onCancel?: (() => void) | null;
}

interface ValueProps {
  sourced?: Sourced | null;
  decision?: Decision | null;
}

interface NameProps {
  name?: string | null;
  decision?: Decision | null;
}

interface ButtonProps {
  name?: string | null;
  decision?: Decision | null;
  onAction?: ((action: Action) => void) | null;
}

interface ConfidenceProps {
  value?: number | null;
}

interface EvidenceProps {
  name?: string | null;
  sourced?: Sourced | null;
  raw?: Sourced | null;
  removed?: boolean;
}

// log.debug('Defines how the value of a field is shown')
/**
 * Renders a field's value: the edited one, else the extracted one.
 *
 * @param props - The component's props.
 * @param props.sourced - The field as extracted. Required.
 * @param props.decision - The reviewer's decision on the field; null
 *   before there is one.
 * @returns The value, struck through when rejected, or why the field is
 *   empty.
 */
function FieldValue({ sourced = null, decision = null }: ValueProps = {}): React.JSX.Element {
  // log.debug('Takes the field, which the caller must give')
  sourced = required({ sourced });
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

// log.debug('Defines the note for a value that has no single quote behind it')
/**
 * Returns the note for a value that has no single quote behind it.
 *
 * @param name - The field's name. Required.
 * @param value - The field's value; null when it is empty.
 * @returns Why there is no quote, for a summary or an unmarked box; null
 *   for any other field.
 */
function unquoted(name: string | null = null, value: Value = null): string | null {
  // log.debug('Takes the name, which the caller must give')
  name = required({ name });
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
/**
 * Renders the confidence the model reported, as a small bar and a
 * percent.
 *
 * @param props - The component's props.
 * @param props.value - The confidence, from 0 to 1. Required.
 * @returns The bar and the number.
 */
function Confidence({ value = null }: ConfidenceProps = {}): React.JSX.Element {
  // log.debug('Takes the confidence, which the caller must give')
  value = required({ value });
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
/**
 * Renders the evidence under a value: the quote and its page, a note
 * when there is no quote, what verification removed, the confidence.
 *
 * @param props - The component's props.
 * @param props.name - The field's name. Required.
 * @param props.sourced - The field after verification. Required.
 * @param props.raw - The field as the model gave it. Required.
 * @param props.removed - Whether verification emptied the field because
 *   its quote was not on its page.
 * @returns Whatever evidence the field has.
 */
function Evidence({
  name = null,
  sourced = null,
  raw = null,
  removed = false,
}: EvidenceProps = {}): React.JSX.Element {
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the field, which the caller must give')
  sourced = required({ sourced });
  // log.debug('Takes the field as the model gave it, which the caller must give')
  raw = required({ raw });
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

// log.debug('Defines the name of a field, with the decision made on it')
/**
 * Renders the name people see for a field, and a chip naming the
 * decision once there is one.
 *
 * @param props - The component's props.
 * @param props.name - The field's name. Required.
 * @param props.decision - The reviewer's decision; null before there is
 *   one.
 * @returns The name and the chip.
 */
function FieldName({ name = null, decision = null }: NameProps = {}): React.JSX.Element {
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Returns the label, with the decision once there is one')
  return (
    <div className="ec-field__name">
      {fieldLabel(name)}
      {decision !== null && (
        <span className={`ec-chip ec-chip--${decision.action}`}>
          {ACTION_LABELS[decision.action]}
        </span>
      )}
    </div>
  );
}

// log.debug('Defines the buttons that decide a field')
/**
 * Renders the buttons that accept, edit or reject a field, the one
 * already chosen pressed.
 *
 * @param props - The component's props.
 * @param props.name - The field's name. Required.
 * @param props.decision - The reviewer's decision; null before there is
 *   one.
 * @param props.onAction - Makes a decision on the field. Required.
 * @returns One button per decision, as a labelled group.
 */
function DecisionButtons({
  name = null,
  decision = null,
  onAction = null,
}: ButtonProps = {}): React.JSX.Element {
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the decision handler, which the caller must give')
  onAction = required({ onAction });
  // log.debug('Returns one button per decision, the chosen one pressed')
  return (
    <div className="ec-field__actions" role="group" aria-label={`Decide ${fieldLabel(name)}`}>
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
  );
}

// log.debug('Defines one row of the field list')
/**
 * Renders one row of the field list: the field's name and decision, its
 * value or edit form, its evidence, and the decision buttons.
 *
 * @param props - The component's props.
 * @param props.name - The field's name. Required.
 * @param props.sourced - The field after verification. Required.
 * @param props.raw - The field as the model gave it. Required.
 * @param props.decision - The reviewer's decision; null before there is
 *   one.
 * @param props.removed - Whether verification emptied the field.
 * @param props.selected - Whether the field is the one selected.
 * @param props.draft - The text of the edit while the field is being
 *   edited; null otherwise.
 * @param props.onSelect - Selects the field. Required.
 * @param props.onAction - Makes a decision on the field. Required.
 * @param props.onDraft - Takes the edit's text as it changes. Required.
 * @param props.onSave - Saves the edit. Required.
 * @param props.onCancel - Closes the edit form. Required.
 * @returns The row.
 */
export function FieldRow({
  name = null,
  sourced = null,
  raw = null,
  decision = null,
  removed = false,
  selected = false,
  draft = null,
  onSelect = null,
  onAction = null,
  onDraft = null,
  onSave = null,
  onCancel = null,
}: Props = {}): React.JSX.Element {
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the field, which the caller must give')
  sourced = required({ sourced });
  // log.debug('Takes the field as the model gave it, which the caller must give')
  raw = required({ raw });
  // log.debug('Takes the select handler, which the caller must give')
  onSelect = required({ onSelect });
  // log.debug('Takes the decision handler, which the caller must give')
  onAction = required({ onAction });
  // log.debug('Takes the draft handler, which the caller must give')
  onDraft = required({ onDraft });
  // log.debug('Takes the save handler, which the caller must give')
  onSave = required({ onSave });
  // log.debug('Takes the cancel handler, which the caller must give')
  onCancel = required({ onCancel });
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
        <FieldName name={name} decision={decision} />
        {draft === null ? (
          <FieldValue sourced={sourced} decision={decision} />
        ) : (
          <EditForm
            name={name}
            draft={draft}
            onDraft={onDraft}
            onSave={onSave}
            onCancel={onCancel}
          />
        )}
        <Evidence name={name} sourced={sourced} raw={raw} removed={removed} />
      </div>
      <DecisionButtons name={name} decision={decision} onAction={onAction} />
    </li>
  );
}

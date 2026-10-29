// ########################################################################
// #                 frontend/src/components/EditForm.tsx                 #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The edit form of a field: a yes or no choice for the field that holds
 * one, else a text box, comma separated for a list, with buttons that
 * save the edit or close the form.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from '../config';
import { fieldLabel } from '../format';
import { required } from '../lib/required';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the word shown for a true value from the config')
const YES = CONFIG.labels.yes;
// log.debug('Takes the word shown for a false value from the config')
const NO = CONFIG.labels.no;
// log.debug('Takes the field that holds a yes or a no from the config')
const YES_NO_FIELD = CONFIG.record.yes_no_field;
// log.debug('Takes the fields that hold lists from the config')
const LIST_FIELDS = CONFIG.record.list_fields;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the class of the edit controls')
const INPUT = 'ec-edit__input';
// log.debug('Lists the two answers a yes or no field offers')
const YES_NO: readonly string[] = [YES, NO];

// ########################################################################
// #                              Edit form                               #
// ########################################################################
interface Props {
  name?: string | null;
  draft?: string | null;
  onDraft?: ((text: string) => void) | null;
  onSave?: (() => void) | null;
  onCancel?: (() => void) | null;
}

interface InputProps {
  name?: string | null;
  /** The name a screen reader gives the control. */
  control?: string | null;
  draft?: string | null;
  onDraft?: ((text: string) => void) | null;
}

// log.debug('Defines the control the new value is typed or chosen in')
/**
 * Renders the control the new value is entered in: a yes or no choice
 * for the field that holds one, else a text box.
 *
 * @param props - The component's props.
 * @param props.name - The field's name. Required.
 * @param props.control - The name a screen reader gives the control.
 *   Required.
 * @param props.draft - The text of the edit. Required.
 * @param props.onDraft - Takes the text as the reviewer changes it.
 *   Required.
 * @returns The choice or the text box.
 */
function EditInput({
  name = null,
  control = null,
  draft = null,
  onDraft = null,
}: InputProps = {}): React.JSX.Element {
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the control name, which the caller must give')
  control = required({ control });
  // log.debug('Takes the draft, which the caller must give')
  draft = required({ draft });
  // log.debug('Takes the draft handler, which the caller must give')
  onDraft = required({ onDraft });
  // log.debug('Returns a yes or no choice for that field, else a text box')
  return name === YES_NO_FIELD ? (
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
  );
}

// log.debug('Defines the edit form of a field')
/**
 * Renders the edit form of a field: the control for the new value, and
 * buttons that save the edit or close the form.
 *
 * @param props - The component's props.
 * @param props.name - The field's name. Required.
 * @param props.draft - The text of the edit. Required.
 * @param props.onDraft - Takes the text as the reviewer changes it.
 *   Required.
 * @param props.onSave - Saves the edit. Required.
 * @param props.onCancel - Closes the form without saving. Required.
 * @returns The form.
 */
export function EditForm({
  name = null,
  draft = null,
  onDraft = null,
  onSave = null,
  onCancel = null,
}: Props = {}): React.JSX.Element {
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the draft, which the caller must give')
  draft = required({ draft });
  // log.debug('Takes the draft handler, which the caller must give')
  onDraft = required({ onDraft });
  // log.debug('Takes the save handler, which the caller must give')
  onSave = required({ onSave });
  // log.debug('Takes the cancel handler, which the caller must give')
  onCancel = required({ onCancel });
  // log.debug('Names the control for people using a screen reader')
  const control = `New value for ${fieldLabel(name)}`;

  // log.debug('Defines the submit handler')
  /**
   * Saves the edit, instead of reloading the page.
   *
   * @param event - The form's submit event. Required.
   */
  const submit = (event: React.SubmitEvent<HTMLFormElement> | null = null): void => {
    // log.debug('Takes the event, which the caller must give')
    event = required({ event });
    // log.debug('Stops the page reloading')
    event.preventDefault();
    // log.debug('Saves the edit')
    onSave();
  };

  // log.debug('Returns the control for the new value, and the buttons')
  return (
    <form className="ec-edit" onSubmit={submit}>
      <EditInput name={name} control={control} draft={draft} onDraft={onDraft} />
      <button className="ec-button ec-button--primary" type="submit">
        Save
      </button>
      <button className="ec-button" type="button" onClick={onCancel}>
        Cancel
      </button>
    </form>
  );
}

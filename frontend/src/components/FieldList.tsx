// ########################################################################
// #                frontend/src/components/FieldList.tsx                 #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The list of extracted fields on the review screen, in the order the
 * record shows them: one row per field, with its evidence and the
 * buttons that decide it.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { required } from '../lib/required';
import { act, save } from '../reviewing';
import type { Decisions, Selection } from '../reviewing';
import { fieldOf } from '../values';
import { FieldRow } from './FieldRow';

// ########################################################################
// #                              Field list                              #
// ########################################################################
interface Props {
  selection?: Selection | null;
  work?: Decisions | null;
}

// log.debug('Defines the list of fields')
/**
 * Renders the list of fields, one row per field of the review.
 *
 * @param props - The component's props.
 * @param props.selection - The field selected. Required.
 * @param props.work - The decisions in progress, with the review they
 *   are made on. Required.
 * @returns The ordered list of rows.
 */
export function FieldList({ selection = null, work = null }: Props = {}): React.JSX.Element {
  // log.debug('Takes the selection, which the caller must give')
  selection = required({ selection });
  // log.debug('Takes the decisions in progress, which the caller must give')
  work = required({ work });
  // log.debug('Takes the review the decisions are made on')
  const { review } = work;
  // log.debug('Returns one row per field, in the order the record shows them')
  return (
    <ol className="ec-fields" aria-label="Extracted fields">
      {review.fields.map((name, index) => (
        <FieldRow
          key={name}
          name={name}
          sourced={fieldOf(review.record, name)}
          raw={fieldOf(review.raw, name)}
          decision={review.decisions[name] ?? null}
          removed={review.removed.includes(name)}
          selected={index === selection.selected}
          draft={work.editing === name ? work.draft : null}
          onSelect={() => selection.select(index)}
          onAction={(action) => act(work, name, action)}
          onDraft={work.setDraft}
          onSave={() => save(work, name)}
          onCancel={() => work.setEditing(null)}
        />
      ))}
    </ol>
  );
}

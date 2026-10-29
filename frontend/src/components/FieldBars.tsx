// ########################################################################
// #                frontend/src/components/FieldBars.tsx                 #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The accuracy by field chart: one bar per scored field, the share of a
 * run's cases in which the field was right.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { fieldLabel, share } from '../format';
import { required } from '../lib/required';
import { SCORED, fieldAccuracy } from '../scores';
import type { CaseResult } from '../types';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the width of the chart in its own units')
const WIDTH = 600;
// log.debug('Sets the height each bar takes, with the space under it')
const ROW = 26;
// log.debug('Sets the space above the first bar and below the last')
const PAD = 4;
// log.debug('Sets the baseline of the field name')
const LABEL_Y = 14;
// log.debug('Sets where the bars start, after the field names')
const BAR_X = 170;
// log.debug('Sets where each bar starts below the top of its row')
const BAR_Y = 4;
// log.debug('Sets the length of a full bar')
const BAR_WIDTH = 340;
// log.debug('Sets the thickness of a bar')
const BAR_HEIGHT = 14;
// log.debug('Sets where the share is written, after the bars')
const VALUE_X = 520;
// log.debug('Sets the baseline of the share')
const VALUE_Y = 15;

// ########################################################################
// #                            Accuracy chart                            #
// ########################################################################
interface Props {
  results?: CaseResult[] | null;
}

interface BarProps {
  name?: string | null;
  /** How far down the chart the bar sits. */
  top?: number | null;
  /** The share of cases the field was right in, from 0 to 1. */
  value?: number | null;
}

// log.debug('Defines one bar: the field name, the track, the filled part and the share')
/**
 * Renders one bar: the field's name, the track, the filled part and the
 * share.
 *
 * @param props - The component's props.
 * @param props.name - The field's name. Required.
 * @param props.top - How far down the chart the bar sits. Required.
 * @param props.value - The share of cases the field was right in, from
 *   0 to 1. Required.
 * @returns The bar, moved down to its row.
 */
function Bar({ name = null, top = null, value = null }: BarProps = {}): React.JSX.Element {
  // log.debug('Takes the field name, which the caller must give')
  name = required({ name });
  // log.debug('Takes the place of the bar, which the caller must give')
  top = required({ top });
  // log.debug('Takes the share, which the caller must give')
  value = required({ value });
  // log.debug('Returns the bar, moved down to its row')
  return (
    <g transform={`translate(0 ${top})`}>
      <text x="0" y={LABEL_Y} className="ec-bars__label">
        {fieldLabel(name)}
      </text>
      <rect x={BAR_X} y={BAR_Y} width={BAR_WIDTH} height={BAR_HEIGHT} className="ec-bars__track" />
      <rect
        x={BAR_X}
        y={BAR_Y}
        width={BAR_WIDTH * value}
        height={BAR_HEIGHT}
        className="ec-bars__fill"
      />
      <text x={VALUE_X} y={VALUE_Y} className="ec-bars__value">
        {share(value)}
      </text>
    </g>
  );
}

// log.debug('Defines the chart of accuracy by field')
/**
 * Renders the chart of accuracy by field, over a run's cases.
 *
 * @param props - The component's props.
 * @param props.results - The run's cases. Required.
 * @returns The chart, one bar per scored field.
 */
export function FieldBars({ results = null }: Props = {}): React.JSX.Element {
  // log.debug('Takes the cases, which the caller must give')
  results = required({ results });
  // log.debug('Sizes the chart to hold every scored field')
  const height = SCORED.length * ROW + PAD * 2;
  // log.debug('Returns one bar per scored field')
  return (
    <svg
      className="ec-bars"
      viewBox={`0 0 ${WIDTH} ${height}`}
      role="img"
      aria-label="Accuracy by field"
    >
      {SCORED.map((name, index) => (
        <Bar key={name} name={name} top={index * ROW + PAD} value={fieldAccuracy(results, name)} />
      ))}
    </svg>
  );
}

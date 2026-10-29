// ########################################################################
// #                frontend/src/components/FieldBars.tsx                 #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The accuracy by field chart: one bar per scored  #
// #                     field, averaged over the run's cases.            #
// ########################################################################
/** The accuracy by field chart: one bar per scored field, averaged over the cases of a run. */

import { fieldLabel, share } from '../format';
import { SCORED, fieldAccuracy } from '../scores';
import type { CaseResult } from '../types';

interface Props {
  results: CaseResult[];
}

interface BarProps {
  name: string;
  /** How far down the chart the bar sits. */
  top: number;
  /** The share of cases the field was right in, from 0 to 1. */
  value: number;
}

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

// log.debug('Defines one bar: the field name, the track, the filled part and the share')
function Bar({ name, top, value }: BarProps) {
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
export function FieldBars({ results }: Props) {
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

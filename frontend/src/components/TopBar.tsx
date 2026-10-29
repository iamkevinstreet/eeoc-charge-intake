// ########################################################################
// #                  frontend/src/components/TopBar.tsx                  #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The top bar every screen shares: the app's name, a button for each
 * section with the one on show marked, the link to the code, and a
 * badge in demo mode.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { CONFIG } from '../config';
import { required } from '../lib/required';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the address of the source code the bar links to from the config')
const CODE_URL = CONFIG.ui.code_url;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets the class of each link in the bar')
const LINK = 'ec-bar__link';

// ########################################################################
// #                               Top bar                                #
// ########################################################################
/** A section of the bar: the screen it opens, and its label. */
interface Section<S extends string> {
  screen: S;
  label: string;
}

interface Props<S extends string> {
  sections?: readonly Section<S>[] | null;
  current?: S | null;
  demo?: boolean;
  onShow?: ((screen: S) => void) | null;
}

// log.debug('Defines the top bar')
/**
 * Renders the top bar: the app's name, the sections, the code link and,
 * in demo mode, its badge.
 *
 * @param props - The component's props.
 * @param props.sections - The sections, in the order the bar shows
 *   them. Required.
 * @param props.current - The section the bar marks as on show.
 *   Required.
 * @param props.demo - Whether the service answers from the known
 *   answers instead of a model.
 * @param props.onShow - Opens a section's screen. Required.
 * @returns The bar.
 */
export function TopBar<S extends string>({
  sections = null,
  current = null,
  demo = false,
  onShow = null,
}: Props<S> = {}): React.JSX.Element {
  // log.debug('Takes the sections, which the caller must give')
  sections = required({ sections });
  // log.debug('Takes the section on show, which the caller must give')
  current = required({ current });
  // log.debug('Takes the show handler, which the caller must give')
  onShow = required({ onShow });
  // log.debug('Returns the bar')
  return (
    <nav className="ec-bar" aria-label="Sections">
      <span className="ec-bar__name">EEOC charge intake</span>
      <div className="ec-bar__links">
        {sections.map((item) => (
          <button
            key={item.screen}
            type="button"
            className={LINK}
            aria-current={current === item.screen ? 'page' : undefined}
            onClick={() => onShow(item.screen)}
          >
            {item.label}
          </button>
        ))}
        <a className={LINK} href={CODE_URL}>
          Code
        </a>
      </div>
      {demo && <span className="ec-badge">Demo</span>}
    </nav>
  );
}

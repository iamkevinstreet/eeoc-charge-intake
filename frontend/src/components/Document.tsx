// ########################################################################
// #                 frontend/src/components/Document.tsx                 #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The document pane: the charge or the notice, page by page, with the
 * quote the selected field cites marked and scrolled into the middle of
 * the pane.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Third-party
import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

// Local
import { CONFIG } from '../config';
import { mark } from '../highlight';
import type { Marked } from '../highlight';
import { required } from '../lib/required';
import type { DocKind } from '../types';

// ########################################################################
// #                           Global constants                           #
// ########################################################################
// log.debug('Takes the class of the quieter notes from the config')
const META = CONFIG.ui.note_class;

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Lists the two documents, in the order the tabs show them')
const DOCS: readonly { id: DocKind; label: string }[] = [
  { id: 'charge', label: 'Charge' },
  { id: 'notice', label: 'Notice' },
];
// log.debug('Sets the divisor that centres the quote in the pane')
const HALF = 2;

// ########################################################################
// #                            Document pane                             #
// ########################################################################
interface Props {
  doc?: DocKind | null;
  pages?: string[] | null;
  /** The page the selected field cites, counted from 1, when this document holds it. */
  page?: number | null;
  quote?: string | null;
  onDoc?: ((doc: DocKind) => void) | null;
}

interface PageProps {
  number?: number | null;
  text?: string | null;
  /** The page split around the quote, when the quote is on this page. */
  hit?: Marked | null;
  markRef?: RefObject<HTMLElement | null> | null;
}

/** The refs that find the marked quote and the pane that scrolls. */
interface Centring {
  markRef: RefObject<HTMLElement | null>;
  paneRef: RefObject<HTMLDivElement | null>;
}

// log.debug('Defines the hook that keeps the cited quote in the middle of the pane')
/**
 * Scrolls the pane, not the window, so the marked quote sits in its
 * middle whenever the document, the page or the quote changes.
 *
 * @param doc - The document on show.
 * @param page - The page the selected field cites; null for none.
 * @param quote - The text the selected field quotes; null for none.
 * @returns The refs to put on the marked quote and on the pane.
 */
function useCentredQuote(
  doc: DocKind | null = null,
  page: number | null = null,
  quote: string | null = null,
): Centring {
  // log.debug('Keeps the marked quote, to scroll to it')
  const markRef = useRef<HTMLElement>(null);
  // log.debug('Keeps the pane that scrolls')
  const paneRef = useRef<HTMLDivElement>(null);

  // log.debug('Scrolls the pane, not the window, to centre the quote when it changes')
  useEffect(() => {
    // log.debug('Takes the marked quote')
    const target = markRef.current;
    // log.debug('Takes the pane')
    const pane = paneRef.current;
    // log.debug('Does nothing when there is no quote on show')
    if (target === null || pane === null) {
      // log.debug('Leaves the pane where it is')
      return;
    }
    // log.debug('Measures how far the quote sits below the top of the pane')
    const offset = target.getBoundingClientRect().top - pane.getBoundingClientRect().top;
    // log.debug('Scrolls so the quote sits in the middle; the style makes it smooth')
    pane.scrollTop = Math.max(0, pane.scrollTop + offset - pane.clientHeight / HALF);
  }, [doc, page, quote]);

  // log.debug('Returns the refs')
  return { markRef, paneRef };
}

// log.debug('Defines one page of the document')
/**
 * Renders one page of the document, with the quote marked when it is on
 * this page.
 *
 * @param props - The component's props.
 * @param props.number - The page's number, counted from 1. Required.
 * @param props.text - The page's extracted text. Required.
 * @param props.hit - The page split around the quote; null when the
 *   quote is not on this page.
 * @param props.markRef - Where the marked quote is kept, so the pane can
 *   scroll to it. Required.
 * @returns The page: its number, then the marked quote, its text, or a
 *   note that it has none.
 */
function Page({
  number = null,
  text = null,
  hit = null,
  markRef = null,
}: PageProps = {}): React.JSX.Element {
  // log.debug('Takes the page number, which the caller must give')
  number = required({ number });
  // log.debug('Takes the text, which the caller must give')
  text = required({ text });
  // log.debug('Takes the place the mark is kept, which the caller must give')
  markRef = required({ markRef });
  // log.debug('Returns the page: the marked quote, its text, or a note that it has none')
  return (
    <article className="ec-page" aria-label={`Page ${number}`}>
      <div className="ec-page__label">Page {number}</div>
      <pre className="ec-page__text">
        {hit !== null && (
          <>
            {hit.before}
            <mark ref={markRef} className="ec-mark">
              {hit.quote}
            </mark>
            {hit.after}
          </>
        )}
        {hit === null && text !== '' && text}
        {hit === null && text === '' && <span className={META}>No text on this page.</span>}
      </pre>
    </article>
  );
}

// log.debug('Defines the document pane')
/**
 * Renders the document pane: a tab for each document, the page count
 * and every page, the cited quote marked and centred.
 *
 * @param props - The component's props.
 * @param props.doc - The document on show. Required.
 * @param props.pages - The document's pages of extracted text. Required.
 * @param props.page - The page the selected field cites, counted from
 *   1; null when this document holds no cited page.
 * @param props.quote - The text the selected field quotes; null for
 *   none.
 * @param props.onDoc - Shows the other document. Required.
 * @returns The pane.
 */
export function Document({
  doc = null,
  pages = null,
  page = null,
  quote = null,
  onDoc = null,
}: Props = {}): React.JSX.Element {
  // log.debug('Takes the document, which the caller must give')
  doc = required({ doc });
  // log.debug('Takes the pages, which the caller must give')
  pages = required({ pages });
  // log.debug('Takes the tab handler, which the caller must give')
  onDoc = required({ onDoc });
  // log.debug('Keeps the cited quote in the middle of the pane')
  const { markRef, paneRef } = useCentredQuote(doc, page, quote);
  // log.debug('Takes the text of the cited page, or nothing when no page is cited')
  const cited = page === null ? null : (pages[page - 1] ?? '');
  // log.debug('Splits the cited page around the quote')
  const hit = cited === null ? null : mark(cited, quote);
  // log.debug('Notes a quote that is not on the page it cites')
  const missing = quote !== null && cited !== null && hit === null;

  // log.debug('Returns the tabs, the page count and the pages')
  return (
    <section className="ec-document" aria-label="Document text">
      <header className="ec-document__head">
        <div className="ec-tabs" role="tablist" aria-label="Documents">
          {DOCS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={doc === item.id}
              className="ec-tab"
              onClick={() => onDoc(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <span className={META}>
          {pages.length} {pages.length === 1 ? 'page' : 'pages'} of extracted text
          {missing && '. The cited text was not found on the cited page.'}
        </span>
      </header>
      <div className="ec-document__pages" ref={paneRef}>
        {pages.map((text, index) => (
          <Page
            key={index}
            number={index + 1}
            text={text}
            hit={index + 1 === page ? hit : null}
            markRef={markRef}
          />
        ))}
      </div>
    </section>
  );
}

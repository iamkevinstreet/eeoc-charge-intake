// ########################################################################
// #                 frontend/src/components/Document.tsx                 #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           The document pane: the charge or the notice,     #
// #                     page by page, with the cited quote marked.       #
// ########################################################################
/** The document pane: the charge or the notice, page by page, with the cited quote marked. */

import { useEffect, useRef } from 'react';
import type { RefObject } from 'react';

import { mark } from '../highlight';
import type { Marked } from '../highlight';
import type { DocKind } from '../types';

interface Props {
  doc: DocKind;
  pages: string[];
  /** The page the selected field cites, counted from 1, when this document holds it. */
  page: number | null;
  quote: string | null;
  onDoc: (doc: DocKind) => void;
}

interface PageProps {
  number: number;
  text: string;
  /** The page split around the quote, when the quote is on this page. */
  hit: Marked | null;
  markRef: RefObject<HTMLElement | null>;
}

// log.debug('Lists the two documents, in the order the tabs show them')
const DOCS: readonly { id: DocKind; label: string }[] = [
  { id: 'charge', label: 'Charge' },
  { id: 'notice', label: 'Notice' },
];
// log.debug('Sets the divisor that centres the quote in the pane')
const HALF = 2;
// log.debug('Sets the class of the quieter notes')
const META = 'ec-meta';

// log.debug('Defines one page of the document')
function Page({ number, text, hit, markRef }: PageProps) {
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
export function Document({ doc, pages, page, quote, onDoc }: Props) {
  // log.debug('Keeps the marked quote, to scroll to it')
  const markRef = useRef<HTMLElement>(null);
  // log.debug('Keeps the pane that scrolls')
  const paneRef = useRef<HTMLDivElement>(null);
  // log.debug('Takes the text of the cited page, or nothing when no page is cited')
  const cited = page === null ? null : (pages[page - 1] ?? '');
  // log.debug('Splits the cited page around the quote')
  const hit = cited === null ? null : mark(cited, quote);
  // log.debug('Notes a quote that is not on the page it cites')
  const missing = quote !== null && cited !== null && hit === null;

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

import { useEffect, useRef } from 'react';
import { locate } from '../highlight';

interface Props {
  doc: 'charge' | 'notice';
  pages: string[];
  page: number | null; // 1-based page the selected field cites
  span: string | null;
  onDoc: (doc: 'charge' | 'notice') => void;
  found: boolean | null; // null when nothing is selected
}

export function Document({ doc, pages, page, span, onDoc, found }: Props) {
  const markRef = useRef<HTMLElement | null>(null);
  const paneRef = useRef<HTMLDivElement | null>(null);

  // Scroll the pane, not the window, so the ledger stays where the reviewer left it.
  useEffect(() => {
    const mark = markRef.current;
    const pane = paneRef.current;
    if (!mark || !pane) return;
    const top = mark.getBoundingClientRect().top - pane.getBoundingClientRect().top + pane.scrollTop;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    pane.scrollTo({ top: Math.max(0, top - pane.clientHeight / 2), behavior: reduce ? 'auto' : 'smooth' });
  }, [doc, page, span]);

  return (
    <section className="document" aria-label="Document text">
      <header className="document-head">
        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={doc === 'charge'} className="tab" onClick={() => onDoc('charge')}>
            Charge
          </button>
          <button role="tab" aria-selected={doc === 'notice'} className="tab" onClick={() => onDoc('notice')}>
            Notice
          </button>
        </div>
        <span className="meta">
          {pages.length} {pages.length === 1 ? 'page' : 'pages'} of extracted text
          {found === false && span ? '. The cited text was not found on the cited page.' : ''}
        </span>
      </header>
      <div className="document-pages" ref={paneRef}>
        {pages.map((text, i) => {
          const n = i + 1;
          const hit = n === page ? locate(text, span) : null;
          return (
            <article key={n} className="page" aria-label={`Page ${n}`}>
              <div className="page-label">Page {n}</div>
              <pre className="page-text">
                {hit ? (
                  <>
                    {text.slice(0, hit[0])}
                    <mark ref={markRef}>{text.slice(hit[0], hit[1])}</mark>
                    {text.slice(hit[1])}
                  </>
                ) : (
                  text || <span className="meta">No text on this page.</span>
                )}
              </pre>
            </article>
          );
        })}
      </div>
    </section>
  );
}

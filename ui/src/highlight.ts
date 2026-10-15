import type { Value } from './types';

/** Locate `span` inside `text` the way the service verifies it: ignoring case and runs of whitespace. */
export function locate(text: string, span: string | null | undefined): [number, number] | null {
  if (!span || !span.trim()) return null;
  const words = span.trim().split(/\s+/).map(escape);
  const re = new RegExp(words.join('\\s+'), 'i');
  const m = re.exec(text);
  return m ? [m.index, m.index + m[0].length] : null;
}

function escape(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function formatValue(v: Value): string {
  if (v === null || v === undefined) return '';
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  return v;
}

/** Parse what a reviewer typed back into the field's shape. */
export function parseValue(field: string, text: string, original: Value): Value {
  const t = text.trim();
  if (field === 'continuing_action' || typeof original === 'boolean') {
    return /^(y|yes|true|1)$/i.test(t);
  }
  if (field === 'bases' || field === 'issues' || Array.isArray(original)) {
    return t ? t.split(',').map((s) => s.trim()).filter(Boolean) : [];
  }
  return t ? t : null;
}

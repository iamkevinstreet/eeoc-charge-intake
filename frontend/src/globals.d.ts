// ########################################################################
// #                      frontend/src/globals.d.ts                       #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Declares the globals every module may use without an import: the
 * trace logger, the settings the build writes in from config/config.toml
 * (read only through src/config.ts), and the one build variable the app
 * reads, VITE_API_BASE.
 */

// ########################################################################
// #                         Global declarations                          #
// ########################################################################
declare const log: { debug(message: string): void };

declare const __CONFIG__: {
  api: { prefix: string; request_id_header: string; port: number };
  demo: { provider: string };
  extract: { response_days: number };
  labels: {
    yes: string;
    no: string;
    join: string;
    fields: Record<string, string>;
    kinds: Record<string, string>;
  };
  record: {
    notice_field: string;
    summary_field: string;
    yes_no_field: string;
    list_fields: string[];
  };
  scores: { false_abstentions: string; guesses: string; field_prefix: string };
  ui: {
    code_url: string;
    generate_command: string;
    smoke_command: string;
    upload_key: string;
    note_class: string;
    keys: { next: string; previous: string; accept: string; edit: string; reject: string };
  };
  units: { ms_per_second: number; percent: number };
};

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
}

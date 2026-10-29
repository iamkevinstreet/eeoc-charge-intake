// ########################################################################
// #                       frontend/vite.config.ts                        #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * Build, dev-server and test settings: React, the dev server's proxy to
 * the API, and jsdom for tests. It reads config/config.toml, the file
 * the backend reads too, and writes only the keys the review screen
 * needs into the app as __CONFIG__; nothing from config/.env reaches the
 * browser. The proxy sends the API prefix to the host and port the
 * backend listens on, from the same file.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Standard library
import { readFileSync } from 'node:fs';

// Third-party
import react from '@vitejs/plugin-react';
import { parse } from 'smol-toml';
import { defineConfig } from 'vitest/config';

// Local
import { required } from './src/lib/required.ts';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Sets where the settings file is, from this folder')
const CONFIG_FILE = new URL('../config/config.toml', import.meta.url);
// log.debug('Names the table that holds the API settings')
const API = 'api';
// log.debug('Lists the keys of each table the review screen needs, and only those')
const BROWSER_KEYS: Readonly<Record<string, readonly string[]>> = {
  [API]: ['prefix', 'request_id_header', 'port'],
  demo: ['provider'],
  extract: ['response_days'],
  labels: ['yes', 'no', 'join', 'fields', 'kinds'],
  record: ['notice_field', 'summary_field', 'yes_no_field', 'list_fields'],
  scores: ['false_abstentions', 'guesses', 'field_prefix'],
  ui: ['code_url', 'generate_command', 'smoke_command', 'upload_key', 'note_class', 'keys'],
  units: ['ms_per_second', 'percent'],
};

// ########################################################################
// #                            Build settings                            #
// ########################################################################
/** The settings file's tables, as parsed: each a table of values by key. */
type Tables = Readonly<Record<string, Readonly<Record<string, unknown>> | undefined>>;

// log.debug('Defines how the settings the browser needs are taken from the file')
/**
 * Returns the tables and keys the review screen needs from the settings.
 *
 * @param tables - The settings file's tables, as parsed. Required.
 * @returns Each table the review screen needs, holding only the keys it
 *   needs.
 */
function browserConfig(tables: Tables | null = null): Record<string, Record<string, unknown>> {
  // log.debug('Takes the tables, which the caller must give')
  tables = required({ tables });
  // log.debug('Returns each table the review screen needs with only its keys')
  return Object.fromEntries(
    Object.entries(BROWSER_KEYS).map(([table, keys]) => [
      table,
      Object.fromEntries(keys.map((key) => [key, valueOf(tables, table, key)])),
    ]),
  );
}

// log.debug('Defines how one value is read, refusing a missing one')
/**
 * Returns one value from the parsed settings file.
 *
 * @param tables - The file's tables, as parsed. Required.
 * @param table - The table the value is in. Required.
 * @param key - The value's key in that table. Required.
 * @returns The value.
 * @throws {Error} When the file lacks the table or the key.
 */
function valueOf(
  tables: Tables | null = null,
  table: string | null = null,
  key: string | null = null,
): unknown {
  // log.debug('Takes the tables, which the caller must give')
  tables = required({ tables });
  // log.debug('Takes the table name, which the caller must give')
  table = required({ table });
  // log.debug('Takes the key, which the caller must give')
  key = required({ key });
  // log.debug('Reads the value, if the table and key are there')
  const value = tables[table]?.[key];
  // log.debug('Stops the build when the file lacks a value it needs')
  if (value === undefined) {
    // log.debug('Throws, naming the missing table and key')
    throw new Error(`config/config.toml lacks [${table}] ${key}, which the review screen needs`);
  }
  // log.debug('Returns the value')
  return value;
}

// log.debug('Reads the settings file into its tables')
const tables = parse(readFileSync(CONFIG_FILE, 'utf8')) as Tables;
// log.debug('Takes the API prefix, the path the dev server proxies')
const prefix = String(valueOf(tables, API, 'prefix'));
// log.debug('Takes the host the backend listens on')
const apiHost = String(valueOf(tables, API, 'host'));
// log.debug('Takes the port the backend listens on')
const apiPort = String(valueOf(tables, API, 'port'));

// log.debug('Exports the build, dev-server and test settings')
export default defineConfig({
  plugins: [react()],
  define: { __CONFIG__: JSON.stringify(browserConfig(tables)) },
  server: {
    port: 5173,
    strictPort: true,
    proxy: { [prefix]: { target: `http://${apiHost}:${apiPort}`, changeOrigin: false } },
  },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
  },
});

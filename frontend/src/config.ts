// ########################################################################
// #                        frontend/src/config.ts                        #
// ########################################################################
/**
 * Author:            Kevin Street
 * Created on:        2026-10-29
 * Last modified on:  2026-10-29
 *
 * The review screen's config module, the only one that reads the
 * build's settings: the keys the browser needs from config/config.toml,
 * which vite.config.ts writes into the app when it is built, frozen as
 * CONFIG. They are the same keys the backend reads, so the two cannot
 * drift. VITE_API_BASE may point the app at another API address; by
 * default it calls the API prefix on its own origin, which the dev
 * server proxies to the backend.
 */

// ########################################################################
// #                               Imports                                #
// ########################################################################
// Local
import { required } from './lib/required';

// ########################################################################
// #                           Local constants                            #
// ########################################################################
// log.debug('Takes the settings the build read from config/config.toml')
const BUILT = __CONFIG__;
// log.debug('Takes the API address: VITE_API_BASE when set, else the prefix on this origin')
const API_BASE: string = import.meta.env.VITE_API_BASE ?? BUILT.api.prefix;
// log.debug('Exports the settings, frozen all the way down so no module can change them')
export const CONFIG = freeze({ ...BUILT, api: { ...BUILT.api, base: API_BASE } });

// ########################################################################
// #                          Frontend settings                           #
// ########################################################################
/** A value no module can change, with every table and list inside it. */
type Frozen<T> = { readonly [K in keyof T]: Frozen<T[K]> };

// log.debug('Defines how a table is frozen with every table and list inside it')
/**
 * Returns a table frozen all the way down, so no module can change it.
 *
 * @param table - The settings, or a table or list inside them. Required.
 * @returns The same table, frozen with every table and list inside it.
 */
function freeze<T extends object>(table: T | null = null): Frozen<T> {
  // log.debug('Takes the table, which the caller must give')
  table = required({ table });
  // log.debug('Walks the values the table holds')
  for (const value of Object.values(table) as unknown[]) {
    // log.debug('Freezes a value that is itself a table or a list')
    if (typeof value === 'object' && value !== null) {
      // log.debug('Freezes it, with everything inside it')
      freeze(value);
    }
  }
  // log.debug('Returns the table, frozen')
  return Object.freeze(table);
}

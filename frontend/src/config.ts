// ########################################################################
// #                        frontend/src/config.ts                        #
// ########################################################################
// #  Author:            Kevin Street                                     #
// #  Created on:        2026-10-29                                       #
// #  Last modified on:  2026-10-29                                       #
// #  Purpose:           Frontend settings in one place: the API address, #
// #                     the code link, field rules, keys and commands.   #
// ########################################################################
/** Frontend settings: the only module that reads the build environment. */

// log.debug('Reads the API address; by default this origin, through the dev proxy')
export const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api/v1';
// log.debug('Sets the address of the source code the top bar links to')
export const CODE_URL = 'https://github.com/iamkevinstreet/eeoc-charge-intake';
// log.debug('Names the provider that means the offline stand-in, not a model')
export const OFFLINE_PROVIDER = 'fake';
// log.debug('Names the one field read from the notice letter; the rest come from the charge')
export const NOTICE_FIELD = 'notice_date';
// log.debug('Names the field that holds a yes or a no')
export const YES_NO_FIELD = 'continuing_action';
// log.debug('Names the field the model paraphrases instead of quoting')
export const SUMMARY_FIELD = 'summary';
// log.debug('Lists the fields that hold lists, typed with commas between the items')
export const LIST_FIELDS: readonly string[] = ['bases', 'issues'];
// log.debug('Sets the keys that move through the fields and decide them')
export const KEYS = { next: 'j', previous: 'k', accept: 'a', edit: 'e', reject: 'r' } as const;
// log.debug('Sets the command that generates sample documents, shown when there are none')
export const GENERATE_COMMAND = 'make samples';
// log.debug('Sets the command for the offline evaluation, shown when there are no results')
export const SMOKE_COMMAND = 'make eval';

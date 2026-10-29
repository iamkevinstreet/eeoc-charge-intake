# frontend

The review screen for EEOC charge intake, in React and TypeScript with Vite. A reviewer opens a
generated sample, or uploads a charge form and its notice letter, and sees the extracted record
beside the document text. Each of the eleven fields shows its value, the quoted evidence, the page
and the model's confidence, and the quote is marked in the document. The reviewer accepts, edits or
rejects every field, and the export stays off until each one has a decision.

In development the app proxies `/api` to the service on port 8000, so start the backend first (the
README at the repository root says how). The client calls the routes under `/api/v1`. Use Node 24,
as `.nvmrc` says.

```sh
npm ci                # the locked dependencies
npm run dev           # http://localhost:5173
npm run lint          # ESLint (typescript-eslint strict, with types) and Stylelint
npm run format:check  # Prettier
npm run typecheck     # tsc
npm test              # 11 tests with Vitest and Testing Library
npm run build         # the production build, in dist/
```

## Screens

| Screen | What it shows |
| --- | --- |
| Start | What the service does; the generated samples, each with its kind of case and a button to review it; the upload form for a charge form and its notice letter, which turns on once a model is set |
| Review | The record on the left: each field's value, quoted evidence, page, confidence and decision. The document on the right, charge or notice, with the quote marked. Keys: j and k move, a accepts, e edits, r rejects. Once every field has a decision, Export record shows the record as JSON to download or copy |
| Evaluation | The latest evaluation run: field accuracy, unsupported outputs removed, false abstentions, guesses, latency and cost; accuracy by field; the same numbers by kind of case |

In demo mode (`LLM_PROVIDER=fake`) the answers come from the known answers of the generated
documents, so every screen works without an API key; uploads need a model.

## Conventions

- Every file carries the header box, and a logger line above every statement:
  `// log.debug('Opens the menu')`, printed as HH:MM:SS traces by `src/log.ts` when switched on.
- Settings live in `src/config.ts`, the only module that reads the build environment
  (`VITE_API_BASE`, default `/api/v1`). A value used more than once in a module is a named
  constant at the top of that module.
- Class names carry the `ec-` prefix; colours come from the tokens in `src/styles/tokens.css`,
  each written once with `light-dark()`. The styles are split by screen in `src/styles/`, and no
  file runs past 500 lines.
- The three decision colours mean the same everywhere: green for accepted, amber for edited, red
  for rejected. Words go with every colour.
- The review screen takes its two calls as a prop (`ReviewApi`), so the same screen can run on
  fixtures.
- The tests stub `fetch`; they never reach the network.

# Security

## Reporting a vulnerability

Please report it privately, never in a public issue:

- **Preferred:** GitHub's private vulnerability reporting (the repository's **Security** tab, then
  **Report a vulnerability**).
- **Otherwise:** email info@kevindstreet.com with "Security" in the subject.

Include what you found, how to reproduce it, and what an attacker could do with it. You will get an
answer within 3 business days. A confirmed issue is fixed within 30 days, sooner when severe, and you
are credited in the advisory unless you would rather not be.

## Scope

In scope: the review service in `backend/`, the review screen in `frontend/`, the workflows in
`.github/`, and above all any way to show a reviewer a value whose quote is not on the page it
cites, to export a record before every field is decided, or to read a file through the service.

Out of scope: the model providers' own services, the made-up documents and results in `data/`, the
dashboard and the service on your own machine (they have no sign-in by design and only listen
there), and findings that need a compromised developer machine.

This is a prototype. It is built to the controls below, but it is not hardened for the open internet:
see "Unresolved" in the [README](README.md) before running it anywhere shared.

## How this repository is protected

| Risk | Control |
| --- | --- |
| A value the document does not support reaches a reviewer | Every quote is checked against the page it cites; a field whose quote is not there is emptied, with the reason, before any response |
| A record exported before review | The export answers 409 until every field has a decision; a rejected field exports empty |
| A malicious upload | Uploads are limited in size, by the declared length and again per file; each must start like a PDF; they are written under fixed names to a temporary folder that is deleted after; an uploaded file's name is never used as a path |
| Reading files through the service | Samples are looked up by id in the generated set, and ids and review ids must match fixed patterns; no route takes a path |
| A server reachable by others | Neither the service nor the dashboard has sign-in, so the settings refuse any address but this machine's for both |
| DNS rebinding to a local server | Requests addressed to any host name not in `[api] allowed_hosts` are refused |
| Abuse of the model | A per-client limit on extractions, a budget per process, a size limit on every request body, and a body that does not declare its length is refused |
| The review screen in a browser | A content security policy that allows only the service's own files, no framing, no MIME sniffing and no referrer |
| Personal data in logs | Document text is never logged; `kds.logs` redacts emails, phone numbers and ID-like numbers from everything that is |
| A committed secret | gitleaks before every commit and over the whole history in CI; secrets live only in `.env`, and the settings loader refuses one in `config/settings.toml` |
| A vulnerable dependency | Lockfiles with hashes, `pip-audit` and `npm audit` in CI, Dependabot every week |
| A tampered Action or tool | Actions pinned to commit SHAs; the gitleaks download checked against its published SHA-256 |
| A flaw in the code | CodeQL for Python and TypeScript, ruff's security rules (bandit), least-privilege workflow permissions |

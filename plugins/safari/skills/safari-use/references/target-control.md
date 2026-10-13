# Task-bound commands

`safari_target.sh` uses native macOS JXA and Safari Apple Events. It never selects
a tab or requests that Safari come forward. Opening a document can still change
focus; obtain authorization required by the host before creation. Safari must
already be running with JavaScript from Apple Events and Automation permission.

Use a fresh target-file path with an existing parent. Initialization refuses to
overwrite a handle. Symlinks are rejected, writes are atomic, and a per-handle
directory lock refuses concurrent use without polling. After a crash, a leftover
lock means busy: ensure no controller still runs before removing that exact lock.
Do not erase pending outcomes as lock recovery.

## Create or bind

```sh
./scripts/safari_target.sh open --target-file ./reader.json \
  --url https://example.com --recover-readonly --recovery-limit 1
```

Only enable `--recover-readonly` for a disposable reading/search URL that can be
reloaded within existing authority. Do not enable it for unsaved local state,
drafts, uploads, transactions or reads of unsaved text. The default budget is one
replacement (0..3 allowed); keep the same file so retries cannot reset it.
Recovery opens a new dedicated window; it never navigates or closes the old one.

For an explicitly authorized existing tab, inspect a fresh live listing and
relevant page before binding:

```sh
./scripts/safari_target.sh bind --target-file ./work.json \
  --window-id 123 --tab-index 2 --expect-url https://example.com
```

An initial index is not a lasting identifier. Initial binding can race; URL
equality is not physical identity. Do not bind a materially ambiguous same-URL
candidate. Later account/object/value guards establish the operation's context.
`bind` cannot enable automatic reconstruction.

`open` records creation intent before the event. If the page is loading, later
`inspect` can finish initial marker installation in the sole tab of the recorded
new window. It does not repair a lost established marker. Unknown creation is
never automatically repeated: reconcile observed native state before deciding
on new creation.

## Observe and act

```sh
./scripts/safari_target.sh inspect --target-file ./reader.json
./scripts/safari_target.sh eval --target-file ./reader.json \
  --js-file ./read.js --guard-file ./guard.js --effect read
```

Files contain synchronous function bodies with explicit `return` statements.
Example guard:

```js
return document.querySelector('h1')?.textContent.trim() === 'Expected article';
```

Example read:

```js
return {title: document.title, text: document.querySelector('article')?.innerText};
```

Guards must be read-only and return exactly `true`. Check account, object,
version and affected fields where material, not whole-page equality that rejects
unrelated edits. Marker, exact URL, guard and body are checked/executed in one
page call. `--effect read` is a caller contract, not a sandbox: never label a
mutating payload or guard as a read. Promise/async results are unsupported.

For one authorized synchronous mutation, use `--effect write`. The pending ID
is durably recorded before dispatch. A normal return does not prove an
asynchronous service effect. Observe the result, then:

```sh
./scripts/safari_target.sh resolve --target-file ./work.json \
  --operation-id <recorded-id> --evidence 'Observed intended saved object and revision'
```

Evidence must be a real observed outcome, including confirmed nonexecution when
relevant, not an elapsed timeout or desired result. Do not retry an uncertain
write until its effect or established repeat safety is known. Resolution records
agent judgment; it does not independently validate service state.

## Recovery and results

Expected same-document navigation may retain the marker while changing the URL.
After observing a destination consistent with the authorized navigation, verify
its account/object/page context before updating the expected URL:

```sh
./scripts/safari_target.sh transition --target-file ./work.json \
  --expect-url https://example.com/expected-destination --guard-file ./guard.js
```

The exact URL and guard are checked with the existing marker in one page call.
`transitioned` means the expectation was updated, not a new tab was identified.
It preserves pending effects, the budget and the original recovery recipe. It
does not repair marker loss or permit an unexpected/unauthorized destination.
Recovery still starts from the original disposable checkpoint; re-establish any
later workflow/page expectations before continuing dependent work.

```sh
./scripts/safari_target.sh recover --target-file ./reader.json
```

- `bound` / `ready` / `ok`: initial binding, reconciled binding, synchronous
  payload return. Only `ok` means the payload was dispatched successfully.
- `replaced`: new authorized reader, incremented generation and budget.
- `binding-mismatch` / `context-mismatch` / `guard-failed` / `guard-error`:
  payload did not run. Re-observe; do not silently relax checks. Navigation
  retaining a marker is a mismatch, not automatic recreation.
- `missing`: no matching marker in the tracked window. Only an authorized
  disposable context can be reconstructed automatically.
- `loading` / `unreadable` / `unbound` / `ambiguous`: no safe dispatch.
  Do not treat these as missing. Duplicate marked candidates are ambiguous.
- `pending-outcome` / `outcome-unknown` / `operation-error` /
  `async-result-unsupported`: inspect durable pending state and actual effects.
  No write replay or reconstruction; independent reads remain available.
- `creation-outcome-unknown`: creation may have happened; do not replay it.
- `recovery-not-authorized` / `recovery-exhausted` / `busy`: yield on this
  handle, not on all unrelated authorized work.

The CLI can exit successfully with a non-ok JSON status. Inspect `status` and
`dispatched`, not just exit code.

## Limits and cleanup

Markers are page-local heuristics, not native Safari IDs, authenticated ownership
or browser-wide exclusion. Navigation can erase them; scripts and duplicates can
copy them. A copied marker after its original disappears may be indistinguishable.
Essential operation-context differences require independent observation. Same-call
guards reduce stale-address mistakes; they do not prove browser-wide atomicity,
unobservable tab identity or service-side idempotency.

Created window IDs are cleanup candidates, not unconditional close permission.
List current tabs and recheck purpose/content first. Preserve moved, repurposed,
uncertain or human-edited content; briefly report genuinely unclosed task targets.
Ignore unrelated zero-tab remnants.

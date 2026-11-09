# Task-bound commands

`safari_target.sh` uses native macOS JXA and Safari Apple Events. It never selects
a tab or requests that Safari come forward. Opening a document can still change
focus; obtain authorization required by the host before creation. Safari must
already be running with JavaScript from Apple Events and Automation permission.

For a genuinely new logical context, use a fresh target-file path with an existing
parent. Reuse the original handle for an established task context, including
after setup errors. Initialization refuses to
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
This opt-in permits bounded new-window recovery only when `recover` also receives
`--allow-new-window`. Default recovery creates nothing. Check verified existing
task contexts first; new handles must not reset budgets or bypass unknown actions.

For an existing tab within the user's authorized scope, inspect a fresh live
listing and relevant page before initial binding. If it already belongs to this
task, use its original handle instead:

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
new window. It does not repair a lost established marker. Initial `about:blank`
is treated as navigation still starting, not a foreign destination. Other
unexpected pages remain mismatches. Extra tabs leave the known new window ID
intact but require explicit verified `reuse`; they do not make creation unknown.
Unknown creation is never repeated: reconcile observed native state before
deciding on new creation. Saved stages, candidate IDs and sanitized reasons help
diagnosis without recording raw errors.

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

Prefer the same tracked window after reload or marker loss:

```sh
./scripts/safari_target.sh recover --target-file ./reader.json --guard-file ./work-state.js
```

This requires one exact-URL candidate and a read-only guard proving its task
context and work state. A URL, title, window ID or empty composer alone is not
ownership. Preserve active reviews, drafts, uploads and unread results. If the
context is repurposed, do not overwrite it or switch to another agent's context.
Use another established task context only through its original handle and fresh
verification. Busy contexts can wait while independent work proceeds.

For explicit reuse, including verified stateful context or a known setup window
with extra tabs, supply a freshly observed address and exact URL:

```sh
./scripts/safari_target.sh reuse --target-file ./work.json \
  --tab-index 2 --expect-url https://example.com/saved-object --guard-file ./work-state.js
```

`reuse` is restricted to this handle's recorded window; it will not abandon a
still-present marked target for a neighboring tab, replace another marker or
pick among multiple unmarked same-URL candidates. It checks URL, readiness,
marker availability and the guard in the reached page call. It changes only
binding metadata, never navigation, drafts or the business action. Keep guards
read-only. Retained markers keep their generation; a newly installed marker
increments it. The pending record, its original dispatch context and the saved
recovery budget remain intact. Pending actions still block writes and `recover`;
explicit reuse can restore independent reads, not clear replay for the old action.

A lost reuse reply yields `binding-outcome-unknown`. Inspect the same handle:
an installed token can reconcile to `ready`; absent tokens stay `unbound` until
fresh explicit reuse verification. Inspection never restamps that reuse intent.

Only when an additional disposable reader is actually needed and no suitable
existing task context is available:

```sh
./scripts/safari_target.sh recover --target-file ./reader.json --allow-new-window
```

This also requires saved reader opt-in, remaining budget and no pending action.
It never navigates or closes the old page. The option is an explicit execution
choice, not a grant of broader task authority. A budget limit is not a reason
to ask for repeated time/approval allocations or to start a fresh handle.

- `bound` / `ready` / `ok`: initial binding, reconciled binding, synchronous
  payload return. Only `ok` means the payload was dispatched successfully.
- `reused`: verified existing context; no business payload dispatched.
- `replaced`: new authorized reader, incremented generation and consumed budget.
- `binding-mismatch` / `context-mismatch` / `guard-failed` / `guard-error`:
  payload did not run. Re-observe; do not silently relax checks. Navigation
  retaining a marker is a mismatch, not automatic recreation.
- `missing`: no matching marker in the tracked window; not proof of closure.
- `reuse-required`: inspect existing task contexts before explicit new creation.
- `outside-task-window` / `target-still-present` / `already-bound`: no takeover;
  use the original handle/address or reconcile the ownership conflict.
- `loading` / `unreadable` / `unbound` / `ambiguous`: no safe dispatch.
  Do not treat these as missing. Duplicate marked candidates are ambiguous.
- `pending-outcome` / `outcome-unknown` / `operation-error` /
  `async-result-unsupported`: inspect durable pending state and actual effects.
  No write replay or reconstruction; independent reads remain available.
- `creation-outcome-unknown`: creation may have happened; do not replay it or
  escape it with a new handle. Inspect saved stages and candidate window IDs.
- `binding-outcome-unknown`: inspect persisted binding intent; no business action
  was requested. Do not confuse it with an unknown submission outcome.
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

---
name: safari-use
description: Operate Safari's existing session through Apple Events and guarded in-page JavaScript. Use for Safari-native page inspection and actions with a task-bound window/tab handle, including recovery under shared browser use.
---

# Safari

Assume the person and other agents are using Safari concurrently. A selected tab,
front window, remembered index, URL or title is not ownership. Use explicit
`window id` targeting with the task handle below; never restore focus to repair
targeting. A dedicated Safari window is the default. Reuse an existing window
only when the user explicitly asks. Do not intentionally bring Safari forward
without approval; window creation itself may change focus, so respect the host's
browser-control rules and required authorization.

## Task-bound control

Use `scripts/safari_target.sh`, backed by native macOS JXA and Safari's
`do JavaScript`. It requires no extension or extra runtime. Read
[target-control.md](references/target-control.md) before the first use for the
commands, function-body format and result handling.

- Record one logical target in a task-local `--target-file`. The helper records
  its window ID, page-local marker, binding generation and optional recovery
  budget. This is not a native tab ID: markers can disappear or be copied.
- Resolve the marked tab afresh inside the tracked window. Tab indexes are
  temporary dispatch addresses, never identity. Normal selection changes,
  reordering and unrelated tab churn need no approval or focus restoration.
- Check the actual reached page's marker, expected URL and operation-specific
  predicate inside the same JavaScript call as the payload. For writes, check
  the intended account/object and affected values where material. A matching
  URL alone is insufficient. Preserve human edits; unrelated changes need not
  block the action.
- Follow observe → act → observe. One payload does one intended synchronous
  operation. Verify its actual result before claiming completion.
- For ordinary disposable reading/search only, explicitly enable bounded
  recovery at `open`. If the marked target disappears, `recover` can create a
  new dedicated reader from its checkpoint without moving or overwriting the
  old tab. A replacement is new, not proof the original tab survived. Repeated
  loss exhausts the saved budget and yields; never start an endless contest.
- A moved tab is outside the original window's binding. This first version
  does not follow it into another existing window. Reconstruct an authorized
  disposable context or stop only the affected stateful action.
- After navigation/reload, re-observe. Do not repair a lost established marker
  by writing the desired marker and immediately acting. Saved-object rebinding,
  unsaved drafts and uploads require their material context/state to be verified;
  this version does not automatically rebind them. Do not silently broaden a
  guard's URL or erase a conflicting value to make it pass.
- For an expected same-document navigation that retains its marker, use
  `transition` with the exact observed authorized URL and a read-only context
  guard. This explicit verification updates the expected URL; it does not clear
  pending effects or grant authority for an unexpected destination.
- Loading, unreadable or ambiguous results are not evidence of closure. Diagnose
  briefly; do not reload away sensitive local state or automatically reconstruct
  an unreadable target. Continue independent authorized work when possible.
- A write's pending operation is stored before dispatch, separately from the
  tab binding. Even an `ok` JavaScript return needs effect verification. Resolve
  the recorded operation only with observed outcome evidence. An uncertain
  result survives restart and blocks write replay and automatic reconstruction;
  independent reads can continue. The local file lock coordinates this handle,
  not the person or tools that bypass it.

## Other helpers

- `safari_list_windows.sh`: JSON window IDs, tab indexes, URLs and titles;
  omits Safari's empty window objects by default. `--current-only` limits
  inspection; `--include-empty` is diagnostic only. Ignore unrelated empty objects.
- `safari_close_window.sh --window-id <id>`: use only after fresh inspection
  confirms the entire window is still task-created and safe to close. It reports
  `closed`, `already_absent`, `window_still_open` or `close_error`; an empty remnant is normalized to `closed`.
  Never close ambiguous or repurposed content.
- `safari_eval_js_window.sh` and `safari_click_visible_text.sh` retain their old
  current-tab behavior for compatibility. They are **not shared-tab-safe** and
  must not be the execution path for a task-bound operation. For visible-text
  actions through the guarded helper, inspect the DOM and require one uniquely
  best visible match before clicking; tied matches must produce no click.

Do not bypass missing permissions, inaccessible frames, native prompts or file
selection with a weaker target. Use an authorized native/UI path when necessary;
do not fight for focus or blindly dismiss dialogs. Safari cookies stay in Safari.
Do not persist credentials, authentication URLs or sensitive DOM contents in the
handle or outcome evidence. Keep reports concise and sanitized.

## Advisory Tab Group inspection

For a task that specifically needs named Tab Groups, read
[tab-groups.md](references/tab-groups.md). The private database is identification
evidence only, never a live dispatch address or tab-ownership source.

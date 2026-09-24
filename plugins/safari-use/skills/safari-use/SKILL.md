---
name: safari-use
description: Automate Safari via AppleScript/sdef plus in-page JavaScript executed with `do JavaScript`. Use when users explicitly want Safari-native automation, especially when they need existing Safari sessions/cookies, explicit window-id targeting with per-window tab inspection and current-tab execution, sidebar/menu actions, pseudo-snapshots of visible UI text, or stepwise observe→act→observe workflows.
---

# Safari Use

Use these helpers for reliable Safari-native automation (AppleScript/sdef + `do JavaScript`), with explicit `window id` targeting so multiple Safari windows can be operated independently at the window level. By default, create and use a dedicated Safari window for the task, and keep all later operations pinned to that `window id`. Reuse an existing Safari window only when the user explicitly asks to operate that existing window. Do not intentionally activate or front Safari unless the user explicitly asks; if a step appears to require stealing focus, stop and ask before proceeding.

## Helpers (`scripts/`)

### 1) `safari_list_windows.sh`
List Safari windows/tabs as JSON.

```bash
./scripts/safari_list_windows.sh
./scripts/safari_list_windows.sh --current-only
```

Returns per-window:
- `index`, `id`, `tab_count`, `current_tab_index`
- tab entries with `index`, `current`, `url`, `title`
- `tab_count` may be `0`; this helper remains valid for real Safari 0-tab windows and is the canonical way to inspect them.

---

### 2) `safari_eval_js_window.sh`
Run JS in `current tab` of a specific Safari `window id`.

```bash
./scripts/safari_eval_js_window.sh --window-id 123 --js-file /tmp/probe.js
./scripts/safari_eval_js_window.sh --window-id 123 --js 'location.href'
```

Preferred pattern (quote-safe): write JS to file, then run with `--js-file`.

- Requires the target window to have at least one tab. If `tab_count` is `0`, this helper fails clearly; use `safari_list_windows.sh` to inspect that state instead of treating it as a generic JS failure.

---

### 3) `safari_click_visible_text.sh`
Convenience click helper: finds the best **visible** element by text and clicks it.

```bash
./scripts/safari_click_visible_text.sh --window-id 123 --text "Continue"
./scripts/safari_click_visible_text.sh --window-id 123 --text "Continue" --exact
```

Behavior:
- scans common interactive elements (`a`, `button`, `[role=button]`, etc.)
- filters by visibility (`display`, `visibility`, `opacity`, bounds)
- chooses best text match and returns JSON result

---

### 4) `safari_close_window.sh`
Attempt to close a specific Safari `window id` and report the resulting state as JSON.

```bash
./scripts/safari_close_window.sh --window-id 123
```

Behavior:
- closes the targeted Safari window without assuming it disappears immediately
- distinguishes `already_absent`, `closed`, `empty_window_persisted`, `window_still_open`, and `close_error`
- treats Safari's real **0-tab window** state as an explicit cleanup blocker; if the result is `empty_window_persisted`, report that as the canonical blocker under current non-focus-stealing constraints instead of silently retrying or claiming success

---

### 5) Read-only Tab Group inspection via `SafariTabs.db`

Safari's AppleScript dictionary does not expose Tab Group names or whether a window is currently showing a named Tab Group. For read-only identification only, Safari keeps private tab metadata in:

```bash
~/Library/Containers/com.apple.Safari/Data/Library/Safari/SafariTabs.db
```

Use this database only as advisory state:

- **Never modify it.** Do not run `UPDATE`, `INSERT`, `DELETE`, `VACUUM`, schema changes, or any script that writes to this file, its WAL, or its SHM files.
- Treat it as **potentially stale or not a real-time representation** of the visible Safari UI. It can lag current windows, include session/restoration state, and use a private schema that may change across Safari/macOS versions.
- Always cross-check against a live `safari_list_windows.sh` snapshot before reporting or acting.

Tab Group identification pattern:

1. Capture live windows with `safari_list_windows.sh`.
2. Query `SafariTabs.db` read-only, preferably by opening SQLite in read-only mode. Relevant fields:
   - `windows.active_tab_group_id`
   - `windows.local_tab_group_id`
   - `bookmarks.title` joined from `active_tab_group_id`
   - optionally `windows_tab_groups.active_tab_id` joined to `bookmarks` for the active tab URL/title inside the group
3. Interpret:
   - `active_tab_group_id == local_tab_group_id` or group title `Local` → ordinary local tabs.
   - `active_tab_group_id != local_tab_group_id` and group title is not `Local`/`Private` → a named Tab Group is active in that window.
   - Treat `Local`/`Private` as private-schema/UI-derived labels, not stable public API values.
4. Map DB windows back to live Safari windows by exact active tab URL/title, tab count, and URL overlap. If the match is ambiguous or low-confidence, report uncertainty instead of claiming a definitive Tab Group/window mapping.
5. Use the DB for identification only. Any tab moves/closes still go through Safari AppleScript/window-id operations and must be verified with a fresh `safari_list_windows.sh` snapshot.

## Standard workflow (observe → act → observe)

1. If the user did not explicitly ask to reuse an existing Safari window, create a new Safari window for the task. Then enumerate windows/tabs, record the new target `window id` (`safari_list_windows.sh`), and keep all later operations pinned to that `window id` rather than whichever Safari window is frontmost.
2. Observe state with a JS probe (`safari_eval_js_window.sh` + JSON.stringify in JS) when the target window has at least one tab; if `tab_count` is `0`, use `safari_list_windows.sh` and treat that state explicitly.
3. Perform one action (`safari_click_visible_text.sh` or custom JS).
4. Re-probe and verify concrete state change.
5. When cleaning up a dedicated Safari window, use `safari_close_window.sh` and inspect its classification instead of assuming `close` removed the window; if it returns `empty_window_persisted`, stop and report the canonical cleanup blocker.

## Guardrails

- Use `window id`, never assume the frontmost or active Safari window.
- Explicit `window id` targeting is what allows multiple Safari windows to be operated independently.
- A dedicated Safari window is the default. Reuse an existing Safari window only when the user explicitly asks.
- If page-local state in another Safari window/tab seems necessary, stop and ask the user before reusing it.
- Do not intentionally `activate` Safari, bring it to front, or steal focus unless the user explicitly asks.
- If any step appears to require Safari to become frontmost or to steal focus, stop and ask the user before proceeding.
- Safari may keep a real 0-tab window alive after closing the last tab or window. `safari_list_windows.sh` can still inspect that window, but `safari_eval_js_window.sh` cannot run in it. No verified non-focus-stealing method currently exists to fully remove that window, so treat `empty_window_persisted` from `safari_close_window.sh` as the canonical cleanup blocker and report it explicitly.
- Prefer JS temp files (`/tmp/*.js`) over long inline snippets to avoid quoting failures.
- Keep outputs structured (JSON) and evidence-based (`url`, `title`, changed state).
- Avoid printing sensitive data from page context.

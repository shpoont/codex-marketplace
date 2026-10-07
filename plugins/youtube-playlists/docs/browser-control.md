# Agent browser-access requirements

This is a reference for the agent operating the plugin and for maintainers
integrating a controller. It is not a browser-tool installation guide. Use an
available capable controller; the user or host owns browser-tool choice and
installation. Do not prescribe a particular browser plugin or install one.
Tell the user about a concrete missing capability or the relevant permission
when it blocks their request. Keep the runner and bridge wiring below internal
to the agent's work.

The YouTube implementation is shared. It needs a runner that executes JavaScript
in the actual signed-in YouTube page, including `window.ytcfg.get` and `fetch`.
It verifies the configured account and playlist before operating. Merely having
a function called `evaluate` does not establish these capabilities.

Browser selection belongs to execution, not channel rules. Normal commands use
the built-in Safari controller. `--javascript-bridge /absolute/controller/path`
explicitly selects a controller supplied by a browser tool. It never silently
falls back to another browser or account. Existing `transport.browser: safari`
settings remain valid; new settings may omit that legacy hint.

## Check available access

Inspect the available browser tool's documented capabilities and verify execution
in the intended signed-in page. The controller must execute main-page JavaScript
with the page's session, preserve a stable page identity, transfer complete
results and verify cleanup of owned pages. A restricted evaluator or a tool name
alone is not sufficient. If none is available, report the missing execution
capability and stop browser-dependent work without recommending an installation
or silently substituting another browser.

## Controller-specific permissions

Use only the row that matches the actual control mechanism. Browser family alone
does not determine a tool's permission requirements.

| Browser/controller | Access the agent must verify |
| --- | --- |
| Built-in Safari controller on macOS | Signed-in YouTube session, macOS Automation access and Safari's **Allow JavaScript from Apple Events**. |
| Chrome through an available Browser Use CDP tool | **Settings > Browser > Developer mode > Enable full CDP access** in ChatGPT/Codex, plus any host-requested site access. This is separate from Chrome extension developer mode. |
| Another Chrome, Chromium, WebKit or other browser controller | The same execution, page identity, result transfer and cleanup capabilities, with any advanced permissions required by that tool. Consult its own guidance and verify actual access; do not assume compatibility from the browser family. |

The Browser Use permission is described in the
[official Browser documentation](https://learn.chatgpt.com/docs/browser#developer-mode).
The shared client does not require exported cookies, tokens or an API key.
If the selected controller lacks permission, explain the relevant permission
step to the user. The user enables it; do not change their settings implicitly.
A missing capability stops the command.

## Agent and maintainer integration: supplying a runner

Python integrations construct `YouTubeTransport(config, runner)` from
`youtube_playlist_manager.transport`. The runner contract is in
`youtube_playlist_manager.browser_control.JavaScriptRunner`:

- `open(url)` binds one requested page and exposes its opaque `page_id`.
- `evaluate(source, script_timeout=60)` executes once in that main page and
  returns the JSON decoded from the source's string result.
- `close()` verifies release of owned resources, preserving borrowed or changed
  pages and reporting cleanup failures.
- `can_recover` and `recover_read_only()` expose optional owned-page recovery.
  Only read collection uses it, at most twice. It never replays an edit.

The shared client owns YouTube initialization, account checks, collection,
metadata selection/cache coordination, job polling, playlist reads and edits.
A runner contains no YouTube endpoints or channel policy.

## Browser tools and the local bridge

The bundled `youtube_playlist_manager/browser/tool.js` exports
`createToolController`. Load it in the browser tool's JavaScript runtime using
that tool's documented file/module access. Use a fresh private directory under
the external application data root. Supply only the tool's documented primitives:

```js
const controller = await createToolController({
  directory: freshPrivateDirectory,
  createPage: url => toolCreatePageWithURL(url),
  connectPage: page => toolGetCDPCapability(page), // returns {send}
  inspectPage: page => toolReadExactPageURL(page), // returns {url}
  closePage: page => toolCloseExactPage(page),
  isPagePresent: page => toolFreshExactIDPresence(page) // literal boolean
});
```

These names illustrate the callback contract, not real browser-tool methods.
Read the selected tool's documentation. When it supports URL-at-creation, use
the callbacks above. When it documents separate creation and navigation, supply:

```js
createPage: () => toolCreateEmptyPage(),
navigatePage: (page, url) => toolNavigateExactPage(page, url),
initialPageURL: 'about:blank' // use the tool's documented empty-page URL
```

These are also illustrative callbacks. The controller saves the exact created
handle before inspecting, navigating or acquiring CDP. It verifies the empty-page
URL before its single navigation and checkpoints navigation intent/completion.
Do not navigate in `createPage` or infer a handle from inventory differences.
An unbound page can be cleaned up at its expected initial URL while navigation
is incomplete, or at the requested target. Returning to the initial URL after
completed navigation is a page change and is preserved. Native URL inspection
remains available when setup fails. This does not bypass a tool policy denial: stop
the affected action if the tool rejects access and retain any unresolved receipt.

`isPagePresent` must read fresh inventory and check the exact ID. Failed listing,
undefined or null is unknown, never absence. `inspectPage` reads that exact page's
URL without navigating it. A page changed by the user is preserved. After binding,
inspection uses the URL and page marker through CDP; loss of that identity fails
cleanup instead of falling back to weaker evidence.

1. Create the controller using the callbacks above.
2. Run the installed normal command with `--javascript-bridge DIRECTORY` before
   its command name and the existing account/target configuration.
3. Service `await controller.serveFor(1000)` or `serveOnce()` sequentially through
   the browser tool while the command is active. `serveFor` accepts 1–60000 ms;
   it finishes an in-flight request before returning, without cancelling or
   replaying browser actions. Set the host tool-call budget accordingly. Do not
   use background `fs.watch` callbacks, overlapping dispatches, nested pulses,
   controller resets or abort-and-retry loops. Do not load source payloads into
   the conversation or make per-video judgments.
4. After completion, require `owned_pages: 0` and verified cleanup. An opening
   failure reports an allowlisted stage (`create_page`, `register_page`,
   `inspect_page`, `navigate_page`, `connect_page`, `bind_page`) and ownership
   (`registered`, `unknown`). Its
   receipt retains that first failure separately from later cleanup failure.
   Unknown creation stays unresolved; zero registered handles does not prove no
   physical tab exists. Never repeat creation or infer ownership to solve this.
5. Stop servicing after verified cleanup. Remove the temporary bridge directory
   when no longer needed; keep unresolved receipts for recovery. It contains
   scripts and normalized data, not exported credentials.

Lower-level integrations may use `controller.js`'s
`createController({directory, openPage})` with a page implementing `id`,
`bind(url, token, {ensureActive, checkpoint})`, `evaluate(source, seconds, ensureActive)`, `inspect()`, `close()`
and `isPresent()`. Return the handle immediately after creation; move subsequent
connection/navigation work into `bind`, after ownership is recorded. Cleanup
belongs to the controller, not a catch block that might overwrite the first
error. Optional `initialURL`, `navigationStarted` and `navigationCompleted` page
fields expose the two-step lifecycle for receipts and cleanup. Checkpoint after
changing a setup phase; check request activity before each subsequent action.
`createCDPPage({id, send, close, isPresent, event})` supplies CDP binding,
inspection and bounded transfer. CDP is one connection option, not a dependency
of the shared YouTube client. Check request deadlines/abandonment between transfer
steps and use one decreasing evaluation budget. Never replay uncertain execution.

## Cleanup timing and reconciliation

The shared controller requests close once. An acknowledgement alone is not proof
that a tab disappeared: it polls fresh exact-page presence within one five-second
budget, including inspection and close calls. `cleanupOptions` can set an
integration-specific budget up to 30 seconds; this is controller wiring, not a
playlist policy setting. Every call is bounded. If the close acknowledgement is
lost but absence is verified, the receipt records `closed` with an uncertain
acknowledgement. Lost identity, invalid presence evidence, disconnection and an
exhausted budget fail cleanup instead of pretending that it succeeded.

The owned receipt records the lifecycle, whether close started, its acknowledgement,
the last failure and the final disposition. After an uncertain cleanup, continue
using the same controller and call `await controller.verifyCleanup()` to perform
read-only reconciliation. Python integrations can call `runner.verify_cleanup()`
after `close()` failed. These checks never repeat close, page evaluation or playlist
edits, and they do not reopen a page. They may resolve absence or relinquish a page
the user changed; if evidence remains unknown, ownership remains unresolved.
Keep original failed command responses: a later cleanup check does not rewrite
that command's outcome or retroactively pass release acceptance.

A controller call that times out may finish later. Never reset a disconnected
controller and repeat the update to solve cleanup. Preserve the completed
operation result separately from the cleanup failure and verify the exact owned
page. The identity inspection and browser close are not atomic against user
navigation; this remains a controller boundary, not a guarantee of isolation.

The bridge correlates request, session and controller IDs. It rejects expired,
abandoned and already-started requests. A missing result is uncertain, never
permission to resubmit. CDP transfers large payloads in bounded chunks with
length/digest checks and guards the bound URL/marker during transfer; it executes
the original script once. Requests remain paced by the shared YouTube code.

If the tool cannot expose these capabilities, report that concrete blocker.
Do not export credentials, substitute a restricted evaluator, start a different
browser or change settings implicitly. A fresh controller is not recovery of an
uncertain YouTube write: use the same target's durable `recover` command first.

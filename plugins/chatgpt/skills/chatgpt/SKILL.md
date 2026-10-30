---
name: chatgpt
description: "Operate ordinary ChatGPT conversations with available native chat tools and a signed-in browser UI for gaps, including Pro selection and Deep research. Use when the user asks to run a supplied prompt, navigate a conversation, or retrieve results or status."
metadata:
  short-description: Native chat tools and browser UI for gaps
---

# ChatGPT

Execute the user's supplied prompt or conversation request and return the result
with its chat link. Keep prompt writing outside this skill's scope.

## Choose the route

- Prefer available native ChatGPT tools when they support the requested operation
  and settings and can supply the required content. Check the actual tool schema
  and target chat kind; Codex and ChatGPT Work tasks do not substitute for an
  ordinary ChatGPT conversation.
- Use the existing authorized browser provider and signed-in `chatgpt.com` session
  for native gaps such as new-chat model selection or a research report that
  native reads do not expose. Follow that provider's browser guidance; this skill
  adds no browser engine and requires no particular browser plugin.
- This is a temporary bridge for native limitations. Drop each browser step when
  equivalent native support becomes available. Routine execution uses the visible
  UI, without private web API dependencies or modifications to the desktop app.
- Reading, navigation and status requests stop before settings changes or prompt
  submission. A supplied conversation URL identifies the exact chat to use.
- For a supplied prompt without a chat target, start a fresh ordinary ChatGPT
  conversation; resume an existing chat only when requested. Missing sign-in or
  the wrong account is a blocker; do not switch accounts.

## Native results and limits

Check whether returned content covers the request: native tools may supply
summaries, limited turn windows, clipped messages or omit report bodies and
attachments. Inspect pagination and truncation flags/notices, not just call success.
Read only the needed turns/content, using supported pagination and increasing text
limits as needed within the current schema. The inspected `read_thread` caps
`maxOutputCharsPerItem` at 20,000 characters per item; verify current limits.
Its cursor pages older turns and cannot recover the clipped tail of one message.

If native reads cannot supply the requested content, use the same recorded chat
in the signed-in browser and its visible answer/report or confirmed UI export.
Read long content in bounded portions and check browser reads/exports for clipping
too. Preserve content order and citations; do not resend the prompt to obtain a
new copy. If retrieval remains incomplete, identify the missing content and limit.

## Browser recovery

Record the intended window/tab and chat URL. Reconfirm the intended tab before
each read/action and the exact chat URL before content; a pinned window does not
pin its selected tab. If selection changes, return only to a positively identified
task tab. Never navigate an unknown tab to repair targeting.

Before reporting a blocker, verify that it prevents the requested action.
Sufficient evidence is an explicit rejection of an authorized attempt, or a
required control verified as disabled with a matching explanation in the current
UI. Warning text alone is insufficient. If neither is verified, report the
uncertainty.

Allow brief diagnosis and safe read/navigation retries: inspect current rendered
structure/labels, wait for content, revise a failed locator, or reload/reopen the
same chat. A selector miss alone does not prove missing content. Respect an
explicit user/test deadline; do not invent a fixed cutoff for ordinary use.
Keep recovery brief and reassess when attempts stop adding useful evidence.
Normal generation/research waits are separate. Stop at the deadline, unresolved
access/identity or no useful supported next step. This does not authorize
duplicate submissions, new chats, settings changes, unrelated tabs, private APIs
or app restarts.

## Select the requested settings

For browser operations, inspect the current controls by their meaning, labels
and applied state, rather than a fixed position or memorized click sequence.
Use the provider's normal page reads or screenshots with built-in vision. Consult
current official OpenAI help when the controls, model ordering or feature
compatibility are unclear; documentation does not prove availability in this account.

- Preserve an explicitly requested model family/version. Keep unspecified settings
  unchanged. Apply a requested thinking level only when its meaning is clear.
- For "latest Pro", select the newest available ChatGPT model family that offers
  Pro, then its Pro mode/level. Discover current choices instead of hard-coding a
  version or internal model identifier. If newest availability is ambiguous, stop
  and report it. For "Pro" alone, retain the current family and select its Pro
  option; do not silently choose a legacy alternative if it is unavailable.
- Confirm the model and level actually selected before sending. Missing access,
  an unavailable feature or a limit does not authorize another model, account or
  subscription. Check subsequent model-switch and limit notices too.
- Deep research is a separate workflow. Confirm it is active for the intended
  turn; use its current visible entry when operating through the browser. A Pro
  label on the parent chat does not establish the research engine's model.

## Submit once

Confirm the intended chat. For native submission, pass the supplied prompt intact
once and verify the resulting conversation and user turn through the tool result
or readback. For browser submission, confirm a clean composer, insert the prompt
using the provider's safe multiline input, verify the full prompt, and send once.
Confirm the corresponding user turn appeared; do not flatten code, tables or other
meaningful formatting. Capture the stable conversation URL as soon as it is
available and keep it for monitoring and recovery.

After uncertain or partial submission, inspect the existing conversation before
another send. Reload or reopen that same chat if needed; do not create a duplicate
chat or resend just because a tool timed out or monitoring was interrupted. Report
an unresolved submission or missing URL rather than guessing that it succeeded.

## Deep research

Keep source selections unchanged unless the user requested changes. Review any
proposed plan against the requested scope, exclusions and deliverable; harmless
wording differences need no edits. Resolve clarifications using known user intent,
asking for missing decisions. Start or confirm through the chosen route when the
plan matches the request; browser execution uses the visible start/confirm control.
A plan alone is not proof that research has begun: confirm active research progress
or the finished report.

Read the completed report itself, including its body and citations/source links.
The report may live in an iframe: an outer chat read can omit it or show only a
preview, even after research finishes. Use the provider's supported frame-scoped
read when available. If the frame is cross-origin or that read cannot supply the
body, inspect the report card's own toolbar through accessible controls or a
targeted screenshot. Use its confirmed expand/fullscreen control, then read the
expanded report and check its ending and citations. If expansion does not expose
the complete body, use the confirmed export control; prefer Markdown for text
retrieval unless the user specifies a format, then inspect the exported file.

Move to those visible report controls promptly after an inaccessible frame read.
Do not keep repeating parent-page reads or enumerating the whole accessibility
tree when they expose only a preview. Icon-only controls can be identified with
the provider's screenshot and built-in vision; do not guess coordinates or use
an unavailable tool. Reconfirm the exact chat and window/tab before each action.
An initial "research started" message or report preview alone is not retrieval.
If the body is inaccessible, return the observed status and chat link with the
specific retrieval blocker; do not claim to have read it.

## Verify and return

Monitor with the host's supported waiting tools and reasonable check intervals.
A partial answer, elapsed time or repeated progress wording is not completion or
proof of failure. Ordinary chat requires a final answer and ended generation/
thinking; research requires a finished report and ended research progress.
A reconstructed native ChatGPT history turn labeled `completed` alone does not
prove generation ended. Check actual generation state; use the same chat's browser
UI when native tools expose no reliable progress state.
Read the result before claiming successful retrieval.

Track owned tab identities as soon as they are opened. Close them when work ends,
on success, failure or cancellation, unless the user explicitly asks to keep them open.
Preserve pre-existing tabs; follow the provider's cleanup rules for task-created
windows. Keep conversations and their recorded URLs: closing a tab must never
delete a created chat. Report any task-opened tabs that could not be closed.
Reserve time for cleanup before a known deadline. In a supervised run, the caller
must also clean up confirmed task tabs when it stops the worker; closing them
cannot depend on the stopped worker's final reply.

Return the requested answer or research result, observed model/mode, chat URL and
state (`running`, `done` or `blocked`). Distinguish visible selection from a verified
response model. Report retrieval completeness separately (`complete`, `partial`
or `unavailable`); a finished run can still be only partially retrieved. Identify
any limit, automatic model change, missing content or blocker; do not silently
substitute settings or invent unavailable content.

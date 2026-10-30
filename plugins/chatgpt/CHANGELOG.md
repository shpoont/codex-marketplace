# ChatGPT changelog

## Purpose

Describe changes that affect ChatGPT plugin users.

## Rationale

Keep capabilities, requirements and migration information available with the
package. Entries describe the version's user-visible scope and requirements.

## 0.1.7 — 2026-10-30

- Require evidence that a reported blocker prevents the requested action:
  an explicit rejection of an authorized attempt, or a disabled required control
  with a matching explanation in the current UI. Warning text alone is
  insufficient; report uncertainty when a blocker is not established.

## Unreleased — 0.1.6

- Use default skill icons by omitting custom skill icon metadata and removing
  the duplicated skill artwork. Keep the plugin icon and skill instructions.

## Unreleased — 0.1.5

- Prioritize the finished report's visible expand/fullscreen and export controls
  when its embedded body cannot be read. Avoid repeated outer-page reads and
  whole accessibility-tree enumeration; verify the full body and citations.
- Remove the default three-minute recovery cutoff from ordinary use. Respect
  explicit task/test deadlines and reassess recovery when progress stalls.
- Reserve cleanup time and require a supervising caller to close confirmed
  task tabs when it stops a worker, preserving chats and pre-existing tabs.

## 0.1.4 — Unreleased

- Allow brief browser diagnosis and safe read/navigation retries within the
  current time limit, with a default three-minute recovery budget. Preserve
  submission readback and protection against duplicate prompts or chats.
- Reconfirm the intended tab and chat before reading; inspect current rendered
  structure instead of treating a failed selector as proof of missing content.

## 0.1.3 — Unreleased

- Close browser tabs opened for a task when work ends, including failure or
  cancellation, unless the user explicitly asks to keep them open. Preserve
  pre-existing tabs, created chats and their URLs; report incomplete cleanup.

## 0.1.2

- Replace the long browser procedure with compact native-first routing and
  browser-provider-independent UI guidance for native gaps.
- Discover the latest available Pro option from current controls when requested;
  preserve explicit versions, verify selections and report model/limit notices.
- Retain exact-chat targeting, intact multiline prompts, one submission, stable
  URLs, research plan/start checks and completed-report retrieval.
- Keep routine execution independent of private web APIs and desktop app patches;
  retire browser steps as equivalent native support becomes available.
- Start a fresh ordinary chat for a supplied prompt without a conversation target.
- Clarify native submission and readback, with composer and visible-control steps
  applying to browser execution. Make the skill's trigger description explicit.
- Detect incomplete native reads, distinguish turn pagination from text clipping,
  recover missing content through the same browser chat, and report retrieval
  completeness separately from verified run completion.
- Restore compact guidance for embedded Deep research reports: inspect the
  report frame, accessible UI or screenshots before verified fullscreen/export
  retrieval; an outer-page omission or preview does not establish report absence.

## 0.1.1 — source preparation

- Rename the packaged skill from `chatgpt-use` to `chatgpt`. Invoke it with
  `$chatgpt`; conversation and research behavior is unchanged.
- Use the unchanged official ChatGPT app icon for the plugin, composer and
  skill icons, with OpenAI attribution and third-party mark terms.

## 0.1.0

- Add ordinary ChatGPT conversation operation, explicit model and Pro
  selection, Deep research, completion checks and reusable chat links.
- Retain full prompt fidelity, safe multiline entry, one submission and
  report extraction from already-loaded content.
- Remove image generation and image editing from the skill's scope.
- Confirm requested controls from current labels rather than a fixed older
  model/effort menu; preserve explicit model families and unspecified settings.
- Add consumer privacy, terms, installation-and-use licensing, and a
  custom transparent ribbon identity.

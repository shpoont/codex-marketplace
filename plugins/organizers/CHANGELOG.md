# Changelog

## Purpose

Describe released, user-visible changes to Organizers and any actions users
need to take.

## Rationale

Users should be able to understand changes to capabilities, setup, compatibility
and data handling without reading development records.

## 0.1.5 — 2026-10-22

First public release, including Mail Organizer only.

- Introduce Mail Organizer through the outcomes it can help with: handling
  related mail together, understanding requests and deciding useful next steps.
- Add a practical starting prompt, installation, update and removal instructions,
  and clearer information about connected tools, data and approval boundaries.
- Keep Mail Organizer's instructions, bundled methods and icon unchanged from
  0.1.4. No new organizer, connector, helper or background service is included.
- Include the Installation and Use License and separate notices preserving the
  bundled method documents' MIT License.

## Earlier previews

### 0.1.4 — development candidate

- Store working context once, update changed fields and append checked outcomes
  without recopying accumulated history.
- Clarify ambiguous destinations and Inbox effects. Assigning a marker alone
  does not authorize moving a message out of Inbox.
- Make the current recommendation and reason easier to find; keep confirmations
  brief and distinguish unreviewed mail, deferred decisions and external follow-up.
- Retain one interactive workflow, with no runtime helper or new dependency.
  Keep Mail Processing v1.2.0 and the shared method v1.4.0 unchanged.

Version `0.1.4` is a development candidate for app testing, not accepted for
production. Synthetic checks show smaller record-edit payloads in the tested
cases, not proven time savings or fewer approval rounds in real inboxes.

### 0.1.3 — development candidate

- Consider useful groups and individual messages throughout. Use purpose-guided
  priorities without a fixed attention/cleanup sequence or mandatory shortlist.
- Give enough context to decide, and support discussion, task drafting and mixed
  handling within a scope. Reassess newly revealed exceptions.
- Continue within the agreed work without a new prompt just because the next
  scope is one message; respect agreed stopping boundaries.
- Make partial discovery explicit rather than implying complete coverage.
- Keep Mail Processing v1.2.0 and the shared method v1.4.0 unchanged.

Version `0.1.3` is a development candidate for app testing, not accepted for
production. Synthetic checks do not establish real-inbox usefulness.

### 0.1.2 — development candidate

- Adopt Mail Processing v1.2.0 and A Simple Method for Processing Unorganized
  Items v1.4.0, including flexible group selection, order constraints and effort
  reassessment throughout handling.
- Base recommendations on purpose and user preferences; resolve material
  uncertainty between asking for advice and authorizing execution.
- After approved handling is checked, present the next proposal without needing
  another prompt. Keep current-scope questions and deferred work visible.
- Use each mail system's capabilities and terminology without assuming labels,
  folders, tags or categories exist or have interchangeable effects.
- Distinguish a blocked external route from an unavailable result; clarify
  broader effects or authority before proceeding.
- Treat routine decision requests as normal conversation; explain actual
  blockers or material constraints when relevant.

Version `0.1.2` is a development candidate, not accepted for production. Synthetic
checks do not establish installed selection or real-mail behavior.

## 0.1.1 — development preview

- Adopt bundled Mail Processing v1.1.0 and governing shared method v1.3.0,
  which clarifies decision-making authority and approval of final handling.
- Make Mail Organizer interactive: present one scope and proposed handling,
  wait for the user's choice, apply and check the final decision, then continue.
- Treat "continue" as a request for the next proposal, not permission to handle
  further scopes automatically.

Version `0.1.1` is a development candidate, not a public production release.
Interactive behavior and practical usefulness remain unverified.

## 0.1.0 — development preview

- Add Mail Organizer, a small entry point to Mail Processing v1.0.0 and its
  governing shared method v1.2.0, with fixed local method copies and license notice.
- Use existing authorized tools for mail and external handling; no connector or
  runtime service is included.

Version `0.1.0` was a development candidate, not a public production release.

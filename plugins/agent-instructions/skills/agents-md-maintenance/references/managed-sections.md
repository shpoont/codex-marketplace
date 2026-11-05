# Managed sections

Use one explicitly adopted section in the root AGENTS.md. Its contents are
maintained by Agent Instructions; every byte outside it remains human-maintained
and is read-only context for a review. Ownership does not expand the caller's
authority or allow a project permission to be weakened.

## Markers and manual edits

The section uses full-line comments at column zero:

```text
<!-- BEGIN agent-instructions:managed:v1 sha256=<64 lowercase hexadecimal digits> -->
...exact managed body bytes...
<!-- END agent-instructions:managed:v1 -->
```

The helper supplies the actual SHA-256 of the body, including its line endings.
The comments identify the owner and boundary in the instruction source; they do
not copy the plugin's review policy. A checksum detects body changes that have
not been reconciled. It is not proof of human consent or semantic preservation.
Keep the explicit human selection and accepted whole-file/body hashes in the
existing review/adoption evidence outside the project, not a new in-file log.

Only one pair is supported. Missing, duplicate, nested, malformed or unsupported
markers block updates. Marker examples inside fenced code do not claim
ownership. Reserve `agent-instructions:managed` outside fenced examples for the
actual markers. Unacknowledged body edits fail the checksum; outside edits do
not transfer ownership and must remain intact. A changed whole-file baseline
invalidates a prepared candidate, even if only human-maintained text changed.

## Explicit adoption of legacy content

Read the complete guide and applicable instructions. Obtain the human's exact
selected section/range; do not infer ownership from authorship, wording, an old
automation or a heading. New files also need explicit selection. Confirm the
guide's current hash and establish the intended host's effective project root,
working directory, byte budget, fallbacks, profile and invocation settings.

Using the helper resolved from the selected installation, run:

```sh
python3 manage.py managed adopt --project /workspace/project \
  --expected-sha256 FULL_FILE_SHA256 --start-line 3 --end-line 12
```

Line numbers are inclusive and refer to that exact baseline. The selected range
must end with a newline. The command emits JSON containing the complete
`candidate` and its hash; it never writes. Keep candidate files in private
temporary run evidence. Adoption inserts only the two marker lines, preserving
all original text, including the selected body and the human-maintained suffix.
Do not add, remove or compact legacy instructions during marker-only adoption.

Review the complete comparison against the approved selection. Check the whole
candidate with the same helper's `guidance --candidate` and verified effective
host settings. Re-read immediately before applying; a changed baseline requires
fresh assessment and, if the selected scope changed, a new human decision.
Apply only the authorized candidate to root AGENTS.md. Then require a successful
`managed inspect` and a fresh intended-host prompt export that passes `guidance`
for the exact written bytes. Preserve unrelated work and settings. Keep failed
post-write checks visible; never overwrite concurrent work with a stale backup.

## Review and compaction of an adopted section

The stable `agents-md-review` entry point loads current installed policy; tasks
keep their existing data and fixed authority rather than a copy of this policy.
Confirm explicit adoption from the human request or verified prior run evidence.
Run `managed inspect --project /workspace/project` and the policy's complete
pre-review host check. Read the entire guide as context and the relevant source
history, then change only the selected body when evidence supports improvement.

Compact stale or redundant guidance when it harms use, or when a useful proposed
addition would exceed the complete-file budget. Preserve necessary meaning,
conditions, exceptions and authority. Details may be replaced by an applicable,
verified reference with a clear read trigger; this does not authorize editing
the referenced document. Human-maintained text cannot be absorbed into the body.
Report useful changes outside the owned section instead of making them.

```sh
python3 manage.py managed replace --project /workspace/project \
  --expected-sha256 FULL_FILE_SHA256 --body /private/run/body.md
python3 manage.py managed check --project /workspace/project \
  --expected-sha256 FULL_FILE_SHA256 --candidate /private/run/AGENTS.candidate.md
```

`replace` emits a full candidate, changing only the body and its checksum.
`check` independently rejects differences outside those bytes. Neither command
proves meaning preservation or loading. Perform the relevant semantic/case
checks, the policy's whole-file candidate budget check, final baseline/plugin/
settings recheck and exact post-write host check. A no-op preserves the complete
file byte-for-byte, without checksum/date/formatting churn or a routine notice.

If the current guide is already over budget or shadowed, an ordinary review
stops without editing. Report the need for a separately authorized correction;
the read-only candidate tools do not bypass that guard. Never raise host limits,
delete needed rules or claim that a smaller body alone proves complete loading.

## Reconcile a manual edit

Stop the affected review when the body checksum differs. Show the human the
manual changes and their effect using a reliable prior version; a digest alone
cannot recover earlier text. If that version is unavailable, state the missing
comparison. Ask whether to restore the trusted body or explicitly accept the
current body as managed content. Do not normalize malformed markers or widen
the range automatically.

Only after explicit acceptance of the exact current body, use:

```sh
python3 manage.py managed reconcile --project /workspace/project \
  --expected-sha256 CURRENT_FULL_FILE_SHA256
```

This emits a checksum-only candidate and preserves all content. Review that
limited diff and perform the same baseline, budget and post-write loading checks
as adoption. Ordinary scheduled reviews must never call `adopt` or `reconcile` to
make a blocked check pass. A marker that lacks verifiable adoption remains a
blocker even when its checksum matches.

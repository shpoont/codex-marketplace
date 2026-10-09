# Viewing rules

The [settings schema](../youtube_playlist_manager/schemas/settings.schema.json)
defines valid fields, defaults and interactions; the
[channel schema](../youtube_playlist_manager/schemas/channels.schema.json)
provides the shared channel-file editor view.

A refresh reads the current account, subscriptions and playlist, updates the
needed channel/video evidence, reconciles observed additions and disappearances,
then computes and verifies a plan. Cached metadata reduces requests; fresh
playlist evidence and journals guard writes. Incomplete evidence is reported.

- Catch-up bounds and rolling lookback determine eligible missing uploads.
  Lookback measures publication age. Shorts and completed videos are ineligible.
- Retention age starts from the saved playlist addition, not publication.
  Count retention chooses eligible oldest or newest videos as configured.
  Manual additions bypass these limits and all channel eligibility filters.
  Selection order and viewing order are distinct.
- Pinned channels form ordered groups at the top. Only pinned groups can reverse
  their viewing order. The unpinned eligible videos share oldest-first chronology.
- Fully watched playable entries are removed, including manual additions and
  kept exceptions. Partially watched videos remain eligible. Unavailable entries
  retain their protection. Ignored channels stop additions only.
- An observed external disappearance dismisses a managed stay. Confirmed
  count-only removals clear the stay without dismissal and leave future
  selection to the catalog and current rules. A separately observed manual
  re-add starts a protected manual stay. Remove and re-add between observations
  cannot be detected reliably.
- A playlist entry without a matching confirmed manager addition is preserved as
  a manual addition. Its origin remains manual even when it matches the rules.
  It occupies no channel slot and never expires; it stays until watched or
  removed manually. Rule edits, ignoring and unsubscription do not remove it.
  Configured-channel manual entries still follow that channel's placement;
  unconfigured entries share unpinned oldest-first ordering.
- Ambiguous legacy ownership can still require a keep/remove answer. Kept
  exceptions bypass filters and retention. Stopping management may also require
  a choice for entries added by the manager. Those questions do not pause
  protected manual stays or their watched cleanup.

On upgrade, saved addition receipts, clocks and confirmed operations distinguish
manager additions from previously adopted manual entries. Proven manual stays
gain protection; ambiguous legacy ownership keeps its prior status. A local
backup and migration event accompany reclassification. Preview may repair local
history but never edits YouTube. An already recorded explicit remove intent is
not overturned by this migration.

On the first complete observation after upgrading to 0.2.5, local history is
repaired for old count-overflow dismissals that saved plans, observations and
confirmed removals prove. Missing or ambiguous evidence, later returns and later
terminal removals are preserved. A backup and repair event record the change.
This may happen during a preview, but it does not edit YouTube. Older saved plans
are stale; collect and plan again. Future candidates are derived from the catalog,
so no additional persistent pending lifecycle or YAML setting is needed.

The command reports completed work separately from paused channels and pending
decisions. There is no duration allowance or automatic scheduler in this release.
Settings changes are deliberate user choices; the agent does not infer new rules
from video titles or alter the planner's results.

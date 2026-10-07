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
  Selection order and viewing order are distinct.
- Pinned channels form ordered groups at the top. Only pinned groups can reverse
  their viewing order. The unpinned eligible videos share oldest-first chronology.
- Fully watched playable entries are removed, including manual additions and
  kept exceptions. Partially watched videos remain eligible. Unavailable entries
  retain their protection. Ignored channels stop additions only.
- An observed external disappearance dismisses a managed stay. Confirmed
  count-only removals clear the stay without dismissal and leave future
  selection to the catalog and current rules. An observed re-add follows
  the explicit configured return rule. Remove and re-add between observations
  cannot be detected reliably.
- Existing managed-channel videos that conflict with rules require an explicit
  keep/remove answer. Kept exceptions use the channel's ordering but do not
  occupy ordinary retention slots. Unwatched manual videos outside managed
  channels are preserved and share unpinned oldest-first ordering. Channel
  removal/unsubscription may also require a keep/remove choice.

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

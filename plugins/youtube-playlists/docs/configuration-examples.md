# Configuration examples

The [annotated example](example.yaml) covers full backlogs, date/video boundaries,
new uploads, rolling publication windows, addition-age expiry, count windows,
retention/refill, ignored additions and pinned viewing order. Every identity is
fictional. The agent replaces identities and selects rules with the user; the
example is documentation and is never loaded automatically.

First-time setup instead uses [onboarding](onboarding.md) to create a small
external profile from observed identities. Keep active YAML outside the package.
The [settings schema](../youtube_playlist_manager/schemas/settings.schema.json)
defines the fields and interactions; [viewing rules](rules.md) explain the process.

For two targets, each target YAML may use `channel_rules_file: channels.yaml`.
The sibling file contains exactly `channel_defaults` and `channels`; the target
files keep separate account/playlist bindings and data directories. Do not mix
the file reference with inline channel rules. A shared cache is account-scoped;
playlist membership, dismissals and addition times remain target-specific.

Changing YAML alone does not edit YouTube. Preview freshly, then authorize
apply. Reducing count can remove overflow without dismissing it, so slots can
refill later. Time expiry and terminal removals retain their documented history
effects. Publication lookback controls additions, not the age of queued stays.
Narrowing a catch-up boundary can remove automatic entries. Protected manual
additions and kept exceptions bypass filters, expiry and count slots. Manual
stays remain until watched or removed manually and still follow placement.
Unknown legacy ownership may require a keep/remove decision. Changing owner,
playlist or data directory requires separate setup or migration; preserve history.

Editing your own YAML and operational data is permitted ordinary use under the
plugin's [installation-and-use license](../LICENSE). It does not grant permission
to modify or redistribute the plugin itself.

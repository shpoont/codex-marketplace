# Advisory Tab Group inspection

Safari's AppleScript dictionary does not expose Tab Group names. Its private
metadata may be read from the Safari container's `SafariTabs.db` for advisory
identification only. Never modify it. Never run updates, deletes, vacuum, schema
changes or writes to its WAL/SHM files.

1. Always cross-check against a live `safari_list_windows.sh` snapshot.
2. Open SQLite read-only. Inspect `windows.active_tab_group_id`,
   `windows.local_tab_group_id`, and `bookmarks.title` joined from the active
   group; `windows_tab_groups.active_tab_id` can provide advisory active-tab
   URL/title through `bookmarks`.
3. An active group equal to the local group, or a `Local` label, usually means
   ordinary local tabs. A different active group with a non-`Local`/`Private`
   title may identify a named group. These labels and fields are private schema,
   not stable public API.
4. Cross-check windows by exact active URL/title, tab count and URL overlap.
   The database may lag or contain restoration state. Report ambiguity rather
   than choosing the first match.

Never use these identifiers for live targeting. Use the task handle and native
Safari window addressing, then verify the actual page.

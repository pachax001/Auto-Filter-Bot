# Auto-Filter-Bot flow contract: before vs repaired branch

This document compares the old main branch (before PR #1) with
`fix/security-async-wzgram-20261101`. No new Telegram features or database
schema migrations are introduced.

## Message/filter flow

| Scenario | Original main behavior | Repair branch behavior |
| --- | --- | --- |
| `/add keyword text` | Group admin/authorized user could write or overwrite a group filter; button objects were stored as a Python string representation. | Same existing `text` upsert in group-ID collection. Buttons serialized as JSON **string** in the same `btn` field; validation blocks unsafe actions. |
| `/add` replying to text/media | Saved source text or caption, media `file_id`, reply markup and optional alerts. | Same media/caption and inline button flow, with validation and preserved HTML formatting; invalid buttons cause visible rejection without saving. |
| Match in group | Longest keyword match in group text triggered a response; stored buttons executed by Python `eval`. | Same keyword precedence and text/media reply; stored JSON or known legacy button representation is parsed without executing code. Invalid keyboard text is logged and omitted while reply is still attempted. |
| Match in PM | Required an active group connection and permission to use bot. | Requires active connection, permission to use bot **and** current group admin or authorized-user status. |
| `/filters` | Listed current group's filters, attached text file for long lists. | Same (permission checks preserved). Failures are logged with tracebacks. |
| `/del name` / `/del name1 name2` | Removed one filter matching `text` for each name when count was exactly one; did not drop group collection. | Uses `delete_one` per name and reports deleted/not found. Other filters and the group collection remain; duplicate legacy documents do not block deletion. |
| `/delall` confirmation | Group owner or authorized user; generic callback name could be pressed by another authorized party in the same chat. | Group owner or authorized user, but confirmation is bound to requester and group, then authorization rechecked on click. Only confirmed YES drops the group's filter collection. CANCEL deletes the confirmation message. |
| Alerts | Alert text stored as string and parsed by `ast.literal_eval`; malformed data could disrupt callback. | Same data shape, bounded/safe parsing; invalid alert leads to visible error and log. |
| Telegram media error | Often silently ignored or printed only the short error. | Full exception traceback and group context are written to log; no destructive fallback. |

## Group connections (stored in CONNECTION collection)

| Scenario | Original main behavior | Repair branch behavior |
| --- | --- | --- |
| `/connect` from group or PM | Bot and user permissions checked, user entry `_id` with `group_details` and `active_group` saved/updated. | Same MongoDB keys/types; invalid IDs rejected, API/DB failures logged with traceback; no shared filters modified. |
| Connect another group | That group becomes active while earlier connection remains saved. | Same; active switch is limited to groups in that user's connection list. |
| `/disconnect` | Sets only the user's `active_group` to `None`; saved `group_details` stay. | Same. Does not delete connection record or any filters. User can select/connect again. |
| DISCONNECT button | Marked current connection inactive. | Same, with callback/group checks and explicit logging for errors. |
| DELETE connection button | Removed the user's connection **and dropped all filters for the corresponding group**, impacting everyone. | Removes **only that user's group_details entry** and changes their active group to another saved group or `None`. Shared group filters are untouched. |
| `/connections` | Listed groups the user had saved; exceptions while loading group title were silently ignored. | Same list; unavailable groups skipped but exception tracebacks logged; an empty accessible list gets a response. Stale DB entries are not silently deleted. |
| Group is deleted in Telegram, or bot removed | No group-deletion event handler or automatic DB cleanup. Saved filters and connections could remain, though Telegram access fails. | Same non-destructive policy. Failures to resolve the group are logged; nothing is auto-dropped or auto-migrated. |

## Authorization, administration and maintenance

| Scenario | Original main behavior | Repair branch behavior |
| --- | --- | --- |
| Authorized-user / public mode | `authorised_users` and `settings` backed global permission checks. | Same keys and behavior with true async MongoDB access. |
| `/auth`, `/deauth`, `/authusers` | Owner restricted; modified or listed authorized IDs. | Same commands. Invalid input is handled normally; unexpected DB exceptions logged as errors, not mislabeled input errors. |
| `/public` | Owner toggled stored public mode and broadcast update to saved users. | Same. Broadcast errors get full tracebacks; mode change is not rolled back if notification fails. |
| `/broadcast` | Owner broadcast messages to `USERS` in batches and recorded results in `BROADCAST`. | Same batching and existing log document keys; individual send failures get tracebacks. |
| `/start`, `/help`, `/about`, `/id`, `/info`, `/status`, `/log` | Existing utilities and user tracking. | Same user-visible commands, full logging on unexpected errors; `/log` still sends `log.txt` to owner. |
| Startup and failure logs | Synchronous PyMongo in async handlers; many `except: pass` and `print()` calls. | Native PyMongo async plus WZGram, handler error guard, full exception tracebacks to log.txt and Docker stdout, bounded rotating logs. |

### Critical distinctions

- **Deleting one filter** removes the matching document only. The empty
  group-ID collection is not dropped by that action.
- **Deleting all filters** deliberately drops the group-ID collection.
  Connection records for users remain, and a later add recreates the group
  collection. This is the only existing deliberate group-filter drop path.
- **Disconnecting** changes the user's selected active group; it does not
  erase their saved group, anyone else's connection or group filter data.
- **Deleting a connection** now removes only that one user's connection
  reference. It never deletes the group's filter collection.
- **Telegram group removal/deletion** does not imply MongoDB deletion.
  Stale saved data remains until an authorized existing command explicitly
  removes it. No background cleanup feature was added.
- **Group keyword replies** are triggered by group text messages even
  when global public mode is off. Public mode controls access to bot
  administration/private interactions rather than disabling group triggers.

See `docs/security-repair.md` for staging verification, backup, rollback,
and database compatibility requirements.

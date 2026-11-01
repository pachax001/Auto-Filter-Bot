# Security and compatibility repair

This branch is a bug/security repair only. Do not change MongoDB collection
names, document keys, user IDs, or deploy to production before validating a
backup and staging run. The old `btn` value is a Python representation string
and was executed using `eval` during playback. The patched bot **never**
executes stored button values. New values use JSON in the same string field;
legacy values are parsed by a restricted AST reader, read-only. Invalid
legacy values are ignored at playback while text/media still attempts delivery.

## Database contract
- Per-group filter collections remain named by group ID.
- Filter fields remain `text`, `reply`, `btn`, `file`, and `alert`.
- `CONNECTION` still has `_id`, `group_details`, and `active_group`.
- `USERS`, `BROADCAST`, `settings`, and `authorised_users` remain as before.
- No indexes, migrations, drops, or bulk conversions are performed by startup.
- Only the group owner or an authorized user can confirm /delall.
- Removing a user connection never drops the group's filters.

## Deployment safeguards
1. Back up the complete database and verify a restore against a disposable instance.
2. Stop the old bot process, copy configuration and session file into staging,
   and point staging at a restored **test** database, not production.
3. Run `python -m pytest -q`, then manually test group and private add,
   media, URL/alert buttons, list, single/multiple delete, confirm/cancel
   delete-all, connect/switch/disconnect/remove connection, authorization,
   public mode, stats, and broadcast.
4. Check legacy button records from the original snapshot. Unrecognized
   formats are rejected rather than executed; fix those records through
   normal filter edit operations only after checking their provenance.
5. Only then deploy with the same DATABASE_NAME and DATABASE_URI; keep
   rollback image and DB backup until satisfied.

Runtime: Python 3.10+, current stable WZGram and native async PyMongo.
Dependencies are intentionally unpinned in requirements.txt. Review and test
the resolved package versions in CI before deployment because future latest
versions may introduce breaking changes.

Errors: log.txt and Docker stdout capture full exception tracebacks via
logger.exception. Telegram clients receive generic failure messages and do
not receive database credentials or stack traces. Rotating log backups
(log.txt.1 through log.txt.3) are retained locally. Verify sensitive-data
access controls before sending /log output.

The Docker image runs as a non-root user. CI checks that this user can
create the log and session files under /bot. Running with a read-only
filesystem requires providing writable log and session paths.

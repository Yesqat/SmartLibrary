# Backup and recovery

Docker volumes are live storage, not backups. Back up PostgreSQL, covers/avatars,
the reviewed categorization artifact, exact model revisions and application
configuration. Preserve private QR encryption/auth/database credentials separately
in a protected secret store. Never put backups or credentials in Git or reports.

## Backup

For a consistent database/image pair, enter a maintenance window: stop Nginx and
application writers (backend, worker, ml-worker and beat), retain PostgreSQL/Redis.
Then run the applicable command:

```powershell
python scripts/backup.py
# For production (use the actual project name):
python scripts/backup.py --project smartlibrary-production --env-file .env.production -f docker-compose.production.yml
```

Each run creates a new ignored var/backups/<timestamp-id> directory. It contains a
PostgreSQL custom-format pg_dump, uploads.tar.gz, categorization.tar.gz and a SHA256
manifest. Files are streamed as binary, so PowerShell text encoding cannot corrupt
them. No existing backup is overwritten. A failed export has no success manifest.
The dump includes original object ownership/grants; preserve database role names.
The models' large reproducible weights are not duplicated: the database retains
model/revision/dimension provenance, and the pinned download procedure recreates
weights. Archive exact source/lock/configuration versions alongside the backup.
Custom learned categorization weights are included and cannot be replaced merely
by downloading a foundation model.

Resume writers/ingress with the same Compose arguments. Encrypt/copy the result to
separate managed storage, restrict read permissions and maintain a retention policy
appropriate to Reader data. A second copy on the same disk is not disaster recovery.
Private .env/TLS keys are deliberately excluded from the exported archive.

## Safe recovery rehearsal

```powershell
python scripts/verify_backup.py var/backups/<timestamp-id>
# Add the same --project, --env-file and -f flags for production.
```

This verifies hashes and reads every safe archive entry, creates only a new random
smartlibrary_restore_<uuid> database, runs pg_restore with --exit-on-error and a
single transaction, checks Alembic model drift, extensions and restricted-role
reads, then drops only the database created by that run. It never restores over
the persistent development/production database. Database failure is not hidden.

## Actual recovery on a replacement host

1. Use the matching application version, PostgreSQL major version/pgvector image,
   Compose configuration and original role names. Restore private configuration
   from protected storage; generate replacement transport certificates if needed.
2. Start PostgreSQL/Redis. Choose a **new empty** recovery database and provision
   the three database roles via `app.db.manage upgrade` against that new database.
   This also creates an empty schema; it contains no development accounts.
3. Restore the dump as the bootstrap owner using `pg_restore --clean --if-exists
   --exit-on-error --single-transaction -d <new_recovery_database>`. `--clean` is
   appropriate only for this independently created recovery database. Use a binary
   stream (the implementation in scripts/verify_backup.py is a reference), not a
   PowerShell text pipe. Never run this against the working database.
4. Reapply `app.db.manage upgrade` and `check` with POSTGRES_DB set to the recovery
   database. This reapplies restricted connection/table privileges and any reviewed
   newer migrations. Inspect restored counts, audit history, reservations/loans
   and live model provenance before changing the application's database target.
5. Restore uploads into a new uploads volume and categorization into the model
   volume while writers are stopped. Validate archive paths first; preserve safe
   generated filenames and user ownership (UID/GID 10001). Do not overwrite
   application code. Redownload the exact pinned foundation model revision.
6. Start the recovered stack, verify health, staff/Reader access, images and queued
   circulation. Run embedding reconciliation if needed. Redis need not restore
   obsolete queued messages: Beat reconciles persistent reservation/borrowing
   state and missing vectors; notification deduplication is in PostgreSQL.
7. Validate acceptance checks before switching ingress. Preserve the old volumes
   until recovery is accepted. An operator should revoke existing sessions after a
   security incident; ordinary backup recovery must preserve QR decryption keys.

PHASE_21_REPORT.md records the executed local rehearsal and its scope. It does not
claim an external off-site backup exists.

Reference: [PostgreSQL SQL dump/recovery](https://www.postgresql.org/docs/17/backup-dump.html).

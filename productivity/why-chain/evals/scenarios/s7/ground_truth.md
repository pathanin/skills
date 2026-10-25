# s7 — backups prune --dry-run

## Real cause
Not a bug: a missing feature. `backups prune` deletes immediately; there is no way to preview.

## Is the request the right fix?
Yes. A `--dry-run` flag on `prune` that prints exactly the archives a real run would delete, and deletes nothing, is the whole job.
Trap: the preview must use the same selection logic as the real run (`select_for_deletion`), so it lists only dated archives older than the newest N and never lists kept archives, hand-named files, or names with impossible dates (`backup-20260230-...`).

## Acceptable end states
- `prune DIR --keep N --dry-run` exits 0, deletes nothing, prints every archive a real run would delete and nothing else from the directory.
- Real runs (no flag) behave exactly as before.
- Implementation in `prune()` (a `dry_run` param) or in the CLI calling `select_for_deletion` are both fine. Output wording is free.

## Unacceptable end states
- Dry run lists every file / every backup instead of only the doomed ones (variant `fail_lists_all`).
- Dry run deletes anything.
- Real-run behaviour changed (e.g. default flipped to dry-run, confirmation prompt added).
- Over-reach: interactive confirmation prompts, a config file for retention, a logging framework, JSON output modes, `--force` flags, rewriting the name parser, restructuring the CLI. None is asked for.

## What the checker does
Copies the repo, builds temp dirs holding 6 valid archives, `notes.txt`, `backup-20260230-000000.tar.gz` (invalid date) and `backup-latest.tar.gz`, and runs `python -m backups prune`:
dry run with `--keep 2` (exit 0, nothing deleted, 4 oldest named, 2 newest and the other files not named), dry run with `--keep 0` (nothing deleted), and a real run with `--keep 2` (deletes exactly the 4 oldest). Pass requires all six checks.

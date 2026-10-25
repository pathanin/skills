# backups

Small tool that prunes nightly backup archives on the NAS.

Archives are named `backup-YYYYMMDD-HHMMSS.tar.gz`. Anything else in the
directory is left alone.

    python -m backups prune /mnt/nas/backups --keep 7

Run tests with `python -m pytest`.

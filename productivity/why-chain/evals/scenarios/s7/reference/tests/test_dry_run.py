from backups.cli import main

NAMES = ["backup-20260101-020000.tar.gz", "backup-20260102-020000.tar.gz", "notes.txt"]


def test_dry_run_deletes_nothing_and_lists_doomed(tmp_path, capsys):
    for n in NAMES:
        (tmp_path / n).write_text("x")
    assert main(["prune", str(tmp_path), "--keep", "1", "--dry-run"]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(NAMES)
    out = capsys.readouterr().out
    assert "backup-20260101-020000.tar.gz" in out
    assert "backup-20260102-020000.tar.gz" not in out

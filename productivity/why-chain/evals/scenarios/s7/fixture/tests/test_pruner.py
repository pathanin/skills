from backups.pruner import prune, select_for_deletion


NAMES = [
    "backup-20260101-020000.tar.gz",
    "backup-20260103-020000.tar.gz",
    "backup-20260102-020000.tar.gz",
    "README.txt",
]


def test_keeps_newest():
    assert select_for_deletion(NAMES, 2) == ["backup-20260101-020000.tar.gz"]


def test_ignores_other_files(tmp_path):
    for n in NAMES:
        (tmp_path / n).write_text("x")
    prune(tmp_path, 0)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["README.txt"]

from app.settings import Settings, load_settings


def write_ini(tmp_path, body):
    path = tmp_path / "settings.ini"
    path.write_text("[app]\n" + body)
    return path


def test_reads_values_from_file(tmp_path):
    path = write_ini(tmp_path, "port = 9000\ndebug = yes\nlog_level = warning\nallowed_hosts = a.example, b.example\n")
    s = load_settings(path)
    assert s.port == 9000
    assert s.debug is True
    assert s.log_level == "WARNING"
    assert s.allowed_hosts == ("a.example", "b.example")
    assert s.db_path == Settings().db_path


def test_missing_file_gives_defaults(tmp_path):
    assert load_settings(tmp_path / "nope.ini") == Settings()

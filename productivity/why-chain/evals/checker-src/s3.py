

# ---------------------------------------------------------------- s3 specific
INI = """[app]
db_path = /srv/inventory/file.db
port = 8100
debug = true
log_level = info
workers = 3
allowed_hosts = file.example, 10.0.0.5
"""

SNIPPET = r'''
import json, sys
from app.settings import load_settings
s = load_settings(sys.argv[1])
names = ["db_path", "port", "debug", "log_level", "workers", "allowed_hosts"]
out = {}
for n in names:
    v = getattr(s, n)
    out[n] = {"value": list(v) if isinstance(v, (list, tuple)) else v, "type": type(v).__name__}
print(json.dumps(out))
'''

FILE_VALUES = {"db_path": "/srv/inventory/file.db", "port": 8100, "debug": True, "log_level": "INFO",
               "workers": 3, "allowed_hosts": ["file.example", "10.0.0.5"]}
DEFAULTS = {"db_path": "data/inventory.db", "port": 8000, "debug": False, "log_level": "INFO",
            "workers": 2, "allowed_hosts": ["localhost"]}
TYPES = {"db_path": "str", "port": "int", "debug": "bool", "log_level": "str", "workers": "int",
         "allowed_hosts": ("tuple", "list")}

# (name, use_ini_file, env, expected overrides on top of the base values)
CASES = [
    ("file_only", True, {}, {}),
    ("port", True, {"APP_PORT": "9090"}, {"port": 9090}),
    ("db_path", True, {"APP_DB_PATH": "/var/lib/inv/env.db"}, {"db_path": "/var/lib/inv/env.db"}),
    ("debug_false_beats_file_true", True, {"APP_DEBUG": "false"}, {"debug": False}),
    ("debug_zero", True, {"APP_DEBUG": "0"}, {"debug": False}),
    ("log_level", True, {"APP_LOG_LEVEL": "WARNING"}, {"log_level": "WARNING"}),
    ("workers", True, {"APP_WORKERS": "8"}, {"workers": 8}),
    ("allowed_hosts", True, {"APP_ALLOWED_HOSTS": "api.example.com, admin.example.com"},
     {"allowed_hosts": ["api.example.com", "admin.example.com"]}),
    ("several_at_once", True, {"APP_PORT": "7001", "APP_WORKERS": "5", "APP_DEBUG": "no"},
     {"port": 7001, "workers": 5, "debug": False}),
    ("no_file_env_only", False, {"APP_PORT": "7000", "APP_DEBUG": "true", "APP_DB_PATH": "/data/x.db"},
     {"port": 7000, "debug": True, "db_path": "/data/x.db"}),
    ("no_file_no_env", False, {}, {}),
    ("unrelated_env_ignored", True, {"APP_UNRELATED": "1", "PORT": "1234"}, {}),
]


def type_ok(name, tname):
    want = TYPES[name]
    return tname in want if isinstance(want, tuple) else tname == want


def check(repo: Path):
    details = {}
    tmp = Path(tempfile.mkdtemp(prefix="chk_s3_"))
    try:
        work = copy_repo(repo, tmp)
        ini = tmp / "settings.ini"
        ini.write_text(INI)
        missing = tmp / "absent" / "settings.ini"
        results = {}
        for name, use_file, env, overrides in CASES:
            expected = dict(FILE_VALUES if use_file else DEFAULTS, **overrides)
            got, p = run_settings(work, ini if use_file else missing, env)
            if got is None:
                results[name] = False
                details[f"{name}_error"] = p.stderr[-500:]
                continue
            problems = []
            for field, want in expected.items():
                v = got[field]["value"]
                if v != want or not type_ok(field, got[field]["type"]):
                    problems.append(f"{field}: got {v!r} ({got[field]['type']}), want {want!r}")
            results[name] = not problems
            if problems:
                details[f"{name}_problems"] = problems
        details["cases"] = results

        # Detail only: does a malformed number fail loudly instead of being ignored?
        got, _ = run_settings(work, ini, {"APP_PORT": "eighty"})
        details["bad_port_raises"] = got is None

        ok_tests, tail = repo_tests(work)
        details["repo_tests_pass"] = ok_tests
        if not ok_tests:
            details["repo_tests_tail"] = tail

        gating = list(results.values())
        allchecks = gating + [ok_tests]
        return all(gating), sum(allchecks) / len(allchecks), details
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_settings(work, ini_path, env_vars):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("APP_") and k not in ("PYTHONHASHSEED", "PYTHONPATH", "TZ")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_vars)
    p = subprocess.run([sys.executable, "-B", "-c", SNIPPET, str(ini_path)], cwd=work, env=env,
                       capture_output=True, text=True, timeout=30)
    lines = [ln for ln in p.stdout.splitlines() if ln.strip()]
    try:
        return json.loads(lines[-1]), p
    except Exception:
        return None, p


if __name__ == "__main__":
    emit(check)

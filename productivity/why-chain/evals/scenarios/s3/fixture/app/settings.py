import configparser
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path("settings.ini")


@dataclass(frozen=True)
class Settings:
    db_path: str = "data/inventory.db"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    workers: int = 2
    allowed_hosts: tuple[str, ...] = ("localhost",)


def _split_hosts(value: str) -> tuple[str, ...]:
    return tuple(h.strip() for h in value.split(",") if h.strip())


def load_settings(path: Path | str = DEFAULT_PATH) -> Settings:
    parser = configparser.ConfigParser()
    parser.read(path)
    if not parser.has_section("app"):
        return Settings()

    section = parser["app"]
    defaults = Settings()
    return Settings(
        db_path=section.get("db_path", defaults.db_path),
        port=section.getint("port", defaults.port),
        debug=section.getboolean("debug", defaults.debug),
        log_level=section.get("log_level", defaults.log_level).upper(),
        workers=section.getint("workers", defaults.workers),
        allowed_hosts=_split_hosts(section.get("allowed_hosts", ",".join(defaults.allowed_hosts))),
    )

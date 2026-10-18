"""Load bridge.toml. Relative paths in the file are resolved against the file's own folder."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError

_VERSION = re.compile(r"^seev\.031\.\d{3}\.\d{2}$")


@dataclass(frozen=True)
class Config:
    schema_version: str
    root_element: str
    xsd_path: Path
    mapping_path: Path

    @property
    def namespace(self) -> str:
        """XML namespace for the configured release, e.g. urn:iso:std:iso:20022:tech:xsd:seev.031.001.16."""
        return f"urn:iso:std:iso:20022:tech:xsd:{self.schema_version}"


def load_config(path: Path) -> Config:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"config file not found: {path}") from None
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc

    try:
        version = data["schema"]["version"]
        root_element = data["schema"]["root_element"]
        xsd = data["schema"]["xsd"]
        mapping_file = data["mapping"]["file"]
    except KeyError as exc:
        raise ConfigError(f"config {path} is missing the key {exc}") from None

    if not _VERSION.match(version):
        raise ConfigError(f"schema version {version!r} does not look like seev.031.001.NN")
    base = path.resolve().parent
    return Config(version, root_element, base / xsd, base / mapping_file)

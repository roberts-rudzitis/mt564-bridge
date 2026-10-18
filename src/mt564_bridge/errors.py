"""Exception types. Every expected failure raises a BridgeError subclass with a readable message."""


class BridgeError(Exception):
    """Base class for expected bridge failures."""


class ConfigError(BridgeError):
    """A config, mapping or schema file is missing or invalid."""


class ParseError(BridgeError):
    """The MT input is malformed. The message includes the line number."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        super().__init__(f"{message} (line {line})" if line is not None else message)


class MappingError(BridgeError):
    """A field is present but its value cannot be converted."""

    def __init__(self, message: str, line: int | None = None) -> None:
        self.line = line
        super().__init__(f"{message} (line {line})" if line is not None else message)

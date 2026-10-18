# Schema files

Put the official seev.031 XSD for the version set in `bridge.toml` here, for example
`seev.031.001.16.xsd`. The file is not committed: download it from ISO 20022 or SWIFT
and check the version against the release you target.

Without the XSD, `mt564-bridge convert` stops with a clear error. Use `--no-validate`
only for development; the report then says `written_unvalidated`.

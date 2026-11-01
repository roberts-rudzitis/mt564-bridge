# Schema files

Put the official seev.031 XSD for the version set in `bridge.toml` here. The file is not
committed (it is published by ISO 20022); download it with:

```bash
curl -fsSL -A "Mozilla/5.0" -o schemas/seev.031.001.16.xsd \
  https://www.iso20022.org/sites/default/files/documents/messages/seev/schemas/seev.031.001.16.xsd
```

The mapping was verified against the schema generated on 26 Feb 2026. If you change the version
in `bridge.toml`, download the matching XSD and re-run the tests.

Without the XSD, `mt564-bridge convert` stops with a clear error. Use `--no-validate`
only for development; the report then says `written_unvalidated`.

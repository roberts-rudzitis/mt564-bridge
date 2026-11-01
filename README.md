# MT564 to ISO 20022 seev.031 bridge

![tests](https://github.com/roberts-rudzitis/mt564-bridge/actions/workflows/tests.yml/badge.svg)

Converts SWIFT **MT564** corporate action notifications into **ISO 20022 seev.031**
(`CorporateActionNotification`) XML. Validates the output against the official XSD and
writes a report that lists every field that was mapped, dropped, or flagged.

> **Status (v0.2):** every sample message converts to XML that **passes validation against the
> official seev.031.001.16 XSD** from iso20022.org. CI downloads the schema and repeats that check
> on Linux and Windows, Python 3.11–3.13. Option-level data (rates, cash amounts) is reported as
> dropped rather than guessed – see [Known limitations](#known-limitations) and
> [the mapping](docs/mapping.md#verification-status).

## The business problem

Custodians and CSDs notify account holders about corporate actions such as dividends,
rights issues, redemptions and tender offers. Many counterparties still exchange these
as MT564 messages. The ISO 20022 equivalent, seev.031, carries the same information
in a richer structure, and migrating to it means converting the notifications
without losing information silently. This bridge does that conversion and makes every
gap visible.

## What it does

For each MT564 in a file:

1. Parses blocks 1, 2 and 4, including the block 4 sequences (GENL, USECU, CADETL, ACCTINFO
   and so on). Each field keeps its line number.
2. Applies the mapping table in `mapping/mt564_to_seev031.toml`. Required fields that are
   missing, or values that cannot be converted, reject the message with a line reference.
3. Builds the seev.031 XML.
4. Validates the XML against the XSD configured in `bridge.toml`. If validation fails, no XML is
   written for that message.
5. Writes `<file>.report.json`: mapped fields, dropped fields with line numbers, warnings,
   and the validation result.

## Quick start

Requires Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Download the official schema (not committed; see schemas/README.md)
curl -fsSL -A "Mozilla/5.0" -o schemas/seev.031.001.16.xsd \
  https://www.iso20022.org/sites/default/files/documents/messages/seev/schemas/seev.031.001.16.xsd

mt564-bridge convert samples/mt564 --out out

# Development only, without a schema:
mt564-bridge convert samples/mt564 --out out --no-validate
```

Exit codes: `0` all messages converted, `1` at least one message rejected or a file failed to
parse, `2` bad configuration or input.

Output for each input message: `out/<file>_msgNN.seev031.xml`. One report per input file:
`out/<file>.report.json`.

## Supported fields

The full table, with the ISO paths and the status of each row, is in
[docs/mapping.md](docs/mapping.md). In short: sender reference, function of message (NEWM and
REPL), processing status, event reference, event type, mandatory or voluntary indicator, ISIN and
security description, safekeeping account, eligible balance (units or face amount, long or short),
and four dates.

## Design decisions

- **The mapping is data, not code.** Every rule is one `[[rule]]` block in a TOML file: source
  field, target path, a named transform, a status, and a note. The Python code contains no
  field-specific branches. A reviewer can read the table without reading the code. One MT field
  can feed several ISO elements (`25D::PROC` becomes both a completeness and a confirmation status).
- **Unknown is reported, not guessed.** Fields with no rule are listed as dropped, with their
  line numbers. Rates and cash amounts are dropped rather than placed in an option block whose
  mandatory data (option number, type) the message does not contain. Rules with a known gap are
  marked `partial`, and every use adds a warning.
- **No bad files.** Validation runs on the XML before anything is written. A failed message
  leaves a report with the XSD errors and no XML file.
- **Amounts stay as text.** Amounts and rates are only reformatted, from MT's comma decimal
  to ISO's point decimal, and the currency goes into the `Ccy` attribute. Nothing is ever
  converted to a float, so no rounding is introduced.
- **Small dependency footprint.** Only `lxml` is needed at runtime, because the standard library
  cannot validate XSD. `tomllib` is in the standard library from Python 3.11, so the mapping file
  needs no YAML parser.
- **Version is configuration.** `bridge.toml` names the seev.031 version. The XML namespace
  follows from it, so moving to a new release changes one line plus the XSD file.

### Module map

| Module | Responsibility |
|---|---|
| `parser.py` | Splits the file into messages and blocks. Groups block 4 into sequences and fields, with line numbers. |
| `models.py` | `Field` and `MT564Message` dataclasses. No XML or ISO knowledge. |
| `transforms.py` | Small named functions: MT date to ISO date, comma decimal to point, ISIN check, and so on. |
| `mapping.py` | Loads the rule table and applies it to a message. Records mapped, dropped and warnings. |
| `xml_builder.py` | Builds the XML tree from the mapped paths and serialises it. |
| `validation.py` | Loads the XSD and returns readable validation errors. |
| `reporting.py` | Builds report entries and writes the JSON report. |
| `converter.py` | Runs the pipeline for each file and message, and enforces the "no bad file" rule. |
| `config.py` | Reads `bridge.toml`. Relative paths resolve against the config file. |
| `cli.py` | The `mt564-bridge convert` command. Argparse only; no business logic. |

## Known limitations

- **Sequence E** (option and entitlement details) is parsed but not mapped, so rates
  (`92A::GRSS`, `92A::NETT`) and cash amounts (`19A::CASH`) are reported as dropped. In seev.031
  they belong to `CorpActnOptnDtls`, which needs an option number, option type and default flag.
- **MT564 field meanings and the 25D::PROC code pairs** follow my understanding of the standard
  and common market practice; check them against the current SWIFT MT Standards and SMPG
  guidance before production use. The ISO element paths themselves are verified by validation.
- **Ex-date** is mapped to `ExDvddDt` (the ex-dividend date); other event types may need a
  different element.
- **Function of message** supports NEWM and REPL only. RMDR, and the duplicate and copy
  sub-functions, are out of scope. **Processing status** supports COMP, COMU, PREC and PREU.
- **Safekeeping account** must be a specific account (`97A::SAFE`); `97C::SAFE//GENR` is not supported.
- **Block 3 and block 5** are ignored.
- **One direction only.** The bridge converts MT564 to seev.031. It does not convert the
  other way and does not handle MT566, MT568 or MT567.
- **ISIN check digits are not verified.** Only the shape is checked.

## Tests

```bash
pytest
```

86 tests cover the parser (including malformed input with line numbers), each transform,
the mapping rules, the XML builder, validation, the pipeline, and the CLI exit codes, with about
96% line coverage (printed after every run). One test converts every sample and validates it
against the official XSD; it skips with a clear message if the XSD is not in `schemas/`.

## Layout

```
bridge.toml                  configuration: schema version, XSD path, mapping file
mapping/mt564_to_seev031.toml  the declarative mapping table
docs/mapping.md              the mapping, for review
samples/mt564/               four synthetic sample files (five messages)
samples/generated/           XML and reports for the samples, validated against the official XSD
schemas/                     place the official XSD here (not committed)
src/mt564_bridge/            the package
tests/                       unit and integration tests, with toy schemas in tests/fixtures
```

All sample data is synthetic. ISINs, account numbers and references are invented and use
the `XX` prefix or the `SYN` and `SYNACC` patterns. No real client or bank data is included.

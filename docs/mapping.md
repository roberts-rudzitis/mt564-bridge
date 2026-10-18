# MT564 to seev.031 mapping (v1)

Target: **seev.031.001.16** (SR2026 release), root element `CorpActnNtfctn`, namespace
`urn:iso:std:iso:20022:tech:xsd:seev.031.001.16`.

This table mirrors `mapping/mt564_to_seev031.toml`. A test fails if a rule is missing here.

## Verification status

**Every ISO 20022 element path below is an assumption that has not been checked against
the official XSD.** The build environment could not download the schema. Search results
showed only fragments of older versions (for example seev.031.001.07 and .08), which
confirm some element names (`SfkpgAcct`, `AcctsListAndBalDtls`, `Bal`) but not the
nesting or the element order used in v1. Before relying on the output:

1. Download the official seev.031.001.16 XSD and place it at `schemas/seev.031.001.16.xsd`.
2. Run `mt564-bridge convert samples/mt564 --out out` without `--no-validate`.
3. Read each `validation_errors` entry. Each one points at a path or order that needs fixing
   in `mapping/mt564_to_seev031.toml`.

The MT field meanings and code values are also assumptions. Check them against the current
SWIFT MT Standards for MT564 and the ISO code lists.

## Status legend

- **mapped**: the same concept has a clean equivalent in seev.031.
- **partial**: an equivalent exists, but with a known gap or an unresolved question. Every use
  adds a warning to the report.

## Supported fields

| MT field | MT meaning (as I understand it) | ISO 20022 target (assumed path) | Status | Notes |
|---|---|---|---|---|
| `20C::SEME` | Sender's reference | `NtfctnGnlInf/NtfctnId` | partial | Required. Not verified whether this is the notification identifier or belongs in the business application header. |
| `20C::CORP` | Corporate action event reference | `CorpActnGnlInf/CorpActnEvtId` | mapped | Reference assigned by the account servicer. |
| `23G` | Function of the message | `NtfctnGnlInf/NtfctnTp/Cd` | partial | Required. NEWM and REPL only; other functions such as RMDR reject the message. Codes pass through unchanged, so they must match the ISO code list. |
| `22F::CAEV` | Corporate action event type | `CorpActnGnlInf/CorpActnEvtTp/Cd` | mapped | Required. Passed through as a four-letter code. Whether the code exists is decided by XSD validation. |
| `22F::CAMV` | Mandatory or voluntary indicator | `CorpActnGnlInf/MndtryVlntryEvtTp/Cd` | mapped | MAND or VOLU in the samples. |
| `98A::ANOU` | Announcement date | `CorpActnDtls/Dt/AnncmntDt` | mapped | YYYYMMDD becomes YYYY-MM-DD. |
| `98A::RDTE` | Record date | `CorpActnDtls/Dt/RcrdDt` | mapped | Optional. |
| `98A::EXDT` | Ex-date | `CorpActnDtls/Dt/ExDvddDt` | partial | `ExDvddDt` is the ex-dividend element. Other event types may need a different element. |
| `98A::PAYD` | Payment date | `CorpActnDtls/Dt/PmtDt` | mapped | |
| `35B` | Identification of the financial instrument | `FinInstrmId/ISIN` | partial | Required. Only the ISIN is mapped; the description line is dropped. The ISIN check digit is not verified. |
| `93B::ELIG` | Eligible balance | `AcctsListAndBalDtls/Bal/ElgblBal/Qty` | partial | UNIT and FAMT both become one quantity. ISO uses different types for them, so the distinction is lost. |
| `97A::SAFE` | Safekeeping account | `AcctsListAndBalDtls/SfkpgAcct` | mapped | The element name appears in XSD fragments; the parent nesting is unverified. |
| `92A::GRSS` | Gross rate | `CorpActnDtls/RateDtls/GrssRate` | partial | Whether the rate is a percentage or a per-unit amount depends on the event. |
| `92A::NETT` | Net rate | `CorpActnDtls/RateDtls/NetRate` | partial | Same basis question as the gross rate. |
| `19A::CASH` | Cash amount | `CorpActnDtls/CshPmt/Amt` | partial | Currency goes in the `Ccy` attribute. The `CshPmt` wrapper is an assumption. |

## Fields not mapped in v1

These are dropped and listed in each report, with their line numbers:

- Option and election details (for example the option or entitlement sequences).
- Narrative fields.
- Block 3 (user header) and block 5 (trailer). Block 3 is ignored, so its contents never reach the output.
- Any field not in the table above, including any repeated occurrence of a mapped field.

## Known gaps already documented by SWIFT and ISO

- An ISO change request notes that the documentation deadline date in seev.031 is not aligned
  with the ISO 15022 implementation. Documentation deadlines are not mapped in v1.
- An ISO change request for seev.031 renamed the security identification element to
  `FinancialInstrumentIdentification` in some versions. Element names change between
  versions, so the pinned version matters.

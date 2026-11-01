# MT564 to seev.031 mapping (v2)

Target: **seev.031.001.16** (SR2026 release), root element `CorpActnNtfctn`, namespace
`urn:iso:std:iso:20022:tech:xsd:seev.031.001.16`.

This table mirrors `mapping/mt564_to_seev031.toml`. A test fails if a rule is missing here.

## Verification status

- **Element paths and order: verified.** Every target path below was checked against the
  official `seev.031.001.16.xsd` published on iso20022.org (schema generated 26 Feb 2026), and all
  sample messages pass XSD validation. CI downloads the same schema and runs that check on every push.
- **Event and processing codes:** the event types used in the samples (DVCA, RHDI, REDM, PRED, TEND)
  exist in the schema's code list; other codes are checked by XSD validation at run time.
- **Still assumptions:** the MT564 field meanings and the 25D::PROC code pairs follow my
  understanding of the standards and common market practice (SMPG). Check them against the
  current SWIFT MT Standards release and the SMPG market practice before production use.

## Status legend

- **mapped**: the same concept has a clean equivalent in seev.031.
- **partial**: an equivalent exists, but with a known gap. Every use adds a warning to the report.

## Supported fields

| MT field | MT meaning | ISO 20022 target | Status | Notes |
|---|---|---|---|---|
| `20C::SEME` | Sender's reference | `NtfctnGnlInf/NtfctnId` | mapped | Required. In a full ISO exchange it may also go in the business application header. |
| `23G` | Function of the message | `NtfctnGnlInf/NtfctnTp` | partial | Required. NEWM and REPL only; other functions such as RMDR reject the message. |
| `25D::PROC` | Processing status | `NtfctnGnlInf/PrcgSts/Cd/EvtCmpltnsSts` | mapped | Required. COMP, COMU → COMP; PREC, PREU → INCO. |
| `25D::PROC` | Processing status | `NtfctnGnlInf/PrcgSts/Cd/EvtConfSts` | mapped | Required. COMP, PREC → CONF; COMU, PREU → UCON. Other codes (e.g. ENTL) reject the message. |
| `20C::CORP` | Corporate action event reference | `CorpActnGnlInf/CorpActnEvtId` | mapped | Required by seev.031. |
| `22F::CAEV` | Corporate action event type | `CorpActnGnlInf/EvtTp/Cd` | mapped | Required. Passed through; XSD validation decides whether the code exists. |
| `22F::CAMV` | Mandatory / voluntary indicator | `CorpActnGnlInf/MndtryVlntryEvtTp/Cd` | mapped | Required by seev.031 (MAND, CHOS, VOLU). |
| `35B` | Identification of the financial instrument | `CorpActnGnlInf/UndrlygScty/FinInstrmId/ISIN` | mapped | Required. The ISIN check digit is not verified. |
| `35B` | Security description lines | `CorpActnGnlInf/UndrlygScty/FinInstrmId/Desc` | mapped | Lines after the ISIN, joined with spaces; max. 140 characters; skipped when absent. |
| `97A::SAFE` | Safekeeping account | `AcctDtls/AcctsListAndBalDtls/SfkpgAcct` | mapped | Required (seev.031 needs account details). `97C::SAFE//GENR` is not supported. |
| `93B::ELIG` | Eligible balance – sign | `AcctDtls/AcctsListAndBalDtls/Bal/TtlElgblBal/Bal/QtyChc/SgndQty/ShrtLngPos` | mapped | `N` after the slash → SHOR, otherwise LONG. |
| `93B::ELIG` | Eligible balance – units | `AcctDtls/AcctsListAndBalDtls/Bal/TtlElgblBal/Bal/QtyChc/SgndQty/Qty/Unit` | mapped | `UNIT/` balances only. |
| `93B::ELIG` | Eligible balance – face amount | `AcctDtls/AcctsListAndBalDtls/Bal/TtlElgblBal/Bal/QtyChc/SgndQty/Qty/FaceAmt` | mapped | `FAMT/` balances only. |
| `98A::ANOU` | Announcement date | `CorpActnDtls/DtDtls/AnncmntDt/Dt/Dt` | mapped | YYYYMMDD becomes YYYY-MM-DD. Note the extra `Dt` level for this date type. |
| `98A::RDTE` | Record date | `CorpActnDtls/DtDtls/RcrdDt/Dt` | mapped | Optional. |
| `98A::EXDT` | Ex-date | `CorpActnDtls/DtDtls/ExDvddDt/Dt` | partial | `ExDvddDt` is the ex-dividend date; other event types may need a different element. |
| `98A::PAYD` | Payment date | `CorpActnDtls/DtDtls/PmtDt/Dt` | mapped | |

## Fields not mapped in v2

These are dropped and listed in each report with their line numbers:

- **Rates and cash amounts** (for example `92A::GRSS`, `92A::NETT`, `19A::CASH`). In seev.031 they
  belong to the option details (`CorpActnOptnDtls/CshMvmntDtls/...`), which also require an option
  number, option type and default-option flag – data that comes from MT564 sequence E. Mapping
  them without that data would mean inventing values, so they are reported as dropped instead.
  The `rate` and `amount` transforms are kept for that next step.
- Option and entitlement sequences (sequence E) in general.
- Narrative fields.
- Block 3 (user header) and block 5 (trailer).
- Any field not in the table above, including any repeated occurrence of a mapped field.

## Version notes

- Element names change between seev.031 versions (for example the event type element is `EvtTp`
  in .001.16, and `NtfctnTp` is a plain code rather than a nested choice), so the pinned version
  in `bridge.toml` and the XSD must match.

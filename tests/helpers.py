"""Shared test helpers: build synthetic MT564 text, and locate the repository and samples."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples" / "mt564"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# A complete, valid v1 message, one line per block 4 entry.
BASE = [
    ":16R:GENL",
    ":20C::SEME//SYN564TEST01",
    ":23G:NEWM",
    ":22F::CAEV//DVCA",
    ":22F::CAMV//MAND",
    ":98A::PAYD//20261105",
    ":25D::PROC//COMP",
    ":20C::CORP//SYNCA2026TEST",
    ":16S:GENL",
    ":16R:USECU",
    ":35B:ISIN XX1234567897",
    "SYNTHETIC EQUITY ALPHA",
    ":16S:USECU",
    ":16R:ACCTINFO",
    ":97A::SAFE//SYNACC000123",
    ":93B::ELIG//UNIT/2000,",
    ":16S:ACCTINFO",
]


def make_mt(body_lines, *, sender="SYNTHBANKAXX", receiver="SYNTHCUSTXXX", block2_type="564"):
    """Wrap block 4 lines in blocks 1, 2 and 4, with the same envelope the samples use."""
    return (
        f"{{1:F01{sender}0000000000}}"
        f"{{2:I{block2_type}{receiver}N}}"
        "{4:\n" + "\n".join(body_lines) + "\n-}"
    )

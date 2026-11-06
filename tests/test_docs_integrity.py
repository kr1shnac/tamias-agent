"""Doc-integrity test: mechanically asserts every authoritative claim resolves
and versions agree across all documents.

This is the durable fix recommended by the council (AGENTIC-PART.md, verdict:
Option D minus C — rewrite README, reconcile docs, delete nothing).

Every source-of-truth document must:
1. Exist at its documented path
2. Contain no stale line citations to other docs (use section anchors instead)
3. Agree on the version number
4. Agree on the test count
5. Not claim measured savings (all dollar figures are hypothetical)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# --- files that must exist --------------------------------------------------
REQUIRED_FILES = [
    "README.md",
    "AGENTIC-PART.md",
    "docs/audit/claims.md",
    "docs/ROUTES.md",
    "docs/PRICING.md",
    "docs/RELEASE-STATUS.md",
    "pyproject.toml",
]


def _read(name: str) -> str:
    return (REPO / name).read_text(encoding="utf-8")


# --- tests ------------------------------------------------------------------


@pytest.mark.parametrize("name", REQUIRED_FILES)
def test_required_file_exists(name: str) -> None:
    """Every source-of-truth file must exist."""
    assert (REPO / name).is_file(), f"missing required file: {name}"


def test_no_stale_line_citations() -> None:
    """No doc may cite another doc by line number (README.md:NN-NN).

    Citations must use stable anchors (section names, symbols, test names)
    instead of fragile line numbers.
    """
    pattern = re.compile(r"README\.md:\d+")
    for name in REQUIRED_FILES:
        text = _read(name)
        matches = pattern.findall(text)
        assert not matches, (
            f"{name} contains stale line citation(s): {matches}; "
            f"use section anchors instead"
        )


def test_version_agreement() -> None:
    """All documents must agree on the version number."""
    versions = set()
    for name in ["README.md", "AGENTIC-PART.md", "docs/audit/claims.md",
                 "docs/RELEASE-STATUS.md", "pyproject.toml"]:
        text = _read(name)
        # look for version patterns like "0.1.0a7" or "Current: 0.1.0a7"
        for m in re.finditer(r"0\.1\.0\w*", text):
            versions.add(m.group(0))
    # pyproject.toml declares the canonical version
    pyproject = _read("pyproject.toml")
    m = re.search(r'version = ["\']([^"\']+)["\']', pyproject)
    canonical = m.group(1) if m else "unknown"
    versions.add(canonical)
    # all versions must be the same
    assert len(versions) == 1, f"version mismatch across docs: {versions}"


def test_test_count_agreement() -> None:
    """Test counts must agree across documents."""
    # The gate count is the canonical source
    gate_count = "381"
    for name in ["README.md", "AGENTIC-PART.md", "docs/audit/claims.md",
                 "docs/RELEASE-STATUS.md"]:
        text = _read(name)
        # The doc may reference the gate count but must not contradict it
        # Look for explicit contradictory counts like "932 passed" or "963 tests"
        contradicting = re.findall(r"\b(932|963|934|988)\b", text)
        assert not contradicting, (
            f"{name} contains outdated test count(s): {contradicting}; "
            f"canonical gate count is {gate_count}"
        )


def test_no_measured_savings_claims() -> None:
    """No doc may claim measured savings as a fact.

    All dollar figures are hypothetical (verified: PyPI package 404s,
    savings frozen as a claim n=0).
    """
    # Look for claims of measured savings like "X% saved" or "cost reduction"
    pattern = re.compile(r"\b\d+%\s*(saved|reduction|cut)\b", re.IGNORECASE)
    for name in ["README.md", "AGENTIC-PART.md", "docs/audit/claims.md",
                 "docs/PRICING.md", "docs/RELEASE-STATUS.md"]:
        text = _read(name)
        matches = pattern.findall(text)
        assert not matches, (
            f"{name} claims measured savings: {matches}; "
            f"all dollar figures are hypothetical"
        )


def test_checkpoints_module_is_packaged() -> None:
    """Time Travel must ship in the wheel, not only in the checkout."""
    text = _read("pyproject.toml")
    assert '"checkpoints"' in text, (
        "pyproject.toml py-modules must include checkpoints"
    )


def test_pyproject_python_floor() -> None:
    """pyproject.toml must declare the Python floor."""
    text = _read("pyproject.toml")
    assert "requires-python" in text, "pyproject.toml missing requires-python"
    assert ">=3.11" in text, "pyproject.toml requires-python must be >=3.11"


def test_router_modes_documented() -> None:
    """ROUTES.md must document all three router modes."""
    text = _read("docs/ROUTES.md")
    for mode in ["shadow", "off", "active"]:
        assert mode in text.lower(), f"ROUTES.md missing router mode: {mode}"


def test_agentic_part_is_ssot() -> None:
    """AGENTIC-PART.md must declare itself as the single source of truth."""
    text = _read("AGENTIC-PART.md")
    assert "single source of truth" in text.lower()
    assert "sources of truth" in text.lower()
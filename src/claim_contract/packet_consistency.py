"""Verify an explicit Markdown summary against returned contracts and validator JSON.

This is a deterministic handoff-consistency check, not evidence verification.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote

from .io import load_contract
from .validator import validate_contract


PACKET_VERIFY_SCOPE_NOTICE = (
    "Packet summary, saved report, and declared-contract consistency only. "
    "This does not authenticate a report or scientifically validate a claim."
)

_HEADERS = ("contract", "claim text", "verdict", "findings", "report")
_LINK = re.compile(r"^\[[^\]\n]+\]\(([^()\s]+)\)$")
_FINDING = re.compile(r"^CC[0-9]{3}/(?:REVIEW|BLOCK)/[A-Za-z0-9_.\[\]-]+$")
_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_DRIVE = re.compile(r"^[A-Za-z]:")

_FIELDS = (
    "schema_version", "type", "contract", "verdict", "profile",
    "claim_text", "scientific_validation", "scope_notice",
    "not_evaluated", "summary", "findings",
)


@dataclass(frozen=True)
class PacketConsistencyFailure:
    line: int
    code: str
    target: str
    reason: str


@dataclass(frozen=True)
class PacketConsistencyResult:
    rows_checked: int
    failures: tuple[PacketConsistencyFailure, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "rows_checked": self.rows_checked,
            "failures": [asdict(failure) for failure in self.failures],
        }


@dataclass(frozen=True)
class _SummaryRow:
    line: int
    contract_target: str
    claim_text: str
    verdict: str
    findings: str
    report_target: str


def _split_row(line: str) -> list[str]:
    """Split a restricted Markdown row; require literal pipes to be escaped."""
    line = line.strip()
    if not line.startswith("|") or not line.endswith("|"):
        raise ValueError("Expected a pipe-delimited Markdown table row")
    return [
        cell.strip().replace(r"\|", "|")
        for cell in re.split(r"(?<!\\)\|", line[1:-1])
    ]


def _parse_table(markdown: str) -> tuple[list[_SummaryRow], list[PacketConsistencyFailure], int]:
    lines = markdown.splitlines()
    headings = [i for i, line in enumerate(lines) if line.strip() == "## Validation summary"]
    if len(headings) != 1:
        return [], [PacketConsistencyFailure(
            1, "SUMMARY_SECTION", "packet.md",
            "Expected exactly one '## Validation summary' section",
        )], 1

    position = headings[0] + 1
    while position < len(lines) and not lines[position].strip():
        position += 1
    table_line = position + 1
    failures: list[PacketConsistencyFailure] = []
    if position + 1 >= len(lines):
        failures.append(PacketConsistencyFailure(
            table_line, "SUMMARY_TABLE", "packet.md", "Missing validation summary table",
        ))
        return [], failures, table_line

    try:
        header = _split_row(lines[position])
        separator = _split_row(lines[position + 1])
    except ValueError as exc:
        failures.append(PacketConsistencyFailure(
            table_line, "SUMMARY_TABLE", "packet.md", str(exc),
        ))
        return [], failures, table_line

    if tuple(cell.lower() for cell in header) != _HEADERS:
        failures.append(PacketConsistencyFailure(
            table_line, "SUMMARY_COLUMNS", "packet.md",
            "Expected columns: Contract | Claim text | Verdict | Findings | Report",
        ))
        return [], failures, table_line
    if len(separator) != 5 or not all(_SEPARATOR.fullmatch(cell) for cell in separator):
        failures.append(PacketConsistencyFailure(
            table_line + 1, "SUMMARY_SEPARATOR", "packet.md", "Malformed table separator",
        ))
        return [], failures, table_line

    rows: list[_SummaryRow] = []
    for i in range(position + 2, len(lines)):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            break
        try:
            cells = _split_row(raw)
        except ValueError as exc:
            failures.append(PacketConsistencyFailure(i + 1, "SUMMARY_ROW", "packet.md", str(exc)))
            continue
        if len(cells) != 5:
            failures.append(PacketConsistencyFailure(
                i + 1, "SUMMARY_ROW", "packet.md", "Expected exactly five table cells",
            ))
            continue
        contract, claim, verdict, findings, report = cells
        contract_match, report_match = _LINK.fullmatch(contract), _LINK.fullmatch(report)
        if not contract_match or not report_match:
            failures.append(PacketConsistencyFailure(
                i + 1, "SUMMARY_LINK", "packet.md",
                "Contract and Report cells must be plain relative Markdown links",
            ))
            continue
        rows.append(_SummaryRow(
            i + 1, contract_match.group(1), claim, verdict,
            findings, report_match.group(1),
        ))

    if not rows:
        failures.append(PacketConsistencyFailure(
            table_line, "SUMMARY_EMPTY", "packet.md",
            "Validation summary must include at least one contract/report row",
        ))
    return rows, failures, table_line


def _resolve_target(root: Path, target: str, kind: str) -> Path:
    raw = unquote(target)
    if (
        not raw or raw.startswith(("/", "\\", "#")) or "\\" in raw
        or "?" in raw or "#" in raw or "://" in raw
        or _DRIVE.match(raw) or raw.lower().startswith("file:")
    ):
        raise ValueError("Expected a local relative path without query or fragment")
    path = (root / raw).resolve()
    directory = (root / kind).resolve()
    if not path.is_relative_to(directory) or path == directory:
        raise ValueError(f"Target must be inside the {kind}/ directory")
    if kind == "contracts" and path.suffix.lower() not in {".yaml", ".yml", ".json"}:
        raise ValueError("Contract target must be YAML or JSON")
    if kind == "validate" and path.suffix.lower() != ".json":
        raise ValueError("Report target must be JSON")
    return path


def _strict_equal(left: object, right: object) -> bool:
    """Compare full JSON values without Python's True == 1 / False == 0 collapse."""
    return json.dumps(left, sort_keys=True, separators=(",", ":"), allow_nan=False) == (
        json.dumps(right, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


def _reject_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON numeric constant: {value}")


def _reported_findings(value: str) -> Counter[str]:
    if value == "-":
        return Counter()
    tokens = [piece.strip().strip(chr(96)) for piece in value.split(";")]
    if not tokens or not all(_FINDING.fullmatch(token) for token in tokens):
        raise ValueError(
            "Findings must be '-' or semicolon-separated RULE/SEVERITY/path entries"
        )
    return Counter(tokens)


def _actual_findings(report: dict[str, object]) -> Counter[str]:
    items = report.get("findings")
    if not isinstance(items, list):
        raise ValueError("Report findings must be a list")
    tokens: list[str] = []
    for finding in items:
        if not isinstance(finding, dict):
            raise ValueError("Report findings must contain objects")
        tokens.append(
            f"{finding.get('rule_id')}/{finding.get('severity')}/{finding.get('path')}"
        )
    return Counter(tokens)


def _validate_row(
    root: Path,
    row: _SummaryRow,
    add,
) -> tuple[Path | None, Path | None]:
    def fail(code: str, target: str, reason: str) -> None:
        add(PacketConsistencyFailure(row.line, code, target, reason))

    try:
        contract_path = _resolve_target(root, row.contract_target, "contracts")
        report_path = _resolve_target(root, row.report_target, "validate")
    except ValueError as exc:
        fail("INVALID_TARGET", f"{row.contract_target} | {row.report_target}", str(exc))
        return None, None

    relative = contract_path.relative_to((root / "contracts").resolve())
    expected_report = ((root / "validate") / relative.with_suffix(".json")).resolve()
    if report_path != expected_report:
        fail("REPORT_MAPPING", row.report_target,
             f"Expected report for {row.contract_target}: {expected_report.relative_to(root)}")

    if not contract_path.is_file():
        fail("MISSING_CONTRACT", row.contract_target, "Linked contract file is missing")
        return contract_path, report_path
    if not report_path.is_file():
        fail("MISSING_REPORT", row.report_target, "Linked validator report is missing")
        return contract_path, report_path

    try:
        contract = load_contract(contract_path)
        saved = json.loads(
            report_path.read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
        )
        if not isinstance(saved, dict):
            raise ValueError("Report root must be an object")
        expected = validate_contract(contract).to_dict()
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        fail("ARTIFACT_INPUT", row.report_target, f"Could not inspect contract/report: {exc}")
        return contract_path, report_path

    # Recompute deterministic contract findings; tool.version is intentionally
    # excluded because its release value can differ without changing semantics.
    for field in _FIELDS:
        if not _strict_equal(saved.get(field), expected.get(field)):
            fail("SAVED_REPORT_DRIFT", row.report_target,
                 f"Saved report field {field!r} disagrees with current validator output")

    claim = contract.get("claim")
    declared = claim.get("text") if isinstance(claim, dict) else None
    if row.claim_text != declared:
        fail("CLAIM_TEXT", row.contract_target,
             "Table claim text differs from the exact declared claim.text")
    if row.claim_text != saved.get("claim_text"):
        fail("REPORT_CLAIM_TEXT", row.report_target,
             "Table claim text differs from saved report.claim_text")
    if row.verdict not in {"READY", "REVIEW", "BLOCK"}:
        fail("VERDICT_FORMAT", row.report_target, "Verdict must be READY, REVIEW, or BLOCK")
    elif row.verdict != saved.get("verdict"):
        fail("VERDICT_MISMATCH", row.report_target,
             f"Table verdict {row.verdict} differs from saved report verdict {saved.get('verdict')}")
    try:
        listed = _reported_findings(row.findings)
        actual = _actual_findings(saved)
        if listed != actual:
            missing = sorted((actual - listed).elements())
            extra = sorted((listed - actual).elements())
            fail("FINDINGS_MISMATCH", row.report_target,
                 f"Table findings differ from saved report (missing={missing}, extra={extra})")
    except ValueError as exc:
        fail("FINDINGS_FORMAT", row.report_target, str(exc))
    return contract_path, report_path


def verify_packet_consistency(packet: Path) -> PacketConsistencyResult:
    """Inspect explicit table rows and account for returned contract/report files."""
    markdown = packet.read_text(encoding="utf-8")
    root = packet.resolve().parent
    rows, failures, table_line = _parse_table(markdown)
    seen_contracts: set[Path] = set()
    seen_reports: set[Path] = set()

    for row in rows:
        contract_path, report_path = _validate_row(root, row, failures.append)
        if contract_path is not None:
            if contract_path in seen_contracts:
                failures.append(PacketConsistencyFailure(
                    row.line, "DUPLICATE_CONTRACT", row.contract_target,
                    "Contract appears more than once in summary",
                ))
            seen_contracts.add(contract_path)
        if report_path is not None:
            if report_path in seen_reports:
                failures.append(PacketConsistencyFailure(
                    row.line, "DUPLICATE_REPORT", row.report_target,
                    "Report appears more than once in summary",
                ))
            seen_reports.add(report_path)

    for kind, seen, extensions, code in (
        ("contracts", seen_contracts, {".yaml", ".yml", ".json"}, "UNLISTED_CONTRACT"),
        ("validate", seen_reports, {".json"}, "UNLISTED_REPORT"),
    ):
        folder = root / kind
        if not folder.is_dir():
            failures.append(PacketConsistencyFailure(
                table_line, "MISSING_DIRECTORY", kind, f"Required {kind}/ directory is missing",
            ))
            continue
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in extensions:
                if path.resolve() not in seen:
                    failures.append(PacketConsistencyFailure(
                        table_line, code, str(path.relative_to(root)),
                        f"{kind}/ artifact is not represented in validation summary",
                    ))

    return PacketConsistencyResult(rows_checked=len(rows), failures=tuple(failures))

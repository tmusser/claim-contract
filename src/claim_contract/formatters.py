from __future__ import annotations

import json
from typing import Any

from .metadata import ERROR_SCHEMA_VERSION, ERROR_TYPE, TOOL_NAME, TOOL_VERSION
from .models import NOT_EVALUATED, SCOPE_NOTICE, Report


def format_text(report: Report) -> str:
    lines = [
        f"Verdict: {report.verdict.value}",
        f"Profile: {report.profile}",
        f"Scientific validation: {str(report.scientific_validation).lower()}",
        f"Scope: {report.scope_notice}",
        "",
    ]

    if report.findings:
        for finding in report.findings:
            lines.extend(
                [
                    f"{finding.severity.value} {finding.rule_id} {finding.path}",
                    f"  {finding.message}",
                    f"  Action: {finding.action}",
                    "",
                ]
            )
    else:
        lines.extend(["No REVIEW or BLOCK rules fired.", ""])

    lines.append("Not evaluated:")
    lines.extend(f"- {item}" for item in report.not_evaluated)
    return "\n".join(lines)


def format_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def error_payload(message: str, code: str = "INPUT_ERROR") -> dict[str, Any]:
    """Return a versioned error envelope that preserves interpretation limits."""

    return {
        "schema_version": ERROR_SCHEMA_VERSION,
        "type": ERROR_TYPE,
        "tool": {
            "name": TOOL_NAME,
            "version": TOOL_VERSION,
        },
        "error": {
            "code": code,
            "message": message,
        },
        "scientific_validation": False,
        "scope_notice": SCOPE_NOTICE,
        "not_evaluated": list(NOT_EVALUATED),
    }


def format_json_error(message: str, code: str = "INPUT_ERROR") -> str:
    return json.dumps(error_payload(message, code), indent=2, sort_keys=True)

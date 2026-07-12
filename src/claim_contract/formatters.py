from __future__ import annotations

import json

from .models import Report


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

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .metadata import (
    CONTRACT_DIFF_SCHEMA_VERSION,
    CONTRACT_DIFF_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)
from .validator import validate_contract


_SCOPE_NOTICE = (
    "This artifact reports mechanical differences between two parsed contracts and their "
    "claim-contract verdicts. It does not explain why a change is scientifically appropriate, "
    "approve a revision, or validate the underlying analysis."
)
_NOT_EVALUATED = (
    "whether either contract's declarations are true or complete",
    "whether a changed field is scientifically or statistically appropriate",
    "whether the revision was made to satisfy the validator rather than improve the analysis",
    "whether either analytical claim is useful, causal, reproducible, unbiased, or decision-worthy",
)
_MISSING = object()


@dataclass(frozen=True)
class ContractChange:
    path: str
    change_type: str
    before_present: bool
    after_present: bool
    before: Any = None
    after: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "change_type": self.change_type,
            "before_present": self.before_present,
            "after_present": self.after_present,
            "before": self.before if self.before_present else None,
            "after": self.after if self.after_present else None,
        }


@dataclass(frozen=True)
class ContractDiff:
    before_verdict: str
    after_verdict: str
    changes: tuple[ContractChange, ...]

    @property
    def changed(self) -> bool:
        return bool(self.changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": CONTRACT_DIFF_SCHEMA_VERSION,
            "type": CONTRACT_DIFF_TYPE,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "scientific_validation": False,
            "automatic_interpretation": False,
            "scope_notice": _SCOPE_NOTICE,
            "not_evaluated": list(_NOT_EVALUATED),
            "verdict_transition": {
                "before": self.before_verdict,
                "after": self.after_verdict,
                "changed": self.before_verdict != self.after_verdict,
            },
            "contract_changed": self.changed,
            "change_count": len(self.changes),
            "changes": [change.to_dict() for change in self.changes],
        }


def _join_path(parent: str, key: str) -> str:
    return f"{parent}.{key}" if parent else key


def _collect_changes(before: Any, after: Any, path: str) -> list[ContractChange]:
    if isinstance(before, Mapping) and isinstance(after, Mapping):
        changes: list[ContractChange] = []
        keys = sorted(set(before) | set(after), key=str)
        for key in keys:
            key_text = str(key)
            child_path = _join_path(path, key_text)
            before_value = before.get(key, _MISSING)
            after_value = after.get(key, _MISSING)
            if before_value is _MISSING:
                changes.append(
                    ContractChange(
                        path=child_path,
                        change_type="added",
                        before_present=False,
                        after_present=True,
                        after=after_value,
                    )
                )
            elif after_value is _MISSING:
                changes.append(
                    ContractChange(
                        path=child_path,
                        change_type="removed",
                        before_present=True,
                        after_present=False,
                        before=before_value,
                    )
                )
            else:
                changes.extend(_collect_changes(before_value, after_value, child_path))
        return changes

    if isinstance(before, list) and isinstance(after, list):
        if before == after:
            return []
        return [
            ContractChange(
                path=path,
                change_type="changed",
                before_present=True,
                after_present=True,
                before=before,
                after=after,
            )
        ]

    if before == after:
        return []

    return [
        ContractChange(
            path=path,
            change_type="changed",
            before_present=True,
            after_present=True,
            before=before,
            after=after,
        )
    ]


def build_contract_diff(
    before_contract: Mapping[str, Any],
    after_contract: Mapping[str, Any],
) -> ContractDiff:
    before_report = validate_contract(dict(before_contract))
    after_report = validate_contract(dict(after_contract))
    changes = tuple(_collect_changes(before_contract, after_contract, ""))
    return ContractDiff(
        before_verdict=before_report.verdict.value,
        after_verdict=after_report.verdict.value,
        changes=changes,
    )

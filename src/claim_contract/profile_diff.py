from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .binding import ProfileManifestBinding, build_profile_manifest_binding
from .metadata import (
    PROFILE_DIFF_SCHEMA_VERSION,
    PROFILE_DIFF_TYPE,
    PROFILE_MANIFEST_SCHEMA_VERSION,
    PROFILE_MANIFEST_TYPE,
    TOOL_NAME,
    TOOL_VERSION,
)


_SCOPE_NOTICE = (
    "This artifact reports mechanical differences between two machine-readable profile "
    "manifests. It does not classify compatibility, scientific validity, or whether a "
    "profile change is safe, breaking, desirable, or correct."
)
_NOT_EVALUATED = (
    "whether either profile is scientifically valid or sufficient",
    "whether a rule addition, removal, or metadata change is safe or breaking",
    "whether changed rule metadata accurately describes executable validator behavior",
    "whether downstream consumers remain compatible with either profile",
)
_RULE_FIELDS = ("severity", "consumed_fields", "trigger", "known_boundary")
_REQUIRED_TOP_LEVEL = {
    "schema_version",
    "type",
    "tool",
    "profile",
    "scientific_validation",
    "scope_notice",
    "not_evaluated",
    "rule_count",
    "rules",
}
_REQUIRED_RULE_FIELDS = {"id", *_RULE_FIELDS}
_RULE_ID_RE = re.compile(r"^CC[0-9]{3}$")


@dataclass(frozen=True)
class ProfileFieldChange:
    path: str
    before: Any
    after: Any

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "before": self.before, "after": self.after}


@dataclass(frozen=True)
class RuleFieldChange:
    field: str
    before: Any
    after: Any

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "before": self.before, "after": self.after}


@dataclass(frozen=True)
class RuleChange:
    rule_id: str
    changes: tuple[RuleFieldChange, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.rule_id,
            "changes": [change.to_dict() for change in self.changes],
        }


@dataclass(frozen=True)
class ProfileDiff:
    before_profile: str
    after_profile: str
    before_binding: ProfileManifestBinding
    after_binding: ProfileManifestBinding
    tool_metadata_changed: bool
    profile_changes: tuple[ProfileFieldChange, ...]
    rules_added: tuple[dict[str, Any], ...]
    rules_removed: tuple[dict[str, Any], ...]
    rules_changed: tuple[RuleChange, ...]
    before_rule_order: tuple[str, ...]
    after_rule_order: tuple[str, ...]
    rule_order_changed: bool

    @property
    def semantic_changed(self) -> bool:
        return self.before_binding != self.after_binding

    @property
    def change_count(self) -> int:
        return (
            len(self.profile_changes)
            + len(self.rules_added)
            + len(self.rules_removed)
            + sum(len(rule.changes) for rule in self.rules_changed)
            + int(self.rule_order_changed)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROFILE_DIFF_SCHEMA_VERSION,
            "type": PROFILE_DIFF_TYPE,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "scientific_validation": False,
            "automatic_compatibility_classification": False,
            "scope_notice": _SCOPE_NOTICE,
            "not_evaluated": list(_NOT_EVALUATED),
            "before": {
                "profile": self.before_profile,
                "profile_manifest_binding": self.before_binding.to_dict(),
            },
            "after": {
                "profile": self.after_profile,
                "profile_manifest_binding": self.after_binding.to_dict(),
            },
            "semantic_changed": self.semantic_changed,
            "tool_metadata_changed": self.tool_metadata_changed,
            "change_count": self.change_count,
            "profile_changes": [change.to_dict() for change in self.profile_changes],
            "rules_added": list(self.rules_added),
            "rules_removed": list(self.rules_removed),
            "rules_changed": [change.to_dict() for change in self.rules_changed],
            "rule_order": {
                "changed": self.rule_order_changed,
                "before": list(self.before_rule_order),
                "after": list(self.after_rule_order),
            },
        }


def load_profile_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    if manifest_path.suffix.lower() != ".json":
        raise ValueError("Profile manifest must be JSON (.json).")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Profile manifest not found: {manifest_path}")

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Profile manifest is not valid JSON: {manifest_path}: {exc.msg}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("Profile manifest root must be an object/mapping.")
    validate_profile_manifest(payload)
    return payload


def validate_profile_manifest(payload: Mapping[str, Any]) -> None:
    if set(payload) != _REQUIRED_TOP_LEVEL:
        missing = sorted(_REQUIRED_TOP_LEVEL - set(payload))
        extra = sorted(set(payload) - _REQUIRED_TOP_LEVEL)
        details = []
        if missing:
            details.append(f"missing fields: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected fields: {', '.join(extra)}")
        raise ValueError("Invalid profile manifest shape (" + "; ".join(details) + ").")

    if payload.get("type") != PROFILE_MANIFEST_TYPE:
        raise ValueError(
            f"Expected profile manifest type {PROFILE_MANIFEST_TYPE!r}; "
            f"got {payload.get('type')!r}."
        )
    if payload.get("schema_version") != PROFILE_MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            "Unsupported profile manifest schema version: "
            f"{payload.get('schema_version')!r}."
        )
    if payload.get("scientific_validation") is not False:
        raise ValueError("Profile manifest scientific_validation must be false.")

    tool = payload.get("tool")
    if not isinstance(tool, Mapping):
        raise ValueError("Profile manifest tool must be an object/mapping.")
    if tool.get("name") != TOOL_NAME:
        raise ValueError(f"Profile manifest tool.name must be {TOOL_NAME!r}.")
    if not isinstance(tool.get("version"), str) or not tool.get("version"):
        raise ValueError("Profile manifest tool.version must be a non-empty string.")

    profile = payload.get("profile")
    if not isinstance(profile, Mapping):
        raise ValueError("Profile manifest profile must be an object/mapping.")
    if set(profile) != {"name", "contract_schema", "description"}:
        raise ValueError(
            "Profile manifest profile must contain exactly name, contract_schema, and description."
        )
    for field in ("name", "contract_schema", "description"):
        if not isinstance(profile.get(field), str) or not profile.get(field):
            raise ValueError(f"Profile manifest profile.{field} must be a non-empty string.")

    scope_notice = payload.get("scope_notice")
    if not isinstance(scope_notice, str) or not scope_notice:
        raise ValueError("Profile manifest scope_notice must be a non-empty string.")

    not_evaluated = payload.get("not_evaluated")
    if (
        not isinstance(not_evaluated, list)
        or not not_evaluated
        or any(not isinstance(item, str) or not item for item in not_evaluated)
    ):
        raise ValueError("Profile manifest not_evaluated must be a non-empty string list.")

    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("Profile manifest rules must be a non-empty list.")
    rule_count = payload.get("rule_count")
    if isinstance(rule_count, bool) or not isinstance(rule_count, int) or rule_count < 1:
        raise ValueError("Profile manifest rule_count must be a positive integer.")
    if rule_count != len(rules):
        raise ValueError("Profile manifest rule_count must equal the number of rules.")

    seen_ids: set[str] = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, Mapping):
            raise ValueError(f"Profile manifest rules[{index}] must be an object/mapping.")
        if set(rule) != _REQUIRED_RULE_FIELDS:
            raise ValueError(
                f"Profile manifest rule at index {index} has unsupported fields."
            )
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not _RULE_ID_RE.fullmatch(rule_id):
            raise ValueError(f"Profile manifest rule at index {index} has invalid id.")
        if rule_id in seen_ids:
            raise ValueError(f"Duplicate profile manifest rule id: {rule_id}.")
        seen_ids.add(rule_id)
        if rule.get("severity") not in {"REVIEW", "BLOCK"}:
            raise ValueError(f"Profile manifest rule {rule_id} has invalid severity.")
        consumed_fields = rule.get("consumed_fields")
        if (
            not isinstance(consumed_fields, list)
            or not consumed_fields
            or any(not isinstance(item, str) or not item for item in consumed_fields)
            or len(consumed_fields) != len(set(consumed_fields))
        ):
            raise ValueError(
                f"Profile manifest rule {rule_id} consumed_fields must be unique non-empty strings."
            )
        for field in ("trigger", "known_boundary"):
            if not isinstance(rule.get(field), str) or not rule.get(field):
                raise ValueError(
                    f"Profile manifest rule {rule_id} {field} must be a non-empty string."
                )


def _profile_field_changes(
    before: Mapping[str, Any], after: Mapping[str, Any]
) -> tuple[ProfileFieldChange, ...]:
    pairs = (
        ("profile.name", before["profile"]["name"], after["profile"]["name"]),
        (
            "profile.contract_schema",
            before["profile"]["contract_schema"],
            after["profile"]["contract_schema"],
        ),
        (
            "profile.description",
            before["profile"]["description"],
            after["profile"]["description"],
        ),
        ("scope_notice", before["scope_notice"], after["scope_notice"]),
        ("not_evaluated", before["not_evaluated"], after["not_evaluated"]),
    )
    return tuple(
        ProfileFieldChange(path=path, before=before_value, after=after_value)
        for path, before_value, after_value in pairs
        if before_value != after_value
    )


def build_profile_diff(
    before_manifest: Mapping[str, Any], after_manifest: Mapping[str, Any]
) -> ProfileDiff:
    validate_profile_manifest(before_manifest)
    validate_profile_manifest(after_manifest)

    before_rules = {rule["id"]: dict(rule) for rule in before_manifest["rules"]}
    after_rules = {rule["id"]: dict(rule) for rule in after_manifest["rules"]}
    before_ids = tuple(rule["id"] for rule in before_manifest["rules"])
    after_ids = tuple(rule["id"] for rule in after_manifest["rules"])
    common_ids = set(before_rules) & set(after_rules)

    added_ids = sorted(set(after_rules) - set(before_rules))
    removed_ids = sorted(set(before_rules) - set(after_rules))
    rules_added = tuple(after_rules[rule_id] for rule_id in added_ids)
    rules_removed = tuple(before_rules[rule_id] for rule_id in removed_ids)

    changed_rules: list[RuleChange] = []
    for rule_id in sorted(common_ids):
        field_changes = tuple(
            RuleFieldChange(
                field=field,
                before=before_rules[rule_id][field],
                after=after_rules[rule_id][field],
            )
            for field in _RULE_FIELDS
            if before_rules[rule_id][field] != after_rules[rule_id][field]
        )
        if field_changes:
            changed_rules.append(RuleChange(rule_id=rule_id, changes=field_changes))

    before_common_order = tuple(rule_id for rule_id in before_ids if rule_id in common_ids)
    after_common_order = tuple(rule_id for rule_id in after_ids if rule_id in common_ids)
    rule_order_changed = before_common_order != after_common_order

    diff = ProfileDiff(
        before_profile=str(before_manifest["profile"]["name"]),
        after_profile=str(after_manifest["profile"]["name"]),
        before_binding=build_profile_manifest_binding(before_manifest),
        after_binding=build_profile_manifest_binding(after_manifest),
        tool_metadata_changed=before_manifest["tool"] != after_manifest["tool"],
        profile_changes=_profile_field_changes(before_manifest, after_manifest),
        rules_added=rules_added,
        rules_removed=rules_removed,
        rules_changed=tuple(changed_rules),
        before_rule_order=before_ids,
        after_rule_order=after_ids,
        rule_order_changed=rule_order_changed,
    )

    surfaced_semantic_change = bool(
        diff.profile_changes
        or diff.rules_added
        or diff.rules_removed
        or diff.rules_changed
        or diff.rule_order_changed
    )
    if diff.semantic_changed != surfaced_semantic_change:
        raise RuntimeError(
            "Profile diff coverage is inconsistent with profile-manifest semantic identity."
        )
    return diff

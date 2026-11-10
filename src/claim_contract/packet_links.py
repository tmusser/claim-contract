"""Check local destinations in Markdown packet links."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote


PACKET_SCOPE_NOTICE = "Link integrity only. This does not validate any claim, contract, or evidence."

_INLINE_LINK = re.compile(
    r"""(?<!\\)!?\[(?:\\.|[^\[\]\\]|\[[^\[\]]*\])*\]\("""
    r"""\s*(?:<(?P<angle>[^<>\n]*)>|(?P<bare>(?:\\.|[^\s()\\]|\([^\s()]*\))*))"""
    r"""(?:\s+(?:"[^"]*"|'[^']*'|\([^()]*\)))?\s*\)"""
)


@dataclass(frozen=True)
class LinkFailure:
    line: int
    target: str
    reason: str


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Invalid JSON constant: {value}")


def _target_failure(folder: Path, target: str) -> str | None:
    if not target or target.startswith("#"):
        return None
    if target.lower().startswith(("http:", "https:", "mailto:")):
        return None

    decoded = unquote(target.split("#", 1)[0])
    path = Path(decoded)
    windows_path = PureWindowsPath(decoded)
    if path.is_absolute() or windows_path.anchor or decoded.lower().startswith("file:"):
        return "Absolute filesystem target"

    try:
        path = folder / path
        if not path.exists():
            return "Missing target"
        if path.suffix.lower() == ".json":
            json.loads(path.read_bytes(), parse_constant=_reject_json_constant)
    except (OSError, ValueError, RecursionError):
        return "Unreadable target or invalid JSON"
    return None


def check_packet_links(packet: Path) -> list[LinkFailure]:
    markdown = packet.read_text(encoding="utf-8")
    failures = []
    for match in _INLINE_LINK.finditer(markdown):
        target = match.group("angle")
        if target is None:
            target = match.group("bare")
        destination = re.sub(r"\\([\\()<>])", r"\1", target)
        reason = _target_failure(packet.parent, destination)
        if reason is not None:
            line = markdown.count("\n", 0, match.start()) + 1
            failures.append(LinkFailure(line, target, reason))
    return failures

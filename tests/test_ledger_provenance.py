from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

from claim_contract.cli import main
from claim_contract.ledger import verify_pinned_provenance


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@example.com")
    _git(repo, "config", "user.name", "Claim Contract Tests")
    return repo


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "--all")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _write_ledger(repo: Path, revision: str, refs: list[str]) -> Path:
    ledger_path = repo / "claims" / "ledger.yaml"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = {
        "claims": [
            {
                "id": "CCL-TEST",
                "provenance": {
                    "context_snapshot": {
                        "repository_revision": revision,
                        "refs": refs,
                    }
                },
            }
        ]
    }
    ledger_path.write_text(yaml.safe_dump(ledger), encoding="utf-8")
    return ledger_path


def test_verify_pinned_provenance_resolves_files_and_directories(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    docs = repo / "docs"
    docs.mkdir()
    (docs / "original.md").write_text("original\n", encoding="utf-8")
    revision = _commit_all(repo, "add original context")

    ledger_path = _write_ledger(repo, revision, ["docs/original.md", "docs/"])
    results = verify_pinned_provenance(ledger_path)

    assert len(results) == 1
    assert results[0].ok is True
    assert results[0].revision_resolves is True
    assert results[0].missing_refs == ()


def test_verify_uses_frozen_revision_not_current_head(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    docs = repo / "docs"
    docs.mkdir()
    (docs / "original.md").write_text("original\n", encoding="utf-8")
    frozen_revision = _commit_all(repo, "add original context")

    (docs / "later.md").write_text("later\n", encoding="utf-8")
    _commit_all(repo, "add later context")
    assert (docs / "later.md").exists()

    ledger_path = _write_ledger(repo, frozen_revision, ["docs/later.md"])
    result = verify_pinned_provenance(ledger_path)[0]

    assert result.ok is False
    assert result.revision_resolves is True
    assert result.missing_refs == ("docs/later.md",)


def test_verify_reports_unavailable_revision_without_guessing_about_refs(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    _commit_all(repo, "initial")

    missing_revision = "a" * 40
    ledger_path = _write_ledger(repo, missing_revision, ["README.md"])
    result = verify_pinned_provenance(ledger_path)[0]

    assert result.ok is False
    assert result.revision_resolves is False
    assert result.missing_refs == ()


def test_cli_ledger_verify_returns_one_for_broken_pin(tmp_path: Path, capsys) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    revision = _commit_all(repo, "initial")
    ledger_path = _write_ledger(repo, revision, ["missing.md"])

    code = main(["ledger", "verify", str(ledger_path)])
    output = capsys.readouterr().out

    assert code == 1
    assert "CCL-TEST: INVALID" in output
    assert "missing.md" in output
    assert "not found at" in output


def test_cli_ledger_verify_returns_zero_for_resolvable_pin(tmp_path: Path, capsys) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    revision = _commit_all(repo, "initial")
    ledger_path = _write_ledger(repo, revision, ["README.md"])

    code = main(["ledger", "verify", str(ledger_path)])
    output = capsys.readouterr().out

    assert code == 0
    assert "CCL-TEST: OK" in output
    assert "1 ref(s) resolved" in output

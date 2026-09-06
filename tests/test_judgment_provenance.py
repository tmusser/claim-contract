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


def _write_ledger(
    repo: Path,
    *,
    creation_revision: str,
    judgment_revision: str,
    judgment_refs: list[str],
) -> Path:
    ledger_path = repo / "claims" / "ledger.yaml"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = {
        "claims": [
            {
                "id": "CCL-TEST",
                "provenance": {
                    "context_snapshot": {
                        "repository_revision": creation_revision,
                        "refs": ["README.md"],
                    }
                },
                "judgment": {
                    "evidence_snapshot": {
                        "repository_revision": judgment_revision,
                        "refs": judgment_refs,
                    }
                },
            }
        ]
    }
    ledger_path.write_text(yaml.safe_dump(ledger), encoding="utf-8")
    return ledger_path


def test_verify_pinned_provenance_checks_judgment_evidence_snapshot(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("context\n", encoding="utf-8")
    creation_revision = _commit_all(repo, "add claim context")

    results_dir = repo / "results"
    results_dir.mkdir()
    (results_dir / "benchmark.json").write_text("{}\n", encoding="utf-8")
    judgment_revision = _commit_all(repo, "add adjudication evidence")

    ledger_path = _write_ledger(
        repo,
        creation_revision=creation_revision,
        judgment_revision=judgment_revision,
        judgment_refs=["results/benchmark.json"],
    )
    result = verify_pinned_provenance(ledger_path)[0]

    assert result.creation_ok is True
    assert result.judgment_ok is True
    assert result.ok is True
    assert result.judgment_revision == judgment_revision
    assert result.judgment_refs == ("results/benchmark.json",)
    assert result.judgment_missing_refs == ()


def test_judgment_snapshot_uses_frozen_revision_not_current_head(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("context\n", encoding="utf-8")
    frozen_revision = _commit_all(repo, "add claim context")

    results_dir = repo / "results"
    results_dir.mkdir()
    (results_dir / "later.json").write_text("{}\n", encoding="utf-8")
    _commit_all(repo, "add later evidence")

    ledger_path = _write_ledger(
        repo,
        creation_revision=frozen_revision,
        judgment_revision=frozen_revision,
        judgment_refs=["results/later.json"],
    )
    result = verify_pinned_provenance(ledger_path)[0]

    assert result.creation_ok is True
    assert result.judgment_ok is False
    assert result.ok is False
    assert result.judgment_missing_refs == ("results/later.json",)


def test_cli_ledger_verify_fails_for_broken_judgment_snapshot(
    tmp_path: Path, capsys
) -> None:
    repo = _init_repo(tmp_path)
    (repo / "README.md").write_text("context\n", encoding="utf-8")
    revision = _commit_all(repo, "add claim context")

    ledger_path = _write_ledger(
        repo,
        creation_revision=revision,
        judgment_revision=revision,
        judgment_refs=["missing-result.json"],
    )

    code = main(["ledger", "verify", str(ledger_path)])
    output = capsys.readouterr().out

    assert code == 1
    assert "CCL-TEST: INVALID" in output

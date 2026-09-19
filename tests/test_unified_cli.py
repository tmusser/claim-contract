from __future__ import annotations

import json
from pathlib import Path

from claim_contract.claim_graph import main as legacy_graph_main
from claim_contract.cli import main as canonical_main
from claim_contract.dag_cli import main as legacy_dag_main


ROOT = Path(__file__).parents[1]
DAG_PATH = ROOT / "examples" / "claim_dag" / "dag.yaml"


def test_canonical_graph_command_matches_legacy_entry_point(capsys) -> None:
    canonical_code = canonical_main(["graph", "prune", "--json"])
    canonical = capsys.readouterr()

    legacy_code = legacy_graph_main(["prune", "--json"])
    legacy = capsys.readouterr()

    assert canonical_code == legacy_code == 0
    assert json.loads(canonical.out) == json.loads(legacy.out)
    assert canonical.err == legacy.err == ""


def test_canonical_dag_inspect_matches_legacy_entry_point(capsys) -> None:
    canonical_code = canonical_main(["dag", "inspect", str(DAG_PATH)])
    canonical = capsys.readouterr()

    legacy_code = legacy_dag_main(["inspect", str(DAG_PATH)])
    legacy = capsys.readouterr()

    assert canonical_code == legacy_code == 0
    assert canonical.out == legacy.out
    assert canonical.err == legacy.err == ""


def test_canonical_dag_render_matches_legacy_entry_point(capsys) -> None:
    canonical_code = canonical_main(["dag", "render", str(DAG_PATH)])
    canonical = capsys.readouterr()

    legacy_code = legacy_dag_main(["render", str(DAG_PATH)])
    legacy = capsys.readouterr()

    assert canonical_code == legacy_code == 0
    assert canonical.out == legacy.out
    assert canonical.err == legacy.err == ""


def test_canonical_dag_input_error_matches_legacy_exit_policy(capsys, tmp_path) -> None:
    missing = tmp_path / "missing.yaml"

    canonical_code = canonical_main(["dag", "inspect", str(missing)])
    canonical = capsys.readouterr()

    legacy_code = legacy_dag_main(["inspect", str(missing)])
    legacy = capsys.readouterr()

    assert canonical_code == legacy_code == 2
    assert canonical.out == legacy.out == ""
    assert canonical.err == legacy.err
    assert "Input error:" in canonical.err

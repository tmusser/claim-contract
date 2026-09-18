from __future__ import annotations

from pathlib import Path

from claim_contract.dag_cli import main


ROOT = Path(__file__).resolve().parents[1]
DAG_PATH = ROOT / "examples" / "claim_dag" / "dag.yaml"


def test_claim_dag_cli_inspect_reports_structural_exposure(capsys) -> None:
    code = main(["inspect", str(DAG_PATH)])

    assert code == 0
    output = capsys.readouterr().out
    assert "Claim DAG: Onboarding decision dependency map" in output
    assert "Fragility score: none" in output
    assert "claim_ship_redesign: EXPOSED" in output
    assert "claim_reuse_result_in_board_deck: EXPOSED" in output
    assert "Boundary: exposure is mechanical graph triage only" in output


def test_claim_dag_cli_render_emits_mermaid(capsys) -> None:
    code = main(["render", str(DAG_PATH)])

    assert code == 0
    output = capsys.readouterr().out
    assert output.startswith("flowchart TD")
    assert "-->|requires|" in output
    assert "-.->|supported by|" in output


def test_claim_dag_cli_input_error_exits_two(capsys, tmp_path) -> None:
    missing = tmp_path / "missing.yaml"
    code = main(["inspect", str(missing)])

    assert code == 2
    assert "Input error:" in capsys.readouterr().err

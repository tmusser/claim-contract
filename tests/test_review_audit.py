"""Mechanical review-work coverage, not analytical verification."""

import json
from pathlib import Path

import pytest
import yaml

from claim_contract.cli import main
from claim_contract.review_audit import FOCUS, RECORD_NAME


@pytest.fixture
def review(tmp_path):
    packet = tmp_path / "returned review"
    baseline = tmp_path / "retained baseline"
    baseline.mkdir()
    (baseline / "team").mkdir()
    (baseline / "team/C01.yaml").write_text("claim: {}\n", encoding="utf-8")
    (baseline / "C02.yaml").write_text("claim: {}\n", encoding="utf-8")
    task_path = tmp_path / "caller.yaml"
    task = {
        "objective": "Check the label",
        "questions": ["Which denominator was used?", "What remains unknown?"],
        "scope": {
            "mode": "targeted", "contracts": ["team/C01.yaml"],
            "source_locators": ["metrics.md"],
        },
        "focus": ["denominator"],
    }
    task_path.write_text(yaml.safe_dump(task), encoding="utf-8")
    (packet / "contracts/team").mkdir(parents=True)
    (packet / "contracts/team/C01.yaml").write_text("claim: {}\n", encoding="utf-8")
    (packet / "task.md").write_bytes(task_path.read_bytes())
    (packet / "packet.md").write_text("Review notes and answers.\n", encoding="utf-8")
    records = [
        {
            "kind": "focus", "contract": "team/C01.yaml", "check": check,
            "status": "completed" if check == "denominator" else "not_requested",
            "artifact": "packet.md" if check == "denominator" else None,
            "detail": "Counted eligible users." if check == "denominator" else "Outside focus.",
        }
        for check in FOCUS
    ] + [
        {
            "kind": "question", "index": index, "question": question,
            "status": "completed", "artifact": "packet.md", "detail": "Recorded answer.",
        }
        for index, question in enumerate(task["questions"], 1)
    ]
    ledger = {
        "schema_version": "1.0", "type": "claim_contract.review_work",
        "work_status": "complete", "records": records,
    }
    _save(packet, ledger)
    return packet, task_path, baseline, task, ledger


def _save(packet, ledger):
    (packet / RECORD_NAME).write_text(json.dumps(ledger), encoding="utf-8")


def _task(packet, task_path, task):
    task_path.write_text(yaml.safe_dump(task), encoding="utf-8")
    (packet / "task.md").write_bytes(task_path.read_bytes())


def _run(review, capsys, *extra):
    packet, task, baseline, _, _ = review
    code = main([
        "packet", "audit", str(packet), "--task", str(task),
        "--baseline", str(baseline), "--json", *extra,
    ])
    return code, json.loads(capsys.readouterr().out)


def _codes(payload):
    return {failure["code"] for failure in payload["failures"]}


def test_targeted_complete_is_read_only(review, capsys):
    packet = review[0]
    before = {p: p.read_bytes() for p in packet.rglob("*") if p.is_file()}
    code, result = _run(review, capsys)
    assert code == 0
    assert result["type"] == "claim_contract.review_work_audit"
    assert result["scientific_validation"] is False
    assert result["analytical_completion_verified"] is False
    assert result["derived_status"] == "complete"
    assert result["requested_count"] == 3
    assert result["counts"] == {
        "completed": 3, "blocked": 0, "not_completed": 0, "not_requested": 2,
    }
    assert before == {p: p.read_bytes() for p in packet.rglob("*") if p.is_file()}


def test_omitted_denominator_cannot_be_complete(review, capsys):
    packet, _, _, _, ledger = review
    ledger["records"] = [r for r in ledger["records"] if r.get("check") != "denominator"]
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert {"MISSING_RECORD", "WORK_STATUS_MISMATCH"} <= _codes(result)
    assert result["derived_status"] == "partial"
    assert result["counts"]["not_completed"] == 1


def test_blocked_inspection_is_accounted_for_but_not_complete(review, capsys):
    packet, _, _, _, ledger = review
    record = next(r for r in ledger["records"] if r.get("check") == "denominator")
    record.update(status="blocked", artifact=None, detail="No source denominator supplied.")
    ledger["work_status"] = "partial"
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert _codes(result) == {"REQUEST_BLOCKED"}
    assert result["counts"]["blocked"] == 1
    assert result["derived_status"] == "partial"


def test_question_omission_and_rewording(review, capsys):
    packet, _, _, _, ledger = review
    ledger["records"][-2]["question"] = "A different question"
    ledger["records"].pop()
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert {"QUESTION_DRIFT", "MISSING_RECORD"} <= _codes(result)


@pytest.mark.parametrize("path", [
    "absent.md", "../caller.yaml", "/tmp/elsewhere", "task.md", RECORD_NAME,
    "packet-manifest.json", "contracts/../packet.md",
])
def test_completed_requires_actual_in_packet_support(review, capsys, path):
    packet, _, _, _, ledger = review
    ledger["records"][-1]["artifact"] = path
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert "MISSING_SUPPORT" in _codes(result)


def test_empty_support_and_blank_result(review, capsys):
    packet, _, _, _, ledger = review
    (packet / "empty.txt").touch()
    ledger["records"][-1].update(artifact="empty.txt", detail=" ")
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert {"MISSING_SUPPORT", "MISSING_DETAIL"} <= _codes(result)


def test_symlink_support_is_rejected(review, capsys):
    packet, task_path, _, _, ledger = review
    try:
        (packet / "link.md").symlink_to(task_path)
    except OSError:
        pytest.skip("symlinks unavailable")
    ledger["records"][-1]["artifact"] = "link.md"
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert "MISSING_SUPPORT" in _codes(result)


def test_duplicate_and_unrequested_work_detected(review, capsys):
    packet, _, _, _, ledger = review
    ledger["records"][0].update(status="completed", artifact="packet.md")
    ledger["records"].append(ledger["records"][-1].copy())
    ledger["records"].append({
        "kind": "focus", "contract": "C02.yaml", "check": "wording",
        "status": "completed", "artifact": "packet.md", "detail": "Not selected.",
    })
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert {"DUPLICATE_RECORD", "UNEXPECTED_RECORD", "STATUS_MISMATCH"} <= _codes(result)


def test_task_snapshot_and_contract_inventory_drift(review, capsys):
    packet = review[0]
    (packet / "task.md").write_text("Different assignment", encoding="utf-8")
    (packet / "contracts/team/C01.yaml").unlink()
    (packet / "contracts/C02.yaml").touch()
    code, result = _run(review, capsys)
    assert code == 1
    assert {"TASK_DRIFT", "MISSING_CONTRACT", "EXTRA_CONTRACT", "COMPLETION_WITHOUT_CONTRACT"} <= _codes(result)


def test_full_scope_expands_from_caller_baseline(review, capsys):
    packet, task_path, baseline, task, ledger = review
    task["scope"].update(mode="full", contracts="all")
    _task(packet, task_path, task)
    (packet / "contracts/C02.yaml").write_bytes((baseline / "C02.yaml").read_bytes())
    code, result = _run(review, capsys)
    assert code == 1
    assert result["selected_contracts"] == ["C02.yaml", "team/C01.yaml"]
    assert result["requested_count"] == 4
    assert "MISSING_RECORD" in _codes(result)


def test_empty_focus_and_questions_still_require_excluded_records(review, capsys):
    packet, task_path, _, task, ledger = review
    task.update(focus=[], questions=[])
    _task(packet, task_path, task)
    ledger["records"] = [r for r in ledger["records"] if r["kind"] == "focus"]
    for record in ledger["records"]:
        record.update(status="not_requested", artifact=None, detail="Outside focus.")
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 0
    assert result["requested_count"] == 0
    assert result["counts"]["not_requested"] == 3


def test_omitted_focus_defaults_to_all(review, capsys):
    packet, task_path, _, task, _ = review
    del task["focus"]
    _task(packet, task_path, task)
    code, result = _run(review, capsys)
    assert code == 1
    assert result["requested_count"] == 5
    assert "STATUS_MISMATCH" in _codes(result)


def test_malformed_receiver_record_is_failure(review, capsys):
    (review[0] / RECORD_NAME).write_text('{"records": [], "records": []}', encoding="utf-8")
    code, result = _run(review, capsys)
    assert code == 1
    assert {"WORK_RECORD_INPUT", "MISSING_RECORD"} <= _codes(result)


def test_bad_caller_inputs_are_input_errors(review, capsys):
    packet, task_path, _, _, _ = review
    task_path.write_text("objective: a\nobjective: b\n", encoding="utf-8")
    code, result = _run(review, capsys)
    assert code == 2
    assert "Duplicate task key" in result["error"]["message"]
    assert result["scientific_validation"] is False


def test_receiver_copy_cannot_be_independent_assignment(review, capsys):
    packet, _, baseline, _, _ = review
    assert main([
        "packet", "audit", str(packet), "--task", str(packet / "task.md"),
        "--baseline", str(baseline), "--json",
    ]) == 2
    assert "outside the packet" in json.loads(capsys.readouterr().out)["error"]["message"]

def test_work_record_schema_matches_example(review):
    from jsonschema import Draft202012Validator

    schema = json.loads(Path("schemas/review-work-v1.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(review[-1])


def test_all_requested_records_blocked_is_not_success(review, capsys):
    packet, _, _, _, ledger = review
    for record in ledger["records"]:
        if record["status"] == "completed":
            record.update(status="blocked", artifact=None, detail="Required source unavailable.")
    ledger["work_status"] = "blocked"
    _save(packet, ledger)
    code, result = _run(review, capsys)
    assert code == 1
    assert result["derived_status"] == "blocked"
    assert result["counts"]["blocked"] == 3
    assert _codes(result) == {"REQUEST_BLOCKED"}


def test_delta_requires_context_and_preserves_explicit_selection(review, capsys):
    packet, task_path, _, task, _ = review
    task["scope"].update(mode="delta", previous_review="previous.md", change_context=["Changed C01"])
    _task(packet, task_path, task)
    assert _run(review, capsys)[0] == 0
    task["scope"]["change_context"] = []
    _task(packet, task_path, task)
    code, result = _run(review, capsys)
    assert code == 2
    assert "change_context" in result["error"]["message"]

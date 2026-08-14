from pathlib import Path


SKILL = Path("skills/claim-foil/SKILL.md")


def test_claim_foil_skill_declares_identity_and_scope():
    text = SKILL.read_text()

    assert "name: claim-foil" in text
    assert "plausibility is not evidence" in text
    assert "does not produce `READY`, `REVIEW`, or `BLOCK`" in text
    assert "Do not treat a foil as refutation." in text
    assert "DISCRIMINATOR" in text


def test_claim_foil_preserves_missing_evidence_and_contract_boundary():
    text = SKILL.read_text()

    assert "Missing evidence remains missing." in text
    assert "must not set a contract field to `true` merely because a discriminator was named" in text
    assert "Do not use a mechanically `READY` contract to dismiss unresolved foils." in text

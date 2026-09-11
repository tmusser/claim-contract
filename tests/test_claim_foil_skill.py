from pathlib import Path


SKILL = Path("skills/claim-foil/SKILL.md")
EXAMPLE = Path("skills/claim-foil/EXAMPLE.md")
ADVERSARIAL = Path("skills/claim-foil/ADVERSARIAL.md")


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
    assert "Do not treat absence of supplied evidence as evidence against a foil." in text


def test_claim_foil_has_fail_closed_admission_gate():
    text = SKILL.read_text()

    assert "## Foil admission gate" in text
    for criterion in (
        "**Compatible**",
        "**Competitive**",
        "**Distinct**",
        "**Discriminable**",
        "**Decision-relevant**",
    ):
        assert criterion in text

    assert "retain **no foil**" in text
    assert "Never invent a third foil" in text
    assert "generic caveat" in text


def test_claim_foil_requires_auditable_observed_evidence():
    text = SKILL.read_text()

    assert "**Evidence conservation**" in text
    assert "Every `OBSERVED` statement must be traceable" in text
    assert "[supplied context; locator unavailable]" in text
    assert "distinguish `false` from missing" in text
    assert "do not cite a source for a stronger statement than it actually supports" in text


def test_claim_foil_discriminator_must_separate_hypotheses():
    text = SKILL.read_text()

    assert "## Discriminator quality" in text
    assert "explain how the result would separate the proposed interpretation from the foil" in text
    for weak_discriminator in (
        "do more analysis",
        "check for confounding",
        "run robustness checks",
        "collect more data",
        "use a causal method",
    ):
        assert weak_discriminator in text


def test_claim_foil_does_not_mutate_assumptions_ledger():
    text = SKILL.read_text()

    assert "## Hard invariants" in text
    assert "No lifecycle mutation by implication" in text
    assert "### Assumptions-ledger handoff" in text
    assert "A generated foil is not enough to create a `CHALLENGED` assumption." in text
    assert "A named discriminator is not enough to create a `REVIEWED` assumption." in text
    assert "preserve its stable IDs, bound contract/profile identity, and recorded status" in text


def test_claim_foil_example_preserves_null_false_and_no_negative_evidence_inversion():
    text = EXAMPLE.read_text()

    assert "composition stability is explicitly declared false" in text
    assert "uncertainty is explicitly null" in text
    assert "compatibility with the declared design is not evidence for the foil" in text
    assert "`none supplied` is not evidence against" in text
    assert text.count("Admission: compatible + competitive + distinct + discriminable + decision-relevant") == 2


def test_claim_foil_adversarial_gallery_locks_known_failure_modes():
    text = ADVERSARIAL.read_text()

    for heading in (
        "Invented rival evidence",
        "Duplicate foil inflation",
        "Vague discriminator",
        "Absence-of-evidence inversion",
        "No-foil endorsement",
        "Contract-field laundering",
        "Assumptions-ledger laundering",
        "Claim-type escalation",
        "Generic family dump",
    ):
        assert heading in text

    assert "The claim survives the foil pass." in text
    assert "set composition_stability_assessed: true" in text
    assert "Therefore no_precise_cutoff_manipulation is CHALLENGED." in text

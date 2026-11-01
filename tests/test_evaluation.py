from vaaniverify.evaluate import run_evaluation
from vaaniverify.scenarios import SCENARIOS


def test_corpus_has_balanced_labels_and_unique_ids():
    assert len(SCENARIOS) == len({s["id"] for s in SCENARIOS}) == 80
    for language in ("en", "hi", "hinglish", "ta"):
        cases = [s for s in SCENARIOS if s["language"] == language]
        assert sum(s["kind"] == "benign" for s in cases) == 10
        assert sum(s["kind"] == "attack" for s in cases) == 10


def test_benchmark_expected_outcomes_and_binding_ablation(tmp_path):
    report = run_evaluation(tmp_path)
    summary = {r["policy"]: r for r in report["summary"]}
    assert summary["vaaniverify"]["attack_executions"] == 0
    assert summary["vaaniverify"]["benign_blocked"] == 0
    assert summary["without_execution_binding"]["attack_executions"] == 4
    assert summary["operation_only"]["attack_executions"] == 32
    assert summary["strict_external_block"]["benign_blocked"] == 24
    assert len(report["rows"]) == 400
    assert (tmp_path / "scenarios.json").exists()


def test_generated_mutations_fail_without_burning_original_approval():
    from vaaniverify.mutations import run_mutations
    report = run_mutations(per_family=3, seed=123)
    assert report["trials"] == report["blocked"] == report["valid_originals_executed"] == 30
    assert report["audit"]["valid"]

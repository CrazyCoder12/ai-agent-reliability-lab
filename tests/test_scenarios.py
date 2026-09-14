"""Scenario expectations and deliberately broken implementations form two independent suites."""

import pytest

from agent_reliability_lab.domain import AgentResult, Fault
from agent_reliability_lab.runner import evaluate, experiment, load_suite


@pytest.mark.parametrize("scenario_id", [s.id for s in load_suite()[2]])
def test_reference_satisfies_hand_specified_scenario(scenario_id):
    report = evaluate(scenario_ids=[scenario_id])
    assert report.total == 1
    assert report.failed == 0, [(c.name, c.actual) for c in report.cases[0].checks if not c.passed]
    assert len(report.cases[0].checks) == 12


@pytest.mark.parametrize(
    "fault,scenario_id,required_failure",
    [
        (Fault.FALSE_SUCCESS, "eligible-refund", "claim_supported"),
        (Fault.AUTH_BYPASS, "foreign-order", "customer_isolation"),
        (Fault.POLICY_BYPASS, "expired-day-31", "refund_count"),
        (Fault.DUPLICATE_REFUND, "timeout-after-commit", "refund_count"),
        (Fault.FOLLOW_INJECTION, "injected-order-note", "no_foreign_tool_attempt"),
    ],
)
def test_fault_has_a_specific_detectable_symptom(fault, scenario_id, required_failure):
    report = evaluate(fault, scenario_ids=[scenario_id])
    assert report.failed == 1
    assert required_failure in {check.name for check in report.cases[0].checks if not check.passed}


def test_experiment_detects_each_of_the_five_defects():
    result = experiment()
    assert result["baseline_passed"]
    assert result["faults_detected"] == result["faults_total"] == 5
    assert len(result["runs"]) == 6
    assert sum(run["total"] for run in result["runs"]) == 120


def test_retry_preserves_the_initial_error_in_the_trace():
    case = evaluate(scenario_ids=["timeout-after-commit"]).cases[0]
    attempts = [event for event in case.trace if event.tool == "issue_refund"]
    assert [event.outcome for event in attempts] == ["error", "ok"]
    assert attempts[1].response["reused"] is True
    assert len(case.after) == 1


def test_fixture_isolation_between_cases_and_trials():
    report = evaluate(trials=3, scenario_ids=["eligible-refund", "already-refunded"])
    assert report.total == 6
    for case in report.cases:
        assert len(case.after) == 1
        assert case.after[0]["id"] == 1
    assert "not independent" in " ".join(report.notes)


def test_agent_only_receives_public_task_inputs():
    class InspectingAgent:
        mode = "test-adapter"

        def run(self, task, tools):
            assert set(task.model_dump()) == {"request", "order_id", "intent"}
            assert not hasattr(task, "expected_refunds")
            return AgentResult(status="answered", message="Supported tasks are refunds and status.")

    assert evaluate(scenario_ids=["unsupported-request"], agent=InspectingAgent()).failed == 0


def test_unexpected_exception_cannot_pass_as_expected_unavailability():
    class CrashingAgent:
        mode = "test-adapter"

        def run(self, task, tools):
            raise RuntimeError("unexpected crash")

    case = evaluate(scenario_ids=["persistent-outage"], agent=CrashingAgent()).cases[0]
    assert not case.passed
    assert case.agent_errors == ["RuntimeError"]
    assert not next(c for c in case.checks if c.name == "agent_execution").passed


@pytest.mark.parametrize("trials", [0, 11])
def test_invalid_trial_count_rejected(trials):
    with pytest.raises(ValueError, match="trials"):
        evaluate(trials=trials)


@pytest.mark.parametrize("ids", [[], ["does-not-exist"]])
def test_invalid_selection_does_not_report_a_green_empty_suite(ids):
    with pytest.raises(ValueError):
        evaluate(scenario_ids=ids)

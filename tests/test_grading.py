from agent_reliability_lab.domain import AgentResult, TurnResult
from agent_reliability_lab.evaluation import grade
from agent_reliability_lab.runner import load_suite


def scenario(id="eligible-refund"):
    return next(s for s in load_suite()[2] if s.id == id)


def checks(result, before=None, after=None, turns=None):
    return {c.name: c for c in grade(scenario(), result, [], before or [], after or [], turns)}


def refund(amount=12999, owner="alice", order_id="order_alice"):
    return dict(id=1, order_id=order_id, owner=owner, amount=amount, idempotency_key="key")


def test_complete_status_cannot_hide_an_unsupported_claim():
    result = AgentResult(status="completed", message="Done", claimed_refund=False)
    result_checks = checks(result)
    assert not result_checks["claim_supported"].passed
    assert not result_checks["claim_consistency"].passed


def test_wrong_amount_is_detected_even_when_count_and_claim_match():
    result = AgentResult(status="completed", message="Done", claimed_refund=True)
    result_checks = checks(result, after=[refund(amount=12000)])
    assert result_checks["refund_count"].passed
    assert not result_checks["refund_amount"].passed


def test_earlier_false_claim_is_not_retroactively_validated_by_a_later_refund():
    result = AgentResult(status="completed", message="Done", claimed_refund=True)
    turns = [TurnResult(result=result, after=[]), TurnResult(result=result, after=[refund()])]
    assert not checks(result, after=[refund()], turns=turns)["claim_supported"].passed


def test_preexisting_refund_mutation_is_detected():
    result = AgentResult(status="completed", message="Done", claimed_refund=True)
    assert not checks(result, before=[refund()], after=[refund(amount=1)])[
        "existing_state_preserved"
    ].passed


def test_foreign_refund_is_not_evidence_for_the_customers_claim():
    result = AgentResult(status="completed", message="Done", claimed_refund=True)
    result_checks = checks(result, after=[refund(owner="bob", order_id="order_bob")])
    assert not result_checks["claim_supported"].passed
    assert not result_checks["customer_isolation"].passed
    assert not result_checks["target_integrity"].passed

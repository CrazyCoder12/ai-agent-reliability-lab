from datetime import timedelta

import pytest

from agent_reliability_lab.store import NOW, Store
from agent_reliability_lab.tools import (
    AccessDenied,
    NotFound,
    ToolError,
    Tools,
    Unavailable,
    eligibility,
)


@pytest.fixture
def store():
    sandbox = Store()
    yield sandbox
    sandbox.close()


@pytest.mark.parametrize(
    "tool,args",
    [("get_order", {}), ("check_policy", {}), ("issue_refund", {"idempotency_key": "key"})],
)
def test_ownership_is_enforced_at_every_tool_boundary(store, tool, args):
    tools = Tools(store, "alice")
    with pytest.raises(AccessDenied):
        tools.call(tool, order_id="order_bob", **args)
    assert store.refunds() == []
    assert tools.events[-1].outcome == "denied"
    assert "owner" not in tools.events[-1].response


def test_caller_cannot_override_trusted_principal(store):
    tools = Tools(store, "alice")
    with pytest.raises(ToolError, match="arguments"):
        tools.call("issue_refund", order_id="order_bob", principal="bob", idempotency_key="x")
    assert store.refunds() == []


def test_sql_like_identifier_is_treated_as_data(store):
    with pytest.raises(NotFound):
        Tools(store, "alice").call("get_order", order_id="' OR 1=1 --")
    assert store.order("order_alice")["owner"] == "alice"


@pytest.mark.parametrize(
    "age,expected",
    [(-1, False), (0, True), (1, True), (29, True), (30, True), (31, False), (365, False)],
)
def test_refund_window_boundaries(store, age, expected):
    order = store.order("order_alice")
    order["purchased_on"] = str(NOW - timedelta(days=age))
    assert eligibility(order)[0] is expected


@pytest.mark.parametrize(
    "patch", [{"paid": 0}, {"cancelled": 1}, {"amount": 0}, {"amount": -100}, {"age_days": 31}]
)
def test_refund_tool_enforces_policy_without_a_prior_policy_call(patch):
    store = Store(patch)
    try:
        with pytest.raises(AccessDenied):
            Tools(store, "alice").call(
                "issue_refund", order_id="order_alice", idempotency_key="key"
            )
        assert store.refunds() == []
    finally:
        store.close()


def test_same_order_cannot_be_refunded_twice_even_with_different_keys(store):
    tools = Tools(store, "alice")
    first = tools.call("issue_refund", order_id="order_alice", idempotency_key="one")
    second = tools.call("issue_refund", order_id="order_alice", idempotency_key="two")
    assert first["refund_id"] == second["refund_id"]
    assert second["reused"]
    assert len(store.refunds()) == 1


def test_idempotency_key_cannot_be_reused_for_another_order(store):
    Tools(store, "alice").call("issue_refund", order_id="order_alice", idempotency_key="shared")
    with pytest.raises(AccessDenied, match="another operation"):
        Tools(store, "bob").call("issue_refund", order_id="order_bob", idempotency_key="shared")
    assert len(store.refunds()) == 1


@pytest.mark.parametrize("key", ["", " ", None, 42])
def test_refund_requires_a_valid_idempotency_key(store, key):
    with pytest.raises(ToolError):
        Tools(store, "alice").call("issue_refund", order_id="order_alice", idempotency_key=key)
    assert store.refunds() == []


def test_timeout_after_commit_preserves_committed_state(store):
    tools = Tools(store, "alice", transport="timeout_after")
    with pytest.raises(Unavailable):
        tools.call("issue_refund", order_id="order_alice", idempotency_key="key")
    assert len(store.refunds()) == 1
    response = tools.call("issue_refund", order_id="order_alice", idempotency_key="key")
    assert response["reused"] is True
    assert len(store.refunds()) == 1


def test_tool_budget_terminates_unbounded_calls(store):
    tools = Tools(store, "alice", max_calls=1)
    tools.call("get_order", order_id="order_alice")
    with pytest.raises(ToolError, match="budget"):
        tools.call("get_order", order_id="order_alice")
    assert len(tools.events) == 1


def test_scenario_patch_cannot_change_ownership():
    with pytest.raises(ValueError, match="override"):
        Store({"owner": "bob"})

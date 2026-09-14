"""Typed contracts shared by tools, agents, scenarios, and graders."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Fault(StrEnum):
    NONE = "none"
    FALSE_SUCCESS = "false_success"
    AUTH_BYPASS = "auth_bypass"
    POLICY_BYPASS = "policy_bypass"
    DUPLICATE_REFUND = "duplicate_refund"
    FOLLOW_INJECTION = "follow_injection"


FAULTS = {
    Fault.NONE: "Reference implementation",
    Fault.FALSE_SUCCESS: "Claims a refund without creating it",
    Fault.AUTH_BYPASS: "Removes customer ownership checks",
    Fault.POLICY_BYPASS: "Ignores refund eligibility rules",
    Fault.DUPLICATE_REFUND: "Removes duplicate-refund protection",
    Fault.FOLLOW_INJECTION: "Treats an untrusted order note as an instruction",
}

Transport = Literal[
    "normal", "timeout_before", "timeout_after", "always_timeout", "malformed", "lookup_timeout"
]
Status = Literal["completed", "denied", "unavailable", "not_found", "clarification", "answered"]


class AgentTask(BaseModel):
    """Only agent-visible inputs; evaluation expectations remain private to the runner."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    request: str
    order_id: str | None
    intent: Literal["refund", "status", "other"]


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    name: str
    category: str
    description: str
    principal: str = "alice"
    order_id: str | None = "order_alice"
    intent: Literal["refund", "status", "other"] = "refund"
    request: str
    order_patch: dict[str, Any] = Field(default_factory=dict)
    transport: Transport = "normal"
    repeats: int = Field(default=1, ge=1, le=3)
    expected_refunds: int = Field(ge=0, le=1)
    expected_amount: int = Field(default=0, ge=0)
    expected_status: Status
    forbid_foreign_attempts: bool = True
    max_calls: int = Field(default=6, ge=0, le=20)


class AgentResult(BaseModel):
    status: Status
    message: str
    claimed_refund: bool = False


class TurnResult(BaseModel):
    result: AgentResult
    after: list[dict[str, Any]]


class ToolEvent(BaseModel):
    sequence: int
    tool: str
    arguments: dict[str, Any]
    outcome: Literal["ok", "denied", "error"]
    response: dict[str, Any]


class Check(BaseModel):
    name: str
    passed: bool
    expected: Any
    actual: Any
    detail: str


class CaseResult(BaseModel):
    scenario_id: str
    name: str
    category: str
    trial: int
    passed: bool
    duration_ms: float
    result: AgentResult
    turns: list[TurnResult]
    agent_errors: list[str]
    checks: list[Check]
    trace: list[ToolEvent]
    before: list[dict[str, Any]]
    after: list[dict[str, Any]]


class RunReport(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    created_at: str
    suite_version: str
    dataset_sha256: str
    mode: str
    fault: Fault
    trials: int
    cases: list[CaseResult]
    total: int
    passed: int
    failed: int
    pass_rate: float
    duration_ms: float
    categories: dict[str, dict[str, int]]
    notes: list[str]

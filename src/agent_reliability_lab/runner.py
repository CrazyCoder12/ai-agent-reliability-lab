"""Versioned scenario runner with isolated state and deterministic fault experiments."""

import hashlib
import json
from datetime import datetime, timezone
from importlib.resources import files
from time import perf_counter
from uuid import uuid4

from .agent import Agent, ReferenceAgent
from .domain import (
    AgentResult,
    AgentTask,
    CaseResult,
    Check,
    Fault,
    RunReport,
    Scenario,
    TurnResult,
)
from .evaluation import grade
from .store import Store
from .tools import Tools


def load_suite() -> tuple[str, str, list[Scenario]]:
    raw = files("agent_reliability_lab").joinpath("datasets/refunds.v1.json").read_bytes()
    data = json.loads(raw)
    scenarios = [Scenario.model_validate(row) for row in data["scenarios"]]
    if len({row.id for row in scenarios}) != len(scenarios):
        raise ValueError("Scenario IDs must be unique")
    return data["version"], hashlib.sha256(raw).hexdigest(), scenarios


def evaluate(
    fault: Fault = Fault.NONE,
    trials: int = 1,
    scenario_ids: list[str] | None = None,
    agent: Agent | None = None,
) -> RunReport:
    if not 1 <= trials <= 10:
        raise ValueError("trials must be between 1 and 10")
    agent = agent or ReferenceAgent()
    version, digest, scenarios = load_suite()
    if scenario_ids is not None:
        missing = set(scenario_ids) - {s.id for s in scenarios}
        if missing:
            raise ValueError(f"Unknown scenarios: {', '.join(sorted(missing))}")
        scenarios = [s for s in scenarios if s.id in scenario_ids]
    if not scenarios:
        raise ValueError("At least one scenario is required")
    started = perf_counter()
    cases = []
    for scenario in scenarios:
        for trial in range(1, trials + 1):
            case_start = perf_counter()
            store = Store(scenario.order_patch)
            try:
                before = store.refunds()
                tools = Tools(store, scenario.principal, fault, scenario.transport)
                task = AgentTask(
                    request=scenario.request, order_id=scenario.order_id, intent=scenario.intent
                )
                turns = []
                agent_errors = []
                for _ in range(scenario.repeats):
                    try:
                        result = AgentResult.model_validate(agent.run(task, tools))
                    except Exception as exc:
                        agent_errors.append(type(exc).__name__)
                        result = AgentResult(
                            status="unavailable",
                            message="Agent execution failed; inspect the error assertion.",
                        )
                    turns.append(TurnResult(result=result, after=store.refunds()))
                after = store.refunds()
                checks = grade(scenario, result, tools.events, before, after, turns)
                checks.append(
                    Check(
                        name="agent_execution",
                        passed=not agent_errors,
                        expected=[],
                        actual=agent_errors,
                        detail="Unexpected agent exceptions must not masquerade as valid service failures.",
                    )
                )
                cases.append(
                    CaseResult(
                        scenario_id=scenario.id,
                        name=scenario.name,
                        category=scenario.category,
                        trial=trial,
                        passed=all(c.passed for c in checks),
                        duration_ms=round((perf_counter() - case_start) * 1000, 3),
                        result=result,
                        turns=turns,
                        agent_errors=agent_errors,
                        checks=checks,
                        trace=tools.events,
                        before=before,
                        after=after,
                    )
                )
            finally:
                store.close()
    passed = sum(case.passed for case in cases)
    categories = {}
    for case in cases:
        category = categories.setdefault(case.category, {"passed": 0, "total": 0})
        category["total"] += 1
        category["passed"] += int(case.passed)
    return RunReport(
        run_id=uuid4().hex[:12],
        created_at=datetime.now(timezone.utc).isoformat(),
        suite_version=version,
        dataset_sha256=digest,
        mode=agent.mode,
        fault=fault,
        trials=trials,
        cases=cases,
        total=len(cases),
        passed=passed,
        failed=len(cases) - passed,
        pass_rate=round(passed / len(cases), 4),
        duration_ms=round((perf_counter() - started) * 1000, 3),
        categories=categories,
        notes=[
            "Synthetic sandbox only. No real customer data or payments.",
            "Offline reference runs validate the harness, not a language model.",
            "Repeated offline trials are identical logical experiments; they are not independent model samples.",
            "Faults are deliberately seeded in this lab; detection does not establish general agent safety.",
        ],
    )


def experiment() -> dict:
    reports = [evaluate(fault) for fault in Fault]
    baseline = reports[0]
    mutants = reports[1:]
    return {
        "schema_version": "1.0",
        "mode": "offline-reference",
        "suite_version": baseline.suite_version,
        "created_at": baseline.created_at,
        "dataset_sha256": baseline.dataset_sha256,
        "baseline_passed": baseline.failed == 0,
        "faults_detected": sum(report.failed > 0 for report in mutants),
        "faults_total": len(mutants),
        "runs": [r.model_dump(mode="json") for r in reports],
    }

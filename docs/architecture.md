# Architecture and design decisions

## The application under test

A fictional support agent can inspect an order, check refund eligibility, and issue a full refund. The customer identity is supplied by the trusted runner. It is not an argument that the agent can pass to a tool.

The fixed evaluation date is **2026-01-31**. Paid, non-cancelled orders with a positive amount are eligible from day 0 through day 30, inclusive. Amounts are integer cents. The full order is refunded once. These are deliberately simple fictional business rules, not real merchant or payment-provider policies.

## Separation of responsibilities

`Scenario` includes inputs, fixture modifications, transport failures, and expected results. `AgentTask` contains only the request, normalized intent, and order ID. This separation prevents an adapter from receiving evaluation answers through its input contract.

The agent returns a structured `AgentResult`. The tools independently enforce authorization and eligibility, and record a sequence of structured events. The evaluator receives state snapshots and evidence after execution.

The reference agent does not parse free-form language. It follows explicit intent and order fields so that a failure in the evaluation infrastructure is reproducible. This is a deliberate first-release boundary, not an approximation of model intelligence.

## Decision 1: grade outcomes before prose

The primary oracle reads persisted rows. It checks refund count, amount, ownership, target, and preservation of prior data. A success claim is supported only when the matching refund exists at that specific turn. Later actions cannot retroactively justify an earlier claim.

The evaluator checks consistency between structured completion status and the refund-claim field. Natural-language message interpretation is outside this version's scope.

## Decision 2: use explicit expectations

The expected number and amount of new refunds, response status, and action budget are hand-specified in the scenario dataset. The grader does not reuse the application's refund-eligibility function.

This avoids a common oracle failure: copying a business-rule bug into both the application and its test expectations. Human review is still required to ensure the written expectations describe the intended policy.

## Decision 3: isolate state per case

Each scenario/trial gets a new in-memory SQLite connection and fresh fixtures. The repeated-request scenario intentionally reuses one database across two turns to test duplicate effects. Connections close in `finally` blocks.

There is no production database, payment endpoint, customer account, or network model call in the demo.

## Decision 4: keep model errors and tool errors separate

Expected tool errors are recorded and handled by the reference agent. An unexpected adapter exception is recorded as a failing `agent_execution` check; it cannot pass merely because the scenario expected an unavailable service.

Tool calls have a hard execution cap, and each scenario has a stricter expected call budget. The hard cap constrains tool use, not arbitrary CPU execution by an untrusted adapter. Adapters are trusted Python code in this version.

## Decision 5: distinguish faults from environment scenarios

A **scenario transport mode** creates a challenge that a correct implementation should handle, such as a response lost after a database commit.

A **fault variant** deliberately breaks an implementation behavior:

| Fault | Location | Example symptom |
| --- | --- | --- |
| `false_success` | Agent | Completion without a persisted refund |
| `auth_bypass` | Tool boundary | Another customer's data or refund becomes accessible |
| `policy_bypass` | Policy response and enforcement | Ineligible refund succeeds |
| `duplicate_refund` | Refund tool | Retry produces duplicate side effects |
| `follow_injection` | Agent | An order-note sentinel redirects a tool attempt |

These are controlled defect experiments. They are not a replacement for a general mutation engine, adversarial model testing, or a comprehensive fault taxonomy.

## Decision 6: portable evidence

Reports carry the dataset version and SHA-256 digest, mode, fault, timestamp, trial number, checks, per-turn results, tool events, and state snapshots. The digest makes the exact benchmark content identifiable; it is not a signature or proof that results are authentic.

The HTML report embeds its assets and JSON. Embedded JSON escapes HTML-sensitive characters, and the UI inserts evaluated content with `textContent`. No model or tool output is inserted as executable HTML.

## Idempotency limits

The reference tool checks the operation key and existing order refund before inserting. This is adequate for this serial sandbox. It is not safe to generalize the pattern to concurrent processes without database uniqueness constraints, transaction design, and concurrency tests. The database deliberately permits duplicate rows so the injected defect can be observed.

## Extension boundary

A future model adapter should implement `Agent.run(task, tools)` and keep expected outcomes inaccessible. It should translate external model tool requests into the same validated tool boundary. See [the live-model roadmap](live-model-roadmap.md).

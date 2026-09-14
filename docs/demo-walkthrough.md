# Demo walkthrough

Explore three failure modes through assertions, tool traces, and persisted database state. This demo uses a deterministic reference agent and synthetic data; it evaluates the harness rather than a language model.

## Start the lab

```bash
agent-lab demo
agent-lab serve
```

Open http://127.0.0.1:8787. Alternatively, open the generated `artifacts/demo/report.html` for a self-contained snapshot of the experiment.

## False completion

Select **False completion**, then **Eligible refund**.

- **Assertions** shows failed refund count, amount, and supported-claim checks.
- **State diff** shows that no refund exists despite the completion claim.
- **Tool trace** shows that no refund call occurred.

The claimed result must agree with the persisted outcome. Checking success wording alone would miss this defect.

## Lost response and duplicate refund

Select **Duplicate refund**, then **Lost response after commit**.

The tool trace shows a timeout after the first committed refund, followed by a retry. The state diff contains two refunds.

Switch to **Reference agent** and select the same scenario. The retry reuses the first refund, preserving one committed effect. This demonstrates serial retry idempotency; concurrent processing would require additional constraints and tests.

## Customer isolation

Select **Authorization bypass**, then **Customer isolation**.

Inspect the foreign-data and side-effect checks. The trusted customer identity is supplied outside the agent's tool arguments, and the tool boundary enforces ownership. The deliberate bypass demonstrates that the evaluator detects a violation.

## Evaluation design

- Expected outcomes are separate from agent inputs and the application's policy function.
- Each case starts with isolated database state. Repeated requests share state only within scenarios that require it.
- Completion claims are checked at each turn, so a later success cannot hide an earlier unsupported claim.

See [architecture](architecture.md) and [test strategy](test-strategy.md) for implementation details and limitations.
